"""The bridge: the elements of a page become the blocks of the contract.

Only what can be decided without a model: an image, a table out of lines, a list item at the counter before it,
a label with its value beside it, a heading at the font size, a paragraph at its height. What no rule hits
stays in the rest until someone says what it is (`add`): the model, in the sorting step.
"""

from __future__ import annotations

import re

from docket.fluffy import join_lines

# from this multiple of the base font a text is a heading
HEAD = 1.3

# from this height in font sizes a text has more than one line and is a paragraph
TALL = 1.5

# lines that come within this share of the base font are connected
NEAR = 0.5

# a grid is a table only with this many lines, texts in it and columns; a stamp, a crest or a number box does
# not bring that (the first three are the project lead's values)
GRID_LINES = 6
GRID_TEXTS = 4
GRID_COLS = 2

# text in at least this share of the cells, and at most this many inkless elements for every text
GRID_FILL = 0.5
GRID_INK = 0.5

# tables of horizontal lines only: lines of the same length belong together within this many font sizes
GRID_ROW = 8.0

# between two columns nothing stands over the whole height, at least this many font sizes wide
GRID_GAP = 1.0

# a counter or bullet alone in an element: "1.", "4.2", "a)", "II.", "•"
MARK = re.compile(r"^(\(?\d{1,2}(\.\d{1,2})*[.)]?|\(?[a-zA-Z][.)]|[IVX]+\.|[•·▪■◦○\-–—*»])$")

# a label ends with a colon, holds a letter and is at most this long
TERM = 40

# two elements stand beside each other when the right one begins at most this many font sizes further right;
# list items belong to one list when their counters are flush and at most this many font sizes apart
BESIDE = 6.0
STACK = 4.0

# a section name stands alone in a short line: at most this many words
NAME_WORDS = 5

PAGE_PT = (595.0, 842.0)

BLOCK_KINDS = {"head", "p", "list", "def-list", "sig-block"}


class Knowledge:
    """What earlier documents taught: the section names, and the values that stood on the page per field,
    each with its count. Both grow with every find; the values are kept for a person to look at, not offered
    to the model (measured 6 October 2026: offered values bring more values that are not on the page)."""

    def __init__(self, sections: dict[str, int], values: dict[str, dict[str, int]] | None = None,
                 types: dict[str, dict] | None = None, forms: dict[str, dict[str, int]] | None = None,
                 bodies: dict[str, dict] | None = None):
        self.sections = dict(sections)
        self.values = {name: dict(seen) for name, seen in (values or {}).items()}
        # from the export of OpenParlData: the harmonised type per label, the number forms per parliament, and
        # the names of the parliaments (tools/knowledge.py)
        self.types = dict(types or {})
        self.forms = dict(forms or {})
        self.bodies = dict(bodies or {})

    def learn(self, values: dict[str, list[dict]]) -> None:
        """Counts the values that stood on the page, per field."""
        for name, hits in values.items():
            seen = self.values.setdefault(name, {})
            for hit in hits:
                v = hit["value"].strip()
                seen[v] = seen.get(v, 0) + 1

    def section(self, text: str) -> str | None:
        """The section name a short line begins with ("Begründung:", "2. Antrag der Kommission" → antrag)."""
        t = re.sub(r"^[\d.IVXA-Z]+[.)]\s+|\s*[:.]+$", "", text.strip()).strip().lower()
        if not t or len(t.split()) > NAME_WORDS:
            return None
        for name in self.sections:
            if t == name or t.startswith(name + " "):
                return name
        return None

    def count(self, name: str) -> None:
        self.sections[name] = self.sections.get(name, 0) + 1


def pixels_per_point(page: dict) -> float:
    return page["width"] / PAGE_PT[1 if page["width"] > page["height"] else 0]


def base_size(elements: list[dict]) -> float:
    """Base font of the page in points: the size most characters are set in."""
    chars: dict[float, int] = {}
    for e in elements:
        if e["type"] == "text" and e.get("fontSize"):
            key = float(round(float(e["fontSize"])))
            chars[key] = chars.get(key, 0) + len(e.get("content") or "")
    return max(chars.items(), key=lambda item: item[1])[0] if chars else 10.0


