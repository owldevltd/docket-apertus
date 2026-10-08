"""The elements of a page: what the geometry can name on its own, and every other object as "unknown".

Sure are: line, tick mark, empty tinted area, empty cell. An area with print in it is background (a title bar)
and no element. Everything else is read, not guessed.
"""

from __future__ import annotations

from docket.page.mask import Page

# line: much longer than thick; dotted lines come out of the smearing as such objects
LINE_ASPECT = 8.0
LINE_THICK = 0.6


def type_elements(
    page: Page, lines: list[dict], marks: list[dict], areas: list[dict], cells: list[dict], objects: list[dict]
) -> list[dict]:
    elements: list[dict] = []
    for line in lines:
        elements.append(_element("line", line))
    for mark in marks:
        elements.append(_element(mark["kind"], mark))
    for area in areas:
        if any(_overlaps(o, area) for o in objects):
            continue
        # a coloured separator bar is a line, not a field
        elements.append(_element("line" if _thin(page, area) else "input", area))
    for cell in cells:
        # the tinted area in the cell is the field already
        if any(_covers(area, cell) for area in areas):
            continue
        elements.append(_element("input", cell))
    for o in objects:
        elements.append(_element("line" if _thin(page, o) else "unknown", o))
    return sorted(elements, key=lambda e: (e["y"], e["x"]))


def _overlaps(a: dict, b: dict) -> bool:
    across = a["x"] < b["x"] + b["w"] and a["x"] + a["w"] > b["x"]
    down = a["y"] < b["y"] + b["h"] and a["y"] + a["h"] > b["y"]
    return across and down


def _covers(a: dict, b: dict) -> bool:
    """The overlap is more than half of the smaller box."""
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return w > 0 and h > 0 and w * h * 2 > min(a["w"] * a["h"], b["w"] * b["h"])


def _thin(page: Page, b: dict) -> bool:
    thin = min(b["w"], b["h"])
    return thin <= LINE_THICK * page.unit * page.scale and max(b["w"], b["h"]) >= LINE_ASPECT * thin


def _element(kind: str, b: dict) -> dict:
    return {"type": kind, "content": b.get("content", ""), "x": b["x"], "y": b["y"], "width": b["w"], "height": b["h"]}
