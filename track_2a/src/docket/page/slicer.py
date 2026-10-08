"""Objects and tinted areas.

Ink that lies close together belongs together: short paper gaps between ink are smeared shut, first across
(character to word to line), then down (line to paragraph); what is connected afterwards is an object. The
character height of the page, the median height of all ink blobs, is the measure of every distance, so the same
values hold for 8 pt and 14 pt.
"""

from __future__ import annotations

import numpy as np

from docket.page.mask import Page, by_position, label, round_half_up, smear

# gaps in character heights: word gap about 0.5, column gap above 2; down the page more than a form wants,
# since the line decides in the joiner (trial 1 of 5 October 2026, c9 against c7)
SMEAR_H = 1.2
SMEAR_V = 0.7

# an object from this share of the page is too big and is computed again inside its box, with half the gap
BIG = 0.25

# smaller than this on both sides (work pixels) is dust
MIN_SIZE = 3

# an area fills its rectangle at least to this share
MIN_FILL = 0.7


def measure_unit(page: Page) -> int:
    """Character height of the page = the median height of all ink blobs between 4 and 80 work pixels."""
    heights = sorted(b[3] - b[1] + 1 for b in label(page.masks["ink"]) if 4 <= b[3] - b[1] + 1 <= 80)
    return heights[len(heights) // 2] if heights else page.unit


def find_objects(page: Page) -> list[dict]:
    rows = page.masks["ink"].copy()
    for x0, y0, x1, y1 in page.links:
        rows[y0 : y1 + 1, x0 : x1 + 1] = True

    linked = rows
    rows = smear(rows, round_half_up(SMEAR_H * page.unit))
    rows = smear(rows.T, round_half_up(SMEAR_V * page.unit)).T

    big = BIG * page.w * page.h
    boxes = []
    for b in label(rows):
        w = b[2] - b[0] + 1
        h = b[3] - b[1] + 1
        if w * h < big:
            boxes.append(b)
            continue
        sub = smear(linked[b[1] : b[3] + 1, b[0] : b[2] + 1], round_half_up(SMEAR_H * page.unit / 2))
        for c in label(sub):
            boxes.append((c[0] + b[0], c[1] + b[1], c[2] + b[0], c[3] + b[1], c[4]))

    s = page.scale
    objects = []
    for b in boxes:
        w = b[2] - b[0] + 1
        h = b[3] - b[1] + 1
        if w < MIN_SIZE and h < MIN_SIZE:
            continue
        objects.append({"x": b[0] * s, "y": b[1] * s, "w": w * s, "h": h * s})
    return by_position(objects)


def find_areas(page: Page) -> list[dict]:
    """Tinted areas: grey fields, coloured boxes. Only what is tinted without ink and fills its rectangle well;
    the rest are fringes and gradients."""
    rows = page.masks["solid"] & ~page.masks["ink"]
    s = page.scale
    minimum = max(4, page.unit // 2)
    areas = []
    for b in label(rows):
        w = b[2] - b[0] + 1
        h = b[3] - b[1] + 1
        if w < 2 * page.unit or h < minimum:
            continue
        if b[4] < MIN_FILL * w * h:
            continue
        areas.append({"x": b[0] * s, "y": b[1] * s, "w": w * s, "h": h * s})
    return by_position(areas)


def ink_rows(mask: np.ndarray, x0: int, y0: int, w: int, h: int) -> np.ndarray:
    """The box of a mask as its own array."""
    return mask[y0 : y0 + h, x0 : x0 + w]
