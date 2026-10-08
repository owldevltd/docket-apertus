"""Control images: what the geometry found, drawn over the page."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from docket.page.raster import scale_rgb, to_rgb, write_png

OUT_WIDTH = 1400
STROKE = 4

# colour and fill opacity per element type; without a fill only the border
TYPES = {
    "text": ("#e00000", 0.0),
    "image": ("#8a2be2", 0.2),
    "input": ("#00a000", 0.25),
    "checkbox": ("#ff8c00", 0.45),
    "radio": ("#ff8c00", 0.45),
    "line": ("#0030ff", 0.6),
    "unknown": ("#ff00c8", 0.3),
}


def draw_geometry(image: np.ndarray, target: str | Path, found: dict) -> None:
    """Areas green, lines blue (light ones light blue), object borders red, cells green, marks orange."""
    canvas = to_rgb(image).astype(np.float32).copy()
    for a in found["areas"]:
        _fill(canvas, a["x"], a["y"], a["w"], a["h"], "#00a000", 0.18)
        _stroke(canvas, a["x"], a["y"], a["w"], a["h"], "#008000")
    for line in found["lines"]:
        pad = 3
        color = "#00b0ff" if line["light"] else "#0030ff"
        _fill(canvas, line["x"] - pad, line["y"] - pad, line["w"] + 2 * pad, line["h"] + 2 * pad, color, 0.6)
    for o in found["objects"]:
        _stroke(canvas, o["x"], o["y"], o["w"], o["h"], "#e00000")
    for c in found["cells"]:
        _fill(canvas, c["x"], c["y"], c["w"], c["h"], "#00a000", 0.18)
    for m in found["marks"]:
        _fill(canvas, m["x"], m["y"], m["w"], m["h"], "#ff8c00", 0.45)
    _save(canvas, target)


def draw_elements(image: np.ndarray, target: str | Path, elements: list[dict]) -> None:
    """The element list by type: text red border, image violet, input green, mark orange, line blue, unknown
    magenta. Yellow: approve, a person has to confirm the text."""
    canvas = to_rgb(image).astype(np.float32).copy()
    for kind, (color, fill) in TYPES.items():
        for e in elements:
            if e["type"] != kind:
                continue
            if fill > 0:
                _fill(canvas, e["x"], e["y"], e["width"], e["height"], color, fill)
            if kind != "line":
                _stroke(canvas, e["x"], e["y"], e["width"], e["height"], color)
    for e in elements:
        if e.get("approve"):
            _fill(canvas, e["x"], e["y"], e["width"], e["height"], "#ffd400", 0.4)
    _save(canvas, target)


# a small bitmap font, 5 x 7, for the ids the model is shown in a crop; enough for "[block_12]"
GLYPHS = {
    "[": ("###..", "#....", "#....", "#....", "#....", "#....", "###.."),
    "]": ("..###", "....#", "....#", "....#", "....#", "....#", "..###"),
    "b": ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "l": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..##."),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    "c": (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    "k": ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "####.", "#...#", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
}


def draw_label(canvas: np.ndarray, x: int, y: int, text: str, color: tuple[int, int, int], scale: int = 4) -> None:
    """Writes the text in the bitmap font, each glyph 5 x 7 pixels times the scale, at x, y (top left)."""
    cx = x
    for ch in text:
        rows = GLYPHS.get(ch)
        if rows:
            for r, row in enumerate(rows):
                for c, bit in enumerate(row):
                    if bit == "#":
                        y0, x0 = y + r * scale, cx + c * scale
                        canvas[max(0, y0) : max(0, y0 + scale), max(0, x0) : max(0, x0 + scale)] = color
        cx += 6 * scale


def draw_frame(canvas: np.ndarray, x: int, y: int, w: int, h: int, thickness: int, color: tuple[int, int, int]) -> None:
    """A rectangle outline of the thickness, clipped to the canvas."""
    sides = (
        (x, y, w, thickness),
        (x, y + h - thickness, w, thickness),
        (x, y, thickness, h),
        (x + w - thickness, y, thickness, h),
    )
    for rx, ry, rw, rh in sides:
        y0, y1 = max(0, ry), min(canvas.shape[0], ry + rh)
        x0, x1 = max(0, rx), min(canvas.shape[1], rx + rw)
        if y1 > y0 and x1 > x0:
            canvas[y0:y1, x0:x1] = color


def _save(canvas: np.ndarray, target: str | Path) -> None:
    write_png(target, scale_rgb(np.clip(np.rint(canvas), 0, 255).astype(np.uint8), OUT_WIDTH))


def _rgb(color: str) -> np.ndarray:
    return np.array([int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)], dtype=np.float32)


def _fill(canvas: np.ndarray, x: int, y: int, w: int, h: int, color: str, opacity: float) -> None:
    y0, y1 = max(0, y), min(canvas.shape[0], y + h + 1)
    x0, x1 = max(0, x), min(canvas.shape[1], x + w + 1)
    if y1 <= y0 or x1 <= x0:
        return
    canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - opacity) + _rgb(color) * opacity


def _stroke(canvas: np.ndarray, x: int, y: int, w: int, h: int, color: str) -> None:
    half = STROKE // 2
    _fill(canvas, x - half, y - half, w + STROKE, STROKE - 1, color, 1.0)
    _fill(canvas, x - half, y + h - half, w + STROKE, STROKE - 1, color, 1.0)
    _fill(canvas, x - half, y - half, STROKE - 1, h + STROKE, color, 1.0)
    _fill(canvas, x + w - half, y - half, STROKE - 1, h + STROKE, color, 1.0)
