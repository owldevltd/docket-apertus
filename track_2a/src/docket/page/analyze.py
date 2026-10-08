"""One page image to its geometry: lines, tinted areas, text lines, tick marks, empty cells, objects, and the
typed element list with font size and colour. No text and no model here; that is the reading step."""

from __future__ import annotations

from pathlib import Path

from docket.page.elements import type_elements
from docket.page.joiner import join_lines
from docket.page.lines import find_lines
from docket.page.marks import find_cells, find_marks
from docket.page.mask import Page, load_page
from docket.page.slicer import find_areas, find_objects, measure_unit
from docket.page.styler import style_elements


def analyze_page(path: str | Path) -> tuple[Page, dict]:
    page = load_page(path)
    page.unit = measure_unit(page)
    lines = find_lines(page)
    areas = find_areas(page)
    marks = find_marks(page)
    cells = find_cells(page, lines)
    strips = join_lines(page, lines)
    objects = find_objects(page)
    elements = type_elements(page, lines, marks, areas, cells, objects)
    style_elements(page, elements, strips, marks)
    return page, {
        "file": page.file,
        "width": page.width,
        "height": page.height,
        "scale": page.scale,
        "paper": page.paper,
        "ink": page.ink,
        "unit": page.unit * page.scale,
        "lines": lines,
        "areas": areas,
        "strips": strips,
        "marks": marks,
        "cells": cells,
        "elements": elements,
        "objects": objects,
    }
