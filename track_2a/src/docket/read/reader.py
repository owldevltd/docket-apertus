"""Reads the elements of a page without a text layer with the model.

Measured on 6 October 2026 on 180 elements of ten digital pages against their text layer: every block alone with
its surroundings reads 111 of 180 exactly with 180 calls; three blocks cut out and stacked on white as a strip
read 111 with 60 calls; the strip first and then every multi-line block alone reads 116 with 126 calls. That is
the order here. Afterwards every reading is held against the image (fluffy); read elements carry isOCR.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np

from docket.fluffy import THRESHOLD, check_elements
from docket.model.client import Client, ask
from docket.page.painter import draw_frame, draw_label
from docket.page.raster import encode_png, scale_rgb, to_rgb

BUNDLE = 3
MAX_WIDTH = 1240

# strip: air between the blocks and at the edge; single image: surroundings around the block (page pixels)
GAP = 90
EDGE = 40
AROUND = 24

# a block is multi-line from this height in font sizes; it is read alone after the strip
TALL = 1.6

RED = (220, 0, 0)


def read_page(client: Client, rgb: np.ndarray, gray: np.ndarray, page: dict, log: Path | None = None) -> int:
    """Reads every element still unknown; afterwards they carry content, type (text or image), isOCR and
    approve. Returns the number of calls."""
    image = to_rgb(rgb)
    px = page["width"] / (842.0 if page["width"] > page["height"] else 595.0)
    elements = page["elements"]
    unknown = [i for i, e in enumerate(elements) if e["type"] == "unknown"]
    todo = sorted(unknown, key=lambda i: (elements[i]["y"], elements[i]["x"]))
    before = client.calls

    read: dict[int, str] = {}
    for k in range(0, len(todo), BUNDLE):
        chunk = todo[k : k + BUNDLE]
        read.update(_ask(client, _strip(image, [page["elements"][i] for i in chunk]), chunk, framed=False, log=log))
        if client.halted:
            break
    for i in todo:
        e = page["elements"][i]
        tall = e["height"] > TALL * float(e.get("fontSize") or 10) * px
        if (tall or i not in read) and not client.halted:
            read.update(_ask(client, _single(image, e), [i], framed=True, log=log))

    for i in todo:
        e = page["elements"][i]
        text = (read.get(i) or "").strip()
        e["content"] = text
        e["type"] = "text" if text else "image"
        e["isOCR"] = True
    check_elements(page["elements"], gray, THRESHOLD)
    return client.calls - before


def _strip(image: np.ndarray, chunk: list[dict]) -> bytes:
    """Only the blocks, stacked on white with air between them and the id above each."""
    ph, pw = image.shape[:2]
    w = int(max(e["width"] for e in chunk) + 2 * EDGE)
    h = int(sum(e["height"] for e in chunk) + len(chunk) * GAP + EDGE)
    canvas = np.full((h, w, 3), 255, dtype=np.uint8)
    y = EDGE
    for k, e in enumerate(chunk, 1):
        draw_label(canvas, EDGE, y, f"[block_{k}]", RED)
        y += GAP // 2
        x0, y0 = max(0, e["x"]), max(0, e["y"])
        cw, ch = min(e["width"], pw - x0), min(e["height"], ph - y0)
        if cw > 0 and ch > 0:
            canvas[y : y + ch, EDGE : EDGE + cw] = image[y0 : y0 + ch, x0 : x0 + cw]
        y += int(e["height"] + GAP // 2)
    return _png(canvas)


def _single(image: np.ndarray, e: dict) -> bytes:
    """The block with its surroundings, a red frame and the id [block_1]."""
    ph, pw = image.shape[:2]
    x0 = max(0, e["x"] - 3 * AROUND)
    y0 = max(0, e["y"] - 2 * AROUND)
    x1 = min(pw, e["x"] + e["width"] + AROUND)
    y1 = min(ph, e["y"] + e["height"] + AROUND)
    canvas = image[y0 : max(y0 + 1, y1), x0 : max(x0 + 1, x1)].copy()
    draw_frame(canvas, e["x"] - x0 - 4, e["y"] - y0 - 4, e["width"] + 8, e["height"] + 8, 3, RED)
    draw_label(canvas, e["x"] - x0 - 4, max(0, e["y"] - y0 - 36), "[block_1]", RED)
    return _png(canvas)


def _png(canvas: np.ndarray) -> bytes:
    if canvas.shape[1] > MAX_WIDTH:
        canvas = scale_rgb(canvas, MAX_WIDTH)
    return encode_png(canvas)


def _ask(client: Client, png: bytes, chunk: list[int], framed: bool, log: Path | None) -> dict[int, str]:
    """One call with one image; the read text per element index of the chunk."""
    n = len(chunk)
    ids = "[block_1]" + (f" bis [block_{n}]" if n > 1 else "")
    if framed:
        blocks = "ist ein Textblock" if n == 1 else f"sind {n} Textblöcke"
        where = (
            f"Das Bild ist ein Ausschnitt aus einem Dokument. Darin {blocks} mit rotem Rahmen "
            f"und der Kennung {ids} markiert. "
        )
    else:
        where = (
            f"Das Bild zeigt {n} Textblöcke aus einem Dokument untereinander, "
            f"jeder mit der roten Kennung {ids} darüber. "
        )
    prompt = (
        where
        + "Schreibe den Text jedes Blocks exakt ab, Zeichen für Zeichen, ohne die rote Kennung, "
        + 'ohne Kästchen und Kreise; steht kein Text im Block, schreibe "". '
        + 'Antworte mit genau einer Zeile je Block, in der Form "block_1: <Text>", ohne weiteren Text.'
    )
    answer = ask(client, prompt, image=png, room=400 * n, log=log, tag=f"read {'single' if framed else 'strip'}")
    if answer is None:
        return {}
    lines: dict[int, str] = {}
    for line in answer.text.splitlines():
        m = re.match(r"^\s*\[?block[_ ]?(\d+)\]?\s*:\s*(.*)$", line, re.I)
        if m:
            lines[int(m.group(1))] = m.group(2).strip(' \t"')
    # a single block comes back without its id as well
    if n == 1 and not lines:
        lines[1] = answer.text.strip(' \t"')
    return {i: lines[k] for k, i in enumerate(chunk, 1) if k in lines}
