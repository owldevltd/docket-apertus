"""Straight lines, found and taken out of the masks.

Lines are scaffolding (tables, frames, writing lines), not content: left in, the smearing would glue everything
along a table line into one object. Long ink runs per row are bundled over neighbouring rows into lines with a
thickness; both directions are searched on the unchanged masks, so a pixel at a crossing belongs to both lines.
"""

from __future__ import annotations

import numpy as np

from docket.page.mask import Page, round_half_up

# in character heights: longer than any stroke of a letter, thinner than a bar
MIN_LENGTH = 4.0
MAX_THICK = 0.5

# runs beneath each other belong to the same line when start and length lie this close
TOLERANCE = 3

# with ink above and below the run to this share, it is part of an area (a title bar with light text)
MAX_FLANK = 0.5

Run = list[int]  # start, row, length, thickness


def find_lines(page: Page) -> list[dict]:
    masks = page.masks
    # light lines stand only in the tone mask; the ink is taken out, else a dark line merges with the grey
    # area beside it
    light = masks["tone"] ^ masks["ink"]
    found = [
        (scan(masks["ink"], page.unit), "h", False),
        (scan(masks["ink"].T, page.unit), "v", False),
        (scan(light, page.unit), "h", True),
        (scan(light.T, page.unit), "v", True),
    ]
    s = page.scale
    lines: list[dict] = []
    for runs, direction, is_light in found:
        for run in runs:
            x, y, w, h = run if direction == "h" else (run[1], run[0], run[3], run[2])
            if is_light and known(lines, x * s, y * s, w * s, h * s, direction, s):
                continue
            lines.append({"x": x * s, "y": y * s, "w": w * s, "h": h * s, "dir": direction, "light": is_light})
            for mask in masks.values():
                mask[y : y + h, x : x + w] = False
    return lines


def known(lines: list[dict], x: int, y: int, w: int, h: int, direction: str, scale: int) -> bool:
    """The light fringe of a dark line is not a second line."""
    near = 3 * scale
    for line in lines:
        if line["dir"] != direction:
            continue
        if direction == "h" and abs(line["y"] - y) <= near and line["x"] < x + w and line["x"] + line["w"] > x:
            return True
        if direction == "v" and abs(line["x"] - x) <= near and line["y"] < y + h and line["y"] + line["h"] > y:
            return True
    return False


def scan(rows: np.ndarray, unit: int) -> list[Run]:
    """Long runs per row, bundled over neighbouring rows into lines with a thickness. Returns start, row,
    length and thickness in the coordinates of the rows given (transpose for columns)."""
    minimum = max(8, round_half_up(MIN_LENGTH * unit))
    thick = max(3, round_half_up(MAX_THICK * unit))

    padded = np.zeros((rows.shape[0], rows.shape[1] + 2), dtype=np.int8)
    padded[:, 1:-1] = rows
    edges = np.diff(padded, axis=1)
    run_rows, starts = np.nonzero(edges == 1)
    ends = np.nonzero(edges == -1)[1]
    lengths = ends - starts
    keep = lengths >= minimum
    run_rows, starts, lengths = run_rows[keep], starts[keep], lengths[keep]

    open_runs: list[Run] = []
    done: list[Run] = []
    i = 0
    n = len(run_rows)
    for y in range(rows.shape[0]):
        nxt: list[Run] = []
        while i < n and run_rows[i] == y:
            x = int(starts[i])
            length = int(lengths[i])
            i += 1
            hit = False
            for k, o in enumerate(open_runs):
                if abs(o[0] - x) <= TOLERANCE and abs(o[2] - length) <= 2 * TOLERANCE:
                    x0 = min(o[0], x)
                    x1 = max(o[0] + o[2], x + length)
                    nxt.append([x0, o[1], x1 - x0, o[3] + 1])
                    del open_runs[k]
                    hit = True
                    break
            if not hit:
                nxt.append([x, y, length, 1])
        done.extend(open_runs)
        open_runs = nxt
    done.extend(open_runs)

    out: list[Run] = []
    height = rows.shape[0]
    for run in done:
        # thick runs are bars or filled areas and stay content
        if run[3] > thick:
            continue
        above = run[1] - 2
        below = run[1] + run[3] + 1
        flank = 0
        if above >= 0:
            flank += int(rows[above, run[0] : run[0] + run[2]].sum())
        if below < height:
            flank += int(rows[below, run[0] : run[0] + run[2]].sum())
        if flank > MAX_FLANK * 2 * run[2]:
            continue
        out.append(run)
    return out
