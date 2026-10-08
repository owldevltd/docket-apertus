"""Text from the text layer of a PDF into the elements of a page.

A word belongs to the element whose box holds its centre (the smallest one when several do). With it the font
from the PDF: name, size in points and colour, per element the one of most characters; it replaces the estimate
from the image. If the page is a scan, the text layer comes from a text recognition; the elements then carry
isOCR. Without a text layer the page stays as it is, and the reading step handles it.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from docket.fluffy import hyphens

DPI = 300

# below this many words a page counts as having no text layer
WORDS = 20

# from this size on an image in the PDF is the page itself, the page thus a scan
SCAN = (1000, 1400)

# line height in points, to notice a line break inside an element
LINE = 10.0

ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'", "nbsp": " "}


def fill_text_layer(pdf: str | Path, n: int, page: dict) -> bool:
    """Fills the elements of page n (1 ...) with the PDF's text. False when the page has no text layer."""
    xml = _run(["pdftotext", "-bbox-layout", "-f", str(n), "-l", str(n), str(pdf), "-"])
    words = []
    pattern = r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>'
    for m in re.finditer(pattern, xml, re.S):
        x = (float(m.group(1)) + float(m.group(3))) / 2 * DPI / 72
        y = (float(m.group(2)) + float(m.group(4))) / 2 * DPI / 72
        words.append((x, y, _decode(m.group(5))))
    if len(words) < WORDS:
        return False

    scan = False
    for row in _run(["pdfimages", "-list", "-f", str(n), "-l", str(n), str(pdf)]).splitlines()[2:]:
        c = row.split()
        if len(c) > 4 and c[3].isdigit() and c[4].isdigit():
            scan = scan or (int(c[3]) >= SCAN[0] and int(c[4]) >= SCAN[1])

    elements = page["elements"]
    text: list[list[str]] = [[] for _ in elements]
    last_y: list[float | None] = [None] * len(elements)
    for x, y, t in words:
        best = None
        for i, e in enumerate(elements):
            if e["type"] == "line" or x < e["x"] or x > e["x"] + e["width"] or y < e["y"] or y > e["y"] + e["height"]:
                continue
            if best is None or e["width"] * e["height"] < elements[best]["width"] * elements[best]["height"]:
                best = i
        if best is not None:
            # a jump down is a line end; there the hyphens are healed
            previous = last_y[best]
            text[best].append(("\n" if previous is not None and y - previous > 0.6 * LINE * DPI / 72 else "") + t)
            last_y[best] = y

    fonts = _fonts(pdf, n, page["width"])
    for i, e in enumerate(elements):
        e["content"] = hyphens(re.sub(r" ?\n ?", "\n", " ".join(text[i])))
        if e["type"] == "unknown" and e["content"]:
            e["type"] = "text"
        if not e["content"]:
            continue
        e["isOCR"] = scan
        face = _face_of(e, fonts)
        if face:
            e["font"], e["fontSize"], e["color"] = face
    return True


def _face_of(e: dict, fonts: list[dict]) -> tuple[str, float, str] | None:
    """The font of the lines whose centre lies in the element; the one with most characters counts. When no
    centre lies in it (tight boxes of headings), lines that overlap the box count."""
    for loose in (False, True):
        seen: dict[tuple, int] = {}
        for line in fonts:
            if loose:
                across = line["x1"] > e["x"] and line["x0"] < e["x"] + e["width"]
                inside = across and line["y1"] > e["y"] and line["y0"] < e["y"] + e["height"]
            else:
                inside = e["x"] <= line["x"] <= e["x"] + e["width"] and e["y"] <= line["y"] <= e["y"] + e["height"]
            if inside:
                key = (line["font"], line["size"], line["color"])
                seen[key] = seen.get(key, 0) + line["chars"]
        if seen:
            return max(seen.items(), key=lambda item: item[1])[0]
    return None


def _fonts(pdf: str | Path, n: int, width: int) -> list[dict]:
    """The text lines of the page with their font, from pdftohtml: centre and box in pixels of the page image,
    font name without the embedding prefix ("AMMPZW+ArialMT" becomes "ArialMT", bold and italic appended),
    size in points, colour as #rrggbb, characters."""
    xml = _run(["pdftohtml", "-xml", "-i", "-f", str(n), "-l", str(n), "-stdout", str(pdf)])
    pm = re.search(r'<page [^>]*width="([\d.]+)"', xml)
    if not pm or float(pm.group(1)) <= 0:
        return []
    # pdftohtml works in its own measure; the page width gives the factor to the page image and to points
    to_px = width / float(pm.group(1))
    to_pt = 595.0 / float(pm.group(1))
    spec = {}
    for f in re.finditer(r'<fontspec id="(\d+)" size="([\d.]+)" family="([^"]*)" color="(#[0-9a-fA-F]{6})"', xml):
        family = re.sub(r"^[A-Z]{6}\+", "", f.group(3))
        spec[f.group(1)] = (family, round(float(f.group(2)) * to_pt, 1), f.group(4).lower())
    lines = []
    pattern = r'<text top="([\d.]+)" left="([\d.]+)" width="([\d.]+)" height="([\d.]+)" font="(\d+)">(.*?)</text>'
    for t in re.finditer(pattern, xml, re.S):
        plain = _decode(re.sub(r"<[^>]+>", "", t.group(6))).strip()
        if not plain or t.group(5) not in spec:
            continue
        font, size, color = spec[t.group(5)]
        font += (" fett" if "<b>" in t.group(6) else "") + (" kursiv" if "<i>" in t.group(6) else "")
        top, left, w, h = (float(t.group(k)) for k in (1, 2, 3, 4))
        lines.append(
            {
                "x": (left + w / 2) * to_px, "y": (top + h / 2) * to_px,
                "x0": left * to_px, "y0": top * to_px, "x1": (left + w) * to_px, "y1": (top + h) * to_px,
                "font": font, "size": size, "color": color, "chars": len(plain),
            }
        )
    return lines


def _run(command: list[str]) -> str:
    return subprocess.run(command, capture_output=True, text=True, errors="replace").stdout


def _decode(s: str) -> str:
    def one(m: re.Match) -> str:
        if m.group(2):
            return chr(int(m.group(2)))
        if m.group(3):
            return chr(int(m.group(3), 16))
        return ENTITIES.get(m.group(1), m.group(0))

    return re.sub(r"&(\w+|#(\d+)|#x([0-9a-fA-F]+));", one, s)
