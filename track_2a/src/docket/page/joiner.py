"""Bridges by the measure of the line instead of the page.

Every text line measures itself: character height, word gap, baseline. What then belongs to the same line or
the same paragraph gets a bridge in the mask before the slicer smears. Neighbourhoods of ink blobs as in
Docstrum (O'Gorman 1993).
"""

from __future__ import annotations

from docket.page.mask import Page, label

# character height of a line = the height of its tall characters (capitals, ascenders, digits); the median
# jumps between x-height and cap height depending on the text, this share does not
TALL = 0.9

# a gap within a line, in its own character height; measured: word gap 0.3 to 0.7, next column from about 2.1
WORD_GAP = 0.9
WORD_MAX = 1.5

# justified text: gaps up to this multiple of the line's median word gap
WORD_RATIO = 1.6

# from here a gap is a word gap, below it a letter gap
WORD_MIN = 0.25

# baseline distance to the next line of the same paragraph; measured: within a block 1.4 to 1.94, between
# blocks from 2.17 (document mode)
LINE_STEP = 2.05

# characters of a line, and lines of a paragraph, are of similar height
GLYPH_RATIO = 2.5
LINE_RATIO = 1.5

Glyph = tuple[int, int, int, int, int]  # x0, y0, x1, y1, height


def join_lines(page: Page, lines: list[dict]) -> list[dict]:
    """Lays the bridges into page.links and returns the text lines (strips) in original pixels."""
    page.links = []
    glyphs: list[Glyph] = []
    for b in label(page.masks["ink"]):
        h = b[3] - b[1] + 1
        if h * 2 < page.unit or b[2] - b[0] + 1 > 10 * h:
            continue
        glyphs.append((b[0], b[1], b[2], b[3], h))
    glyphs.sort(key=lambda g: g[0])

    strips = _strips(page, glyphs, lines)
    _stack(page, glyphs, strips, lines)

    s = page.scale
    out = []
    for t in strips:
        out.append(
            {
                "x": t["x0"] * s,
                "y": t["y0"] * s,
                "w": (t["x1"] - t["x0"] + 1) * s,
                "h": (t["y1"] - t["y0"] + 1) * s,
                "unit": t["h"] * s,
                "base": t["base"] * s,
                "n": len(t["glyphs"]),
            }
        )
    return sorted(out, key=lambda t: (t["y"], t["x"]))


def _strips(page: Page, g: list[Glyph], lines: list[dict]) -> list[dict]:
    """Characters to lines: every character hangs on its right neighbour at the same height. First collected
    generously, then the collection measures its own word gap and splits on it."""
    n = len(g)
    edges: list[tuple[int, int, int]] = []
    loose = list(range(n))
    for i in range(n):
        c = g[i]
        far = c[2] + 2 * WORD_MAX * GLYPH_RATIO * c[4]
        j = i + 1
        while j < n and g[j][0] <= far:
            r = g[j]
            j += 1
            if max(c[4], r[4]) > GLYPH_RATIO * min(c[4], r[4]):
                continue
            if (min(c[3], r[3]) - max(c[1], r[1]) + 1) * 2 < min(c[4], r[4]):
                continue
            # two small characters may stand in a line twice as high
            gap = max(0, r[0] - c[2] - 1)
            if gap <= 2 * WORD_MAX * max(c[4], r[4]):
                edges.append((i, j - 1, gap))
                loose[_root(loose, i)] = _root(loose, j - 1)
            # sorted by x: the first hit is the nearest
            break

    # per collection: character height and, from three word gaps on, its own word gap
    heights: dict[int, list[int]] = {}
    for i, c in enumerate(g):
        heights.setdefault(_root(loose, i), []).append(c[4])
    unit = {k: _part(v, TALL) for k, v in heights.items()}
    gaps: dict[int, list[int]] = {}
    for i, _, gap in edges:
        k = _root(loose, i)
        if gap >= WORD_MIN * unit[k]:
            gaps.setdefault(k, []).append(gap)

    tight = list(range(n))
    for i, j, gap in edges:
        k = _root(loose, i)
        limit = WORD_GAP * unit[k]
        if len(gaps.get(k, [])) >= 3:
            limit = min(WORD_MAX * unit[k], max(limit, WORD_RATIO * _part(gaps[k], 0.5)))
        if gap > limit:
            continue
        y = (max(g[i][1], g[j][1]) + min(g[i][3], g[j][3])) >> 1
        if gap >= WORD_MIN * unit[k] and _fenced(lines, page.scale, "v", g[i][2], g[j][0], y):
            continue
        tight[_root(tight, i)] = _root(tight, j)
        if gap > 0:
            page.links.append((g[i][0], y, g[j][2], y))

    sets: dict[int, list[int]] = {}
    for i in range(n):
        sets.setdefault(_root(tight, i), []).append(i)
    strips = []
    for ids in sets.values():
        strips.append(
            {
                "x0": min(g[i][0] for i in ids),
                "y0": min(g[i][1] for i in ids),
                "x1": max(g[i][2] for i in ids),
                "y1": max(g[i][3] for i in ids),
                "h": _part([g[i][4] for i in ids], TALL),
                "base": _part([g[i][3] for i in ids], 0.5),
                "glyphs": ids,
            }
        )
    return strips


