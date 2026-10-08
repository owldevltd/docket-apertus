"""Tick marks and empty cells: the shapes the geometry can name without reading.

A tick mark is an empty square (checkbox) or an empty circle (radio) of about character size standing free. A
cell is paper enclosed by lines on all sides with nothing in it. Documents carry such marks on cover sheets
("Richtlinienmotion [ ]"); a ticked mark has ink inside and is left to the reading step here.
"""

from __future__ import annotations

import numpy as np

from docket.page.mask import Page, by_position, has_ink, label, round_half_up

# side length in character heights of the page, and how far width and height may differ
MIN_SIZE = 0.6
MAX_SIZE = 4.0
SQUARE = 1.25
ROUND = 1.15

# share of an edge that carries ink: nearly all of it on a box, only the middle part on a circle
EDGE_FULL = 0.8
EDGE_ARC = 0.75

# inside at most this share of ink
HOLLOW = 0.05

# this far free to the left and right, in shares of the own height: an O inside a word does not stand free
CLEAR = 0.25

# cell: smallest side in character heights of the page, and how well it fills its box
CELL_MIN = 0.8
CELL_FILL = 0.9

# close lines at crossings and corners: this many work pixels longer and thicker
CELL_SEAL = 2


def find_marks(page: Page) -> list[dict]:
    mask = page.masks["ink"]
    s = page.scale
    marks = []
    for b in label(mask):
        w = b[2] - b[0] + 1
        h = b[3] - b[1] + 1
        if min(w, h) < MIN_SIZE * page.unit or max(w, h) > MAX_SIZE * page.unit:
            continue
        if max(w, h) > SQUARE * min(w, h):
            continue
        kind = shape(mask, b[0], b[1], w, h)
        if kind:
            marks.append({"x": b[0] * s, "y": b[1] * s, "w": w * s, "h": h * s, "kind": kind, "content": ""})
    return by_position(marks)


def shape(mask: np.ndarray, x: int, y: int, w: int, h: int) -> str:
    """'checkbox', 'radio' or '' for the blob at x, y in work pixels."""
    # edges: only the outermost pixels; deeper in, nearly the whole width is under ink on a circle too
    t = max(1, min(w, h) // 10)
    rows = mask[y : y + h, x : x + w]
    counts = rows.sum(axis=1)
    top = int(counts[:t].max())
    bottom = int(counts[h - t :].max())
    left = int(rows[:, :t].any(axis=1).sum())
    right = int(rows[:, w - t :].any(axis=1).sum())

    # inside: only the middle field; closer to the edge the ring of a circle lies in the field's corners
    q = max(t + 1, round_half_up(0.35 * min(w, h)))
    if w - 2 * q < 1 or h - 2 * q < 1:
        return ""
    inside = int(rows[q : h - q, q : w - q].sum())
    if inside > HOLLOW * (w - 2 * q) * (h - 2 * q):
        return ""

    if top >= EDGE_FULL * w and bottom >= EDGE_FULL * w and left >= EDGE_FULL * h and right >= EDGE_FULL * h:
        return "checkbox"

    # circle: every edge touched only in the middle, all four corners empty, free to the left and right
    if top > EDGE_ARC * w or bottom > EDGE_ARC * w or left > EDGE_ARC * h or right > EDGE_ARC * h:
        return ""
    if not top or not bottom or not left or not right:
        return ""
    if max(w, h) > ROUND * min(w, h):
        return ""

    # closed: from the middle every direction hits ink (a C or a U is open)
    mid = rows[h // 2]
    col = rows[:, w // 2]
    if not mid[: w // 2].any() or not mid[w // 2 :].any() or not col[: h // 2].any() or not col[h // 2 :].any():
        return ""

    c = max(1, min(w, h) // 8)
    for r0 in (0, h - c):
        if rows[r0 : r0 + c, :c].any() or rows[r0 : r0 + c, w - c :].any():
            return ""
    gap = max(2, round_half_up(CLEAR * h))
    if has_ink(mask, x - gap, y, x - 1, y + h - 1) or has_ink(mask, x + w, y, x + w + gap - 1, y + h - 1):
        return ""
    return "radio"


def find_cells(page: Page, lines: list[dict]) -> list[dict]:
    """Empty cells: paper enclosed by lines and holding nothing. The lines are laid into a full mask as
    barriers; what is connected afterwards and does not touch the page edge is a cell."""
    s = page.scale
    w, h = page.w, page.h
    rows = np.ones((h, w), dtype=bool)
    for line in lines:
        x0 = max(0, line["x"] // s - CELL_SEAL)
        x1 = min(w - 1, (line["x"] + line["w"]) // s + CELL_SEAL)
        y0 = max(0, line["y"] // s - CELL_SEAL)
        y1 = min(h - 1, (line["y"] + line["h"]) // s + CELL_SEAL)
        rows[y0 : y1 + 1, x0 : x1 + 1] = False

    minimum = CELL_MIN * page.unit
    cells = []
    for b in label(rows):
        bw = b[2] - b[0] + 1
        bh = b[3] - b[1] + 1
        if b[0] == 0 or b[1] == 0 or b[2] == w - 1 or b[3] == h - 1:
            continue
        if min(bw, bh) < minimum or b[4] < CELL_FILL * bw * bh:
            continue
        # empty: no ink; a tinted cell is already an area
        if has_ink(page.masks["ink"], b[0], b[1], b[2], b[3]):
            continue
        # the barrier was thicker than the line: the box back out to the line
        cells.append(
            {
                "x": (b[0] - CELL_SEAL) * s,
                "y": (b[1] - CELL_SEAL) * s,
                "w": (bw + 2 * CELL_SEAL) * s,
                "h": (bh + 2 * CELL_SEAL) * s,
            }
        )
    return by_position(cells)
