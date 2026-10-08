"""Fluffy: repairs by code and the check of read text against the image.

Repairs: hyphens at line ends are healed ("Zu-" + "ständigkeit"); lines of a paragraph become one element
(later step). The check: what the model read is held against the image, not pixel by pixel, since the typeface
is unknown, but by the shape of the character sequence: per glyph tall, x-high, with descender, dot, dash, and
the word gaps. "bestätigt" and "bestellt" have different shapes in any typeface. The shape of the image comes
from its ink blobs, the shape of the text from its letters, so nothing is rendered. Where the two sequences
differ beyond the threshold the element gets approve and a person has to look.
"""

from __future__ import annotations

import re

import numpy as np

from docket.page.mask import label

# above this deviation (share of the shape sequence that does not match) a person must confirm; measured
# 6 October 2026 on 172 read elements of documents: 0.01 flags 61 of 71 wrong and 30 of 101 right readings
THRESHOLD = 0.01

# ink is clearly darker than the ground of the crop, but at most this grey value
INK_MAX = 160
INK_DIST = 60

# shape, all in shares of the tall glyphs of the line: from TALL tall, from SMALL x-high, below that
# punctuation; from DESCENT below the baseline a descender; from GAP a word gap
TALL = 0.85
SMALL = 0.5
DESCENT = 0.15
GAP = 0.3

# a blob this many character heights long and thin is a line
RULE = 2.5

# more ink than this in the crop: the writing stands light on a bar
INVERSE = 0.5

# before these words a hyphen at the line end stays ("Bau- und Verkehrsdepartement")
KEEP = ["und", "oder", "bzw.", "sowie", "resp.", "beziehungsweise"]

# two lines belong to the same paragraph when they stand flush left within this share of the font size, their
# top edges lie at most this many font sizes apart and the font size is the same within this share; STEP from
# the distribution on 72 first pages: lines of a paragraph at 2.0 to 2.5, paragraphs start from 3.25
FLUSH = 0.5
STEP = 2.75
SIZE = 0.15

# a short first line before a long one is a heading, not the start of a paragraph: at most this many words and
# narrower than this share of the next line
HEAD_WORDS = 4
HEAD_WIDTH = 0.6

# a counter or bullet left of a line (up to this many font sizes away) makes it a list item, not a next line
MARK = re.compile(r"^(\(?\d{1,2}(\.\d{1,2})*[.)]?|\(?[a-zA-Z][.)]|[IVX]+\.|[•·▪■◦○\-–—*»])$")
BESIDE = 6.0


def join_lines(elements: list[dict], px: float, section) -> list[dict]:
    """Joins text elements that are lines of the same paragraph into one element, in reading order. `section`
    says whether a text is a known section name, which stays a heading."""
    ordered = sorted(elements, key=lambda e: (e["y"], e["x"]))
    out: list[dict] = []
    for e in ordered:
        if out and _follows(out[-1], e, px, section) and not _marked(e, ordered, px):
            p = out[-1]
            p["content"] = hyphens(p["content"] + "\n" + e["content"])
            right = max(p["x"] + p["width"], e["x"] + e["width"])
            p["x"] = min(p["x"], e["x"])
            p["width"] = right - p["x"]
            p["height"] = e["y"] + e["height"] - p["y"]
            for flag in ("approve", "isOCR"):
                if flag in p or flag in e:
                    p[flag] = bool(p.get(flag) or e.get(flag))
            continue
        out.append(dict(e))
    for e in out:
        if isinstance(e.get("content"), str):
            e["content"] = e["content"].replace("\n", " ")
    return out


def _follows(p: dict, e: dict, px: float, section) -> bool:
    """Whether e is the next line of the paragraph that ends with p."""
    if p["type"] != "text" or e["type"] != "text" or not p.get("content") or not e.get("content"):
        return False
    size = float(p.get("fontSize") or 0)
    nxt = float(e.get("fontSize") or 0)
    if size <= 0 or nxt <= 0 or abs(size - nxt) > SIZE * size:
        return False
    # a heading (a known section name, or a short line before a long one) stays on its own
    words = len(p["content"].split())
    if section(p["content"]) is not None or (words <= HEAD_WORDS and p["width"] < HEAD_WIDTH * e["width"]):
        return False
    # a line ending in a colon introduces what follows (a quote, a list); that is a new block
    if p["content"].rstrip().endswith(":") and e["content"].lstrip()[:1].isupper():
        return False
    # the top edge of the last line of the paragraph so far: one line up from its bottom
    top = p["y"] + p["height"] - min(p["height"], e["height"])
    return abs(e["x"] - p["x"]) <= FLUSH * size * px and e["y"] > top and e["y"] - top <= STEP * size * px


