"""Font size and colour per element, measured on the image without the text.

The size comes from the profile of the text lines inside an element: the x-height is the band of pixel rows with
much ink, ascenders and descenders show above and below it, and the largest measure the line yields is used.
The colour is what stands out from the most frequent colour in the box.
"""

from __future__ import annotations

import numpy as np

from docket.page.mask import Page, round_half_up
from docket.page.raster import QUANTUM

# heights in em (Arial, Helvetica): x-height 0.519, cap and ascender height 0.716, ascender to descender 0.93
X_HEIGHT = 0.52
CAP_HEIGHT = 0.72
FULL_HEIGHT = 0.93

# a pixel row belongs to the x-height when it carries at least this share of the fullest row's ink
BAND = 0.5

# when the band fills the line this far, only capitals or digits stand there
ALL_CAPS = 0.85

# from this share of the x-height above or below the band the line has ascenders or descenders
ASCENT = 0.25
DESCENT = 0.15

# more ink than this in the box: light text on dark ground, the paper is measured
INVERSE = 0.55

# page width in points, portrait and landscape: without a note A4; the conversion from pixels to points
PAGE_PT = (595.28, 841.89)

# colours: samples per element, and from which grey distance to the ground a pixel is foreground
SAMPLES = 4000
CONTRAST = 48


def style_elements(page: Page, elements: list[dict], strips: list[dict], marks: list[dict]) -> None:
    """Writes color, background (#rrggbb) and fontSize (points) onto every element."""
    ink = page.gray_q <= page.ink * QUANTUM
    pt = PAGE_PT[1 if page.width > page.height else 0] / page.width
    sizes: dict[int, list[float]] = {}
    for i, e in enumerate(elements):
        if e["type"] != "unknown":
            continue
        for t in _strips_in(e, strips):
            x0, x1 = _span(t, marks)
            px = 0.0 if x1 - x0 < 4 else _profile(_rows(ink, t, x0, x1))
            if px > 0:
                sizes.setdefault(i, []).append(px * pt)

    rgb = page.rgb if page.rgb.ndim == 3 else np.repeat(page.gray[:, :, np.newaxis], 3, axis=2)
    for i, e in enumerate(elements):
        fore, ground = _colors(rgb, e)
        # a line and a field are themselves the colour of their box and have no ground; for everything else
        # color is what stands out from the ground
        own = e["type"] in ("line", "input")
        e["color"] = ground if own else fore
        e["background"] = None if own else ground
        e["fontSize"] = round(_median(sizes[i]), 1) if i in sizes else None


def _strips_in(e: dict, strips: list[dict]) -> list[dict]:
    """The text lines of an element: their centre lies in its box. Lines lying wholly inside another do not
    count: with light text on a bar the bar is the line, and what appears inside are the counters of the
    letters."""
    inside = []
    for t in strips:
        cx = t["x"] + t["w"] / 2
        cy = t["y"] + t["h"] / 2
        if e["x"] <= cx <= e["x"] + e["width"] and e["y"] <= cy <= e["y"] + e["height"]:
            inside.append(t)
    return [t for t in inside if not any(o is not t and _contains(o, t) for o in inside)]


def _contains(o: dict, t: dict) -> bool:
    inside_x = o["x"] <= t["x"] and o["x"] + o["w"] >= t["x"] + t["w"]
    inside_y = o["y"] <= t["y"] and o["y"] + o["h"] >= t["y"] + t["h"]
    return inside_x and inside_y


def _span(t: dict, marks: list[dict]) -> tuple[int, int]:
    """The part of a text line with text in it: a tick mark at the start or the end does not count."""
    x0 = t["x"]
    x1 = t["x"] + t["w"]
    for m in marks:
        cy = m["y"] + m["h"] / 2
        if cy < t["y"] or cy > t["y"] + t["h"] or m["x"] + m["w"] < x0 or m["x"] > x1:
            continue
        if m["x"] + m["w"] / 2 < (x0 + x1) / 2:
            x0 = m["x"] + m["w"] + 2
        else:
            x1 = m["x"] - 2
    return x0, x1


def _rows(ink: np.ndarray, t: dict, x0: int, x1: int) -> np.ndarray:
    """The pixel rows of a text line, True where text is. With more than half dark the text stands light on a
    bar."""
    rows = ink[t["y"] : t["y"] + t["h"], x0:x1]
    if rows.size and rows.sum() > INVERSE * rows.size:
        return ~rows
    return rows


def _profile(rows: np.ndarray) -> float:
    """Font size in pixels from the profile of the pixel rows, measured on the largest measure the line yields:
    ascender to descender, else ascender to baseline, else the x-height alone."""
    if rows.size == 0:
        return 0.0
    n = rows.sum(axis=1)
    peak = int(n.max())
    if not peak:
        return 0.0
    full = np.nonzero(n >= BAND * peak)[0]
    any_ = np.nonzero(n)[0]
    band = int(full[-1] - full[0] + 1)
    all_ = int(any_[-1] - any_[0] + 1)
    up = int(full[0] - any_[0])
    down = int(any_[-1] - full[-1])
    if band > ALL_CAPS * all_:
        return all_ / CAP_HEIGHT
    if up >= ASCENT * band and down >= DESCENT * band:
        return all_ / FULL_HEIGHT
    if up >= ASCENT * band:
        return (band + up) / CAP_HEIGHT
    return band / X_HEIGHT


def _colors(rgb: np.ndarray, e: dict) -> tuple[str | None, str | None]:
    """Ground = the most frequent colour in the box. Foreground = what stands out from it in grey value,
    averaged over the tenth with the largest distance (the middle of the strokes, without the mixed tones at
    the edge)."""
    box = rgb[e["y"] : e["y"] + max(1, e["height"]), e["x"] : e["x"] + max(1, e["width"])]
    h, w = box.shape[:2]
    if h == 0 or w == 0:
        return None, None
    step = max(1, int(np.floor(np.sqrt(w * h / SAMPLES))))
    px = box[::step, ::step].reshape(-1, 3).astype(np.int64)
    keys = (px[:, 0] >> 3) << 10 | (px[:, 1] >> 3) << 5 | (px[:, 2] >> 3)
    uniq, first, counts = np.unique(keys, return_index=True, return_counts=True)
    top = counts == counts.max()
    mode = uniq[top][np.argmin(first[top])]
    back = _mean(px[keys == mode])
    gray = sum(back) / 3

    d = np.abs(px.sum(axis=1) / 3 - gray)
    chosen = np.nonzero(d >= CONTRAST)[0]
    if len(chosen):
        order = chosen[np.argsort(-d[chosen], kind="stable")]
        chosen = order[: max(1, len(order) // 10)]
    fore = _hex(_mean(px[chosen])) if len(chosen) else None
    return fore, _hex(back)


def _mean(px: np.ndarray) -> tuple[int, int, int]:
    n = max(1, len(px))
    return tuple(round_half_up(float(px[:, c].sum()) / n) for c in range(3))  # type: ignore[return-value]


def _hex(c: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*c)


def _median(values: list[float]) -> float:
    ordered = sorted(values)
    return float(ordered[len(ordered) // 2])