def build_blocks(pages: list[dict], knowledge: Knowledge) -> tuple[list[dict], list[dict]]:
    """Blocks of a document from its pages (1 ...), nested into sections with ids, and the rest: elements no
    rule placed, each with its page."""
    flat: list[dict] = []
    rest: list[dict] = []
    for n, page in enumerate(pages, 1):
        px = pixels_per_point(page)
        elements = join_lines(page["elements"], px, knowledge.section)
        page["elements"] = elements
        base = base_size(elements)
        tables, used = _tables(elements, base * px)
        pairs, more = _pairs(elements, used, base, px)
        found = tables + pairs
        used = used | more
        for i, e in enumerate(elements):
            if i in used or e["type"] == "line":
                continue
            size = float(e.get("fontSize") or 0)
            text = e.get("content") or ""
            if not text and e["type"] in ("image", "unknown"):
                found.append(_block("graphic", e))
            elif e["type"] == "text" and size >= HEAD * base:
                found.append(_head(e, text, knowledge.section(text)))
            elif e["type"] == "text" and knowledge.section(text) is not None:
                # a known section name in the base font ("Begründung:") is a heading as well
                found.append(_head(e, text, knowledge.section(text)))
            elif e["type"] == "text" and e["height"] > TALL * (size or base) * px:
                found.append(_block("p", e) | {"text": text})
            else:
                rest.append({"page": n, **e})
        for b in sorted(found, key=lambda b: (b["y"], b["x"])):
            flat.append({"page": n, **b})
    return _nest(flat, knowledge), rest


def add_blocks(
    body: list[dict], rest: list[dict], kinds: dict[int, str], knowledge: Knowledge
) -> tuple[list[dict], list[dict]]:
    """Takes elements of the rest in as blocks and orders the document anew. The kind comes from outside, the
    model; every element stays its own block, so its box stays the place."""
    flat: list[dict] = []
    for b in body:
        inside = b.get("content", []) if b["type"] == "sec" else None
        dropped = ("id", "content") if b["type"] == "sec" else ("id",)
        plain = {k: v for k, v in b.items() if k not in dropped}
        if b["type"] == "sec":
            plain["type"] = "head"
        flat.append(plain)
        for c in inside or []:
            flat.append({k: v for k, v in c.items() if k != "id"})
    left = []
    for i, e in enumerate(rest):
        kind = kinds.get(i)
        if kind is None:
            left.append(e)
            continue
        text = e.get("content") or ""
        block = {"page": e["page"], **_block(kind, e)}
        if kind == "head":
            block["title"] = text
        elif kind == "list":
            block["items"] = [text]
        elif kind == "def-list":
            block["items"] = [_pair(text)]
        else:
            block["text"] = text
        flat.append(block)
    flat.sort(key=lambda b: (b["page"], b["y"], b["x"]))
    return _nest(flat, knowledge), left


def _head(e: dict, text: str, sec_type: str | None) -> dict:
    block = _block("head", e) | {"title": text}
    if sec_type is not None:
        block["sec-type"] = sec_type
    return block


def _pair(text: str) -> dict:
    """Label and value from one line, split at the first colon."""
    at = text.find(":")
    if at < 0:
        return {"term": text.strip(), "def": ""}
    return {"term": text[:at].strip(), "def": text[at + 1 :].strip()}