def _marked(e: dict, all_elements: list[dict], px: float) -> bool:
    """Whether a counter or bullet stands left of the line."""
    size = float(e.get("fontSize") or 10) * px
    for o in all_elements:
        if o["type"] != "text" or not MARK.match((o.get("content") or "").strip()):
            continue
        mid = o["y"] + o["height"] / 2
        right = o["x"] + o["width"]
        beside = right <= e["x"] + 0.5 * size and e["x"] - right <= BESIDE * size
        if beside and e["y"] - 0.5 * size <= mid <= e["y"] + e["height"] + 0.5 * size:
            return True
    return False


def hyphens(text: str) -> str:
    """Heals hyphens at line ends: "Zu-\\nständigkeit" becomes "Zuständigkeit" when the next line continues in
    lower case and no connecting word follows. Other line breaks become spaces."""
    keep = "|".join(re.escape(w) for w in KEEP)
    text = re.sub(r"(?<=[^\W\d_])-\n(?!(?:" + keep + r")\b)(?=[^\W\d_])(?=[a-zäöüàâéèêëîïôûùç])", "", text)
    return text.replace("\n", " ")


def check_elements(elements: list[dict], gray: np.ndarray, threshold: float = THRESHOLD) -> None:
    """Sets approve on every read element: true where the read text does not fit the image or nothing was
    read. An image is not checked, a logo has no letter shape. Tick marks are blanked before the comparison."""
    blank = [
        {"x": e["x"] - 2, "y": e["y"] - 2, "w": e["width"] + 4, "h": e["height"] + 4}
        for e in elements
        if e["type"] in ("checkbox", "radio")
    ]
    for e in elements:
        if not e.get("isOCR"):
            continue
        if e["type"] != "text" or not e.get("content"):
            e["approve"] = e["type"] != "image"
            continue
        seen = shape_of_image(gray, e, blank)
        want = shape_of_text(e["content"])
        n = max(len(seen), len(want))
        e["deviation"] = round(levenshtein(seen, want) / n, 3) if n else 0.0
        e["approve"] = e["deviation"] > threshold


def shape_of_image(gray: np.ndarray, e: dict, blank: list[dict] | None = None) -> str:
    """Shape sequence of a crop with text: one letter per glyph. A tall, x x-high, J tall with descender, g
    x-high with descender, . low, ' high, - middle, _ word gap."""
    mask = _crop_mask(gray, e, blank or [])
    if mask is None:
        return ""
    boxes = [b for b in label(mask) if b[4] >= 3]
    if not boxes:
        return ""
    heights = sorted(b[3] - b[1] + 1 for b in boxes)
    typical = heights[int(0.75 * (len(heights) - 1))]

    # lines in the crop (cell borders, writing lines) are not glyphs; a corner or frame is big but nearly empty
    kept = []
    for b in boxes:
        w = b[2] - b[0] + 1
        h = b[3] - b[1] + 1
        if (w > RULE * typical and h * 3 < typical) or (h > RULE * typical and w * 3 < typical):
            continue
        if (w > RULE * typical or h > RULE * typical) and b[4] * 6 < w * h:
            continue
        kept.append(b)
    if not kept:
        return ""

    # lines: the centres of the larger blobs, separated where they jump by more than half a blob height
    big = sorted((b for b in kept if (b[3] - b[1] + 1) * 2 >= typical), key=lambda b: b[1] + b[3])
    bands: list[dict] = []
    for b in big:
        mid = (b[1] + b[3]) / 2
        if bands and mid - bands[-1]["mid"] <= 0.6 * typical:
            band = bands[-1]
            band["mid"] = (band["mid"] * band["n"] + mid) / (band["n"] + 1)
            band["n"] += 1
        else:
            bands.append({"mid": mid, "n": 1, "boxes": []})
    if not bands:
        return ""
    # every blob, dots and commas too, to the nearest line
    for b in kept:
        mid = (b[1] + b[3]) / 2
        best = min(range(len(bands)), key=lambda k: abs(mid - bands[k]["mid"]))
        bands[best]["boxes"].append(b)
    return "_".join(s for s in (_shape_of_line(band["boxes"]) for band in bands) if s)