def _stack(page: Page, g: list[Glyph], strips: list[dict], lines: list[dict]) -> None:
    """Lines to paragraphs: the next line below belongs when its baseline distance in character heights is
    small enough. Baseline instead of box, because the box depends on whether the line has descenders."""
    ordered = sorted(strips, key=lambda t: t["base"])
    n = len(ordered)
    for i in range(n):
        a = ordered[i]
        nxt = None
        for j in range(i + 1, n):
            b = ordered[j]
            step = b["base"] - a["base"]
            if step > LINE_STEP * a["h"] or (nxt is not None and step > nxt + a["h"] / 2):
                break
            if step * 2 < min(a["h"], b["h"]):
                continue
            over = min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]) + 1
            if over * 2 <= min(a["x1"] - a["x0"], b["x1"] - b["x0"]) + 1:
                continue
            # only the next line counts, even when it does not fit itself
            if nxt is None:
                nxt = step
            if max(a["h"], b["h"]) > LINE_RATIO * min(a["h"], b["h"]):
                continue
            if step > LINE_STEP * min(a["h"], b["h"]):
                continue
            _post(page, g, a["glyphs"], b["glyphs"], lines)


def _post(page: Page, g: list[Glyph], above: list[int], below: list[int], lines: list[dict]) -> None:
    """A vertical bridge between two lines: through a character above and one below that stand over each
    other. Every blob has ink in each of its columns, so the bridge hits both."""
    for i in above:
        for j in below:
            x0 = max(g[i][0], g[j][0])
            x1 = min(g[i][2], g[j][2])
            if x0 > x1 or g[j][1] <= g[i][3]:
                continue
            x = (x0 + x1) >> 1
            if _fenced(lines, page.scale, "h", g[i][3], g[j][1], x):
                return
            page.links.append((x, g[i][1], x, g[j][3]))
            return


def _fenced(lines: list[dict], s: int, direction: str, start: int, end: int, at: int) -> bool:
    """Is there a line across the bridge between start and end? Lines are scaffolding: nothing belongs
    together across a table line. Work pixels in, original pixels on the lines."""
    for line in lines:
        if line["dir"] != direction:
            continue
        if direction == "v":
            pos, lo, hi = line["x"], line["y"], line["y"] + line["h"]
        else:
            pos, lo, hi = line["y"], line["x"], line["x"] + line["w"]
        if start * s <= pos <= end * s and lo <= at * s <= hi:
            return True
    return False


def _part(values: list[int], p: float) -> int:
    """The value at share p of the sorted list, 0.5 = the median."""
    ordered = sorted(values)
    return ordered[int(p * (len(ordered) - 1))]


def _root(parent: list[int], k: int) -> int:
    while parent[k] != k:
        parent[k] = parent[parent[k]]
        k = parent[k]
    return k