def _tables(elements: list[dict], size: float) -> tuple[list[dict], set[int]]:
    """Tables: lines that cross or touch form a grid; it is a table only with enough lines, enough text in
    enough columns and text in most cells. Without vertical lines the columns come from the texts' left edges."""
    near = NEAR * size
    lines = {i: e for i, e in enumerate(elements) if e["type"] == "line"}
    group = {i: i for i in lines}

    def root(i: int) -> int:
        while group[i] != i:
            group[i] = group[group[i]]
            i = group[i]
        return i

    keys = list(lines)
    for a_i, i in enumerate(keys):
        a = lines[i]
        for j in keys[a_i + 1 :]:
            b = lines[j]
            touch = (a["x"] - near <= b["x"] + b["width"] and b["x"] - near <= a["x"] + a["width"]
                     and a["y"] - near <= b["y"] + b["height"] and b["y"] - near <= a["y"] + a["height"])
            # two horizontal lines of the same length beneath each other, with no vertical line joining them
            rule = (a["width"] > a["height"] and b["width"] > b["height"]
                    and abs(a["x"] - b["x"]) <= 2 * near and abs(a["x"] + a["width"] - b["x"] - b["width"]) <= 2 * near
                    and abs(a["y"] - b["y"]) <= GRID_ROW * size)
            if touch or rule:
                group[root(i)] = root(j)
    grids: dict[int, list[int]] = {}
    for i in keys:
        grids.setdefault(root(i), []).append(i)

    blocks = []
    used: set[int] = set()
    for ids in grids.values():
        if len(ids) < GRID_LINES:
            continue
        ys, xs = [], []
        x0 = y0 = float("inf")
        x1 = y1 = 0
        for i in ids:
            line = lines[i]
            if line["width"] >= line["height"]:
                ys.append(line["y"])
            else:
                xs.append(line["x"])
            x0, y0 = min(x0, line["x"]), min(y0, line["y"])
            x1, y1 = max(x1, line["x"] + line["width"]), max(y1, line["y"] + line["height"])
        inside = {i: e for i, e in enumerate(elements) if e["type"] != "line"
                  and x0 <= e["x"] + e["width"] / 2 <= x1 and y0 <= e["y"] + e["height"] / 2 <= y1}
        texts = {i: e for i, e in inside.items() if e.get("content")}
        if len(texts) < GRID_TEXTS or len(inside) - len(texts) > GRID_INK * len(texts):
            continue
        # edges from the lines; where they do not give two columns, from the texts' positions
        cols = _edges([x0, *xs, x1], near)
        rows_at = _edges([y0, *ys, y1], near)
        if len(cols) - 1 < GRID_COLS:
            cols = [x0, *_gaps(list(texts.values()), GRID_GAP * size), x1]
        if len(cols) - 1 < GRID_COLS:
            continue
        cells: list[list[list[str]]] = [[[] for _ in range(len(cols) - 1)] for _ in range(len(rows_at) - 1)]
        for e in texts.values():
            r = sum(1 for y in rows_at if y <= e["y"] + e["height"] / 2) - 1
            c = sum(1 for x in cols if x <= e["x"] + e["width"] / 2) - 1
            cells[min(r, len(rows_at) - 2)][min(c, len(cols) - 2)].append(e["content"])
        flat_cells = [cell for row in cells for cell in row]
        if sum(1 for cell in flat_cells if cell) < GRID_FILL * len(flat_cells):
            continue
        used.update(ids)
        used.update(inside)
        first = next(iter(texts.values()))
        block = {"type": "table-wrap", "x": int(x0), "y": int(y0), "width": int(x1 - x0), "height": int(y1 - y0)}
        block.update(_flags(list(texts.values())))
        block.update(_face(first))
        block["rows"] = [[" ".join(cell) for cell in row] for row in cells]
        blocks.append(block)
    return blocks, used


def _pairs(elements: list[dict], used: set[int], base: float, px: float) -> tuple[list[dict], set[int]]:
    """List items and labels out of two elements side by side: left a counter or bullet, right the text, a list
    item; left a label with a colon, right the value, a labelled value. A counter before a heading stays part
    of the heading. Consecutive items with flush counters become one list."""
    size = base * px
    items = []
    for i, left in enumerate(elements):
        if i in used or left["type"] != "text":
            continue
        text = (left.get("content") or "").strip()
        if MARK.match(text):
            kind = "list"
        elif text.endswith(":") and len(text) <= TERM and re.search(r"[^\W\d_]", text):
            kind = "def-list"
        else:
            continue
        right = None
        for j, e in enumerate(elements):
            mid = e["y"] + e["height"] / 2
            if j == i or j in used or e["type"] != "text" or not e.get("content"):
                continue
            if e["x"] < left["x"] + left["width"] - 0.5 * size or e["x"] > left["x"] + left["width"] + BESIDE * size:
                continue
            if mid < left["y"] - 0.5 * size or left["y"] + left["height"] / 2 > e["y"] + e["height"] + 0.5 * size:
                continue
            if mid > left["y"] + left["height"] + 0.5 * size and e["y"] > left["y"] + left["height"]:
                continue
            if right is None or e["x"] < elements[right]["x"]:
                right = j
        if right is None:
            continue
        e = elements[right]
        if kind == "list" and float(e.get("fontSize") or 0) >= HEAD * base:
            items.append({"kind": "head", "left": i, "right": right, "text": text + " " + e["content"].strip()})
            continue
        value = text + " " + e["content"].strip() if kind == "list" else e["content"].strip()
        items.append({"kind": kind, "left": i, "right": right, "text": value})
    items.sort(key=lambda it: (elements[it["left"]]["y"], elements[it["left"]]["x"]))

    blocks: list[dict] = []
    taken: set[int] = set()
    open_at = None
    for it in items:
        left, right = elements[it["left"]], elements[it["right"]]
        taken.update((it["left"], it["right"]))
        box = {"x": min(left["x"], right["x"]), "y": min(left["y"], right["y"])}
        box["width"] = max(left["x"] + left["width"], right["x"] + right["width"]) - box["x"]
        box["height"] = max(left["y"] + left["height"], right["y"] + right["height"]) - box["y"]
        if it["kind"] == "head":
            blocks.append({"type": "head", **box, **_flags([left, right]), **_face(right), "title": it["text"]})
            open_at = None
            continue
        item = it["text"] if it["kind"] == "list" else {"term": left["content"].strip().rstrip(":"), "def": it["text"]}
        # append to the open list when the same kind, flush and close beneath
        same_kind = open_at is not None and blocks[open_at]["type"] == it["kind"]
        flush = same_kind and abs(blocks[open_at]["x"] - box["x"]) <= size
        if flush and box["y"] - (blocks[open_at]["y"] + blocks[open_at]["height"]) <= STACK * size:
            b = blocks[open_at]
            b["width"] = max(b["x"] + b["width"], box["x"] + box["width"]) - b["x"]
            b["height"] = box["y"] + box["height"] - b["y"]
            b["items"].append(item)
            for flag, v in _flags([left, right]).items():
                b[flag] = bool(b.get(flag) or v)
            continue
        blocks.append({"type": it["kind"], **box, **_flags([left, right]), **_face(right), "items": [item]})
        open_at = len(blocks) - 1
    return blocks, taken