def _shape_of_line(boxes: list) -> str:
    """Shape of one line. Blobs on top of each other (i and its dot, umlaut, colon) are one glyph: when they
    share most of their width, or when a small blob stands over or under a larger one and touches its width."""
    glyphs: list[list[int]] = []
    for b in sorted(boxes, key=lambda b: b[0]):
        if glyphs:
            g = glyphs[-1]
            over = min(g[2], b[2]) - max(g[0], b[0]) + 1
            stacked = b[1] > g[3] or b[3] < g[1]
            small = min(g[3] - g[1], b[3] - b[1]) * 2 <= max(g[3] - g[1], b[3] - b[1])
            if over * 2 > min(g[2] - g[0], b[2] - b[0]) + 1 or (over >= 1 and stacked and small):
                glyphs[-1] = [min(g[0], b[0]), min(g[1], b[1]), max(g[2], b[2]), max(g[3], b[3])]
                continue
        glyphs.append([b[0], b[1], b[2], b[3]])
    # baseline = where most glyphs end; tall = the tall glyphs above it
    bottoms = sorted(g[3] for g in glyphs)
    base = bottoms[len(bottoms) // 2]
    up = sorted(base - g[1] + 1 for g in glyphs)
    tall = max(1, up[int(0.9 * (len(up) - 1))])

    s = ""
    last = None
    for g in glyphs:
        if last is not None and g[0] - last - 1 >= GAP * tall:
            s += "_"
        last = g[2]
        h = base - g[1] + 1
        deep = g[3] - base >= DESCENT * tall
        if g[3] - g[1] + 1 < SMALL * tall:
            # small: low (dot, comma), high (apostrophe, quote) or in the middle (hyphen)
            s += "." if g[1] > base - SMALL * tall else ("'" if g[3] < base - SMALL * tall else "-")
        elif h >= TALL * tall:
            s += "J" if deep else "A"
        else:
            s += "g" if deep else "x"
    return s


def shape_of_text(text: str) -> str:
    """The shape a text would have in print, letter by letter, as the image side would see it."""
    lines = [line.strip() for line in text.replace("\t", " ").splitlines()]
    out = []
    for line in lines:
        s = ""
        gap = False
        for ch in line:
            if ch.isspace():
                gap = True
                continue
            if gap and s:
                s += "_"
            gap = False
            s += _glyph_class(ch)
        if s:
            out.append(s)
    return "_".join(out)


def _glyph_class(ch: str) -> str:
    if ch in ".,-–—_":
        return "."
    if ch in "'\"`´‘’“”*°":
        return "'"
    if ch in "=~":
        return "-"
    if ch in "gpqyµç;":
        return "g"
    # in sans faces J and the slash sit on the baseline; brackets and the section sign hang below it
    if ch in "jQ()[]{}|§@":
        return "J"
    if "a" <= ch <= "z":
        return "A" if ch in "bdfhiklt" else "x"
    if ch in ":<>«»+":
        return "x"
    if ch.isupper() or ch.isdigit() or ch in "ß!?%&#€$£/\\":
        return "A"
    return "x"


def _crop_mask(gray: np.ndarray, e: dict, blank: list[dict]) -> np.ndarray | None:
    """Ink mask of a crop at full resolution. The ground is the most frequent grey value; if it is dark, the
    writing is the light part."""
    height, width = gray.shape
    x0 = max(0, e["x"])
    y0 = max(0, e["y"])
    w = min(width - x0, max(1, e["width"]))
    h = min(height - y0, max(1, e["height"]))
    if w < 1 or h < 1:
        return None
    crop = gray[y0 : y0 + h, x0 : x0 + w]
    ground = int(np.argmax(np.bincount(crop.ravel(), minlength=256)))
    if ground >= 128:
        mask = crop < min(INK_MAX, ground - INK_DIST)
    else:
        mask = crop > ground + INK_DIST
    if mask.sum() > INVERSE * w * h:
        mask = ~mask
    mask = mask.copy()
    for b in blank:
        rows = slice(max(0, b["y"] - y0), max(0, b["y"] + b["h"] - y0))
        cols = slice(max(0, b["x"] - x0), max(0, b["x"] + b["w"] - x0))
        mask[rows, cols] = False
    return mask


def levenshtein(a: str, b: str) -> int:
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]
