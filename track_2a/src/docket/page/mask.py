"""Page image to ink masks, and the two operations every step uses on them.

The geometry works on a mask shrunk to about WORK_WIDTH pixels: object borders do not need 300 dpi. Three
masks: ink (clearly darker than the paper), tone (anything that is not paper, grey fields and light lines
included) and solid (tone where the whole block is tinted, without the light fringes around glyphs).
`label` finds connected components of ink runs, `smear` fills short paper gaps between ink (run-length
smearing, Wong, Casey and Wahl 1982). A mask is a boolean array, rows down, columns across.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from docket.page.raster import QUANTUM, luma_quantum, read_pnm, scale_box

WORK_WIDTH = 1240

# ink is clearly darker than the paper, but at most this grey value
INK_MAX = 160
INK_DIST = 60

# tone starts just below paper white: grey field areas are often only 10 to 15 steps darker
TONE_DIST = 8

Box = tuple[int, int, int, int, int]  # x0, y0, x1, y1, pixel count in work pixels


@dataclass
class Page:
    """One page: the image, its measures and the work masks. Steps read and write here."""

    file: str
    width: int
    height: int
    scale: int
    w: int
    h: int
    paper: int
    ink: int
    # grey per pixel: 8 bit for the histogram and the colours, 16 bit for every threshold
    gray: np.ndarray
    gray_q: np.ndarray
    rgb: np.ndarray
    masks: dict[str, np.ndarray]
    unit: int = 10
    # bridges [x0, y0, x1, y1] in work pixels that the joiner lays into the mask before the smearing
    links: list[tuple[int, int, int, int]] = field(default_factory=list)


def load_page(path: str | Path) -> Page:
    image = read_pnm(path)
    gray_q = luma_quantum(image)
    gray = (gray_q // QUANTUM).astype(np.uint8)
    height, width = gray.shape
    scale = max(1, int(width / WORK_WIDTH + 0.5))
    w = width // scale
    h = height // scale

    # paper white = the most frequent light grey value: scans sit at 235 to 250, old paper around 205
    hist = np.bincount(gray.ravel(), minlength=256)
    paper = 128 + int(np.argmax(hist[128:]))
    ink = min(INK_MAX, paper - INK_DIST)

    return Page(
        file=Path(path).name,
        width=width,
        height=height,
        scale=scale,
        w=w,
        h=h,
        paper=paper,
        ink=ink,
        gray=gray,
        gray_q=gray_q,
        rgb=image,
        masks={
            "ink": make_mask(gray_q, w, h, scale, ink, strict=False),
            "tone": make_mask(gray_q, w, h, scale, paper - TONE_DIST, strict=False),
            "solid": make_mask(gray_q, w, h, scale, paper - TONE_DIST, strict=True),
        },
    )


def make_mask(gray_q: np.ndarray, w: int, h: int, scale: int, level: int, strict: bool) -> np.ndarray:
    """First black and white at full resolution (a pixel at or below the level is ink), then shrunk by area
    averaging to 8-bit values. Loose: a single dark pixel in the block is enough, so 1-px lines survive.
    Strict: the whole block must be dark, so 1-px fringes drop out. Checked against the library's masks on
    482 pages (8 October 2026)."""
    part = 127 // (scale * scale)
    cut = part + 1 if strict else 255 - part
    white = (gray_q > level * QUANTUM).astype(np.float64)
    value = np.rint(255 * scale_box(white, w, h))
    return value < cut


def label(mask: np.ndarray) -> list[Box]:
    """Connected components over ink runs: a run hangs on every run of the row above that it touches, diagonally
    too. Per component the box and the pixel count, in the order the components were first seen."""
    padded = np.zeros((mask.shape[0], mask.shape[1] + 2), dtype=np.int8)
    padded[:, 1:-1] = mask
    edges = np.diff(padded, axis=1)
    rows, starts = np.nonzero(edges == 1)
    ends = np.nonzero(edges == -1)[1]
    parent: list[int] = []
    box: list[list[int]] = []
    prev: list[tuple[int, int, int]] = []
    prev_row = -1
    i = 0
    n = len(rows)
    while i < n:
        y = int(rows[i])
        if y != prev_row + 1:
            prev = []
        cur: list[tuple[int, int, int]] = []
        pi = 0
        pn = len(prev)
        while i < n and rows[i] == y:
            x0 = int(starts[i])
            x1 = int(ends[i]) - 1
            i += 1
            own = len(parent)
            parent.append(own)
            box.append([x0, y, x1, y, x1 - x0 + 1])
            while pi < pn and prev[pi][1] < x0 - 1:
                pi += 1
            pj = pi
            while pj < pn and prev[pj][0] <= x1 + 1:
                a = _root(parent, own)
                b = _root(parent, prev[pj][2])
                if a != b:
                    parent[a] = b
                    ba = box[a]
                    bb = box[b]
                    box[b] = [min(ba[0], bb[0]), min(ba[1], bb[1]), max(ba[2], bb[2]), max(ba[3], bb[3]), ba[4] + bb[4]]
                pj += 1
            # the last touched run of the row above may touch the next run as well
            if pj > pi:
                pi = pj - 1
            cur.append((x0, x1, own))
        prev = cur
        prev_row = y
    return [tuple(box[k]) for k, p in enumerate(parent) if k == p]  # type: ignore[misc]


def _root(parent: list[int], k: int) -> int:
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k


def smear(mask: np.ndarray, gap: int) -> np.ndarray:
    """Paper runs of up to `gap` pixels that touch ink on both sides become ink, along the rows."""
    if gap < 1:
        return mask.copy()
    width = mask.shape[1]
    cols = np.arange(width)
    last = np.maximum.accumulate(np.where(mask, cols, -1), axis=1)
    nxt = np.minimum.accumulate(np.where(mask, cols, width)[:, ::-1], axis=1)[:, ::-1]
    fill = ~mask & (last >= 0) & (nxt < width) & (nxt - last - 1 <= gap)
    return mask | fill


def has_ink(mask: np.ndarray, x0: int, y0: int, x1: int, y1: int) -> bool:
    """Whether the box x0..x1, y0..y1 (inclusive, clipped) holds any ink."""
    x0 = max(0, x0)
    y0 = max(0, y0)
    if x1 < x0 or y1 < y0:
        return False
    return bool(mask[y0 : y1 + 1, x0 : x1 + 1].any())


def by_position(items: list[dict]) -> list[dict]:
    """Sorted by y, then x, keeping the order of equals."""
    return sorted(items, key=lambda b: (b["y"], b["x"]))


def round_half_up(value: float) -> int:
    """Rounding as the measurements had it: halves away from zero (for the positive values used here)."""
    return int(np.floor(value + 0.5))