def _gaps(texts: list[dict], minimum: float) -> list[float]:
    """Column borders without lines: the middle of every gap in which nothing stands across all texts."""
    out = []
    end = None
    for e in sorted(texts, key=lambda e: e["x"]):
        if end is not None and e["x"] - end >= minimum:
            out.append((end + e["x"]) / 2)
        end = max(end or 0, e["x"] + e["width"])
    return out


def _edges(at: list[float], near: float) -> list[float]:
    """Edges of a grid: positions closer than `near` are the same edge."""
    out: list[float] = []
    for v in sorted(at):
        if not out or v - out[-1] > near:
            out.append(v)
    return out


def _block(kind: str, e: dict) -> dict:
    block = {"type": kind, "x": int(e["x"]), "y": int(e["y"]), "width": int(e["width"]), "height": int(e["height"])}
    block.update(_flags([e]))
    block.update(_face(e))
    return block


def _face(e: dict) -> dict:
    """The font of an element for the block, as far as the document gives it."""
    out = {}
    if e.get("font"):
        out["font"] = str(e["font"])
    if e.get("fontSize"):
        out["font-size"] = round(float(e["fontSize"]), 1)
    if isinstance(e.get("color"), str) and e["color"]:
        out["color"] = e["color"]
    return out


def _flags(from_elements: list[dict]) -> dict:
    """approve as soon as an element in the block should be looked at; isOCR as soon as one's text comes from
    a text recognition; without a note no isOCR."""
    out = {}
    if any(e.get("approve") for e in from_elements):
        out["approve"] = True
    ocr = [e["isOCR"] for e in from_elements if isinstance(e.get("isOCR"), bool)]
    if ocr:
        out["isOCR"] = any(ocr)
    return out


def _nest(flat: list[dict], knowledge: Knowledge) -> list[dict]:
    """A heading opens a section; what follows up to the next is its content. Then the ids in reading order."""
    body: list[dict] = []
    open_at = None
    for b in flat:
        if b["type"] == "head":
            section = {"type": "sec", **{k: v for k, v in b.items() if k != "type"}, "content": []}
            body.append(section)
            if "sec-type" in b:
                knowledge.count(b["sec-type"])
            open_at = len(body) - 1
        elif open_at is not None:
            body[open_at]["content"].append(b)
        else:
            body.append(b)
    n = 0
    out = []
    for b in body:
        n += 1
        block = {"id": f"b{n}", **b}
        if b["type"] == "sec":
            inner = []
            for c in b["content"]:
                n += 1
                inner.append({"id": f"b{n}", **c})
            block["content"] = inner
        out.append(block)
    return out
