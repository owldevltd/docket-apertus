"""The reference per page of a shipped document, in the shape the tests read.

Words with poppler's line and block from the text layer (pdftotext -bbox-layout), the ink box of every word
measured on the rendered page, and the raster images placed on the page (pdftohtml -xml). A preparation step,
run once; the results are committed beside the PDF. Needs poppler; the app does not.

    python3 tools/reference.py [data/documents/<id> ...]        default: every folder in data/documents
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.page.mask import load_page  # noqa: E402
from docket.page.raster import QUANTUM  # noqa: E402
from docket.page.render import render_pdf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}


def main(folders: list[Path]) -> None:
    for folder in folders:
        meta = json.loads((folder / "document.json").read_text(encoding="utf-8"))
        pdf = next(folder.glob("*.pdf"))
        with tempfile.TemporaryDirectory() as tmp:
            for n, image in render_pdf(pdf, tmp, pdf.stem):
                page = load_page(image)
                ink = page.gray_q <= page.ink * QUANTUM
                words = words_of(pdf, n, page.width, page.height, ink)
                images = images_of(pdf, n, page.width, page.height, ink, tmp)
                ref = {
                    "source": str(pdf.relative_to(ROOT)),
                    "page": n,
                    "kind": "document" if words else "scan",
                    "lang": meta.get("language", "de"),
                    "dpi": 300,
                    "width": page.width,
                    "height": page.height,
                    "words": words,
                    "images": images,
                }
                target = folder / f"{pdf.stem}-s{n}.json"
                target.write_text(json.dumps(ref, ensure_ascii=False), encoding="utf-8")
                size = f"{page.width}x{page.height}"
                print(f"{target.name:<36} {size}  {len(words)} words  {len(images)} images  {ref['kind']}")


def words_of(pdf: Path, n: int, width: int, height: int, ink) -> list[dict]:
    """Words with the font box from the text layer and the box of what is dark inside it."""
    xml = subprocess.run(
        ["pdftotext", "-bbox-layout", "-f", str(n), "-l", str(n), str(pdf), "-"], capture_output=True, text=True
    ).stdout
    size = re.search(r'<page width="([\d.]+)" height="([\d.]+)"', xml)
    if not size:
        return []
    fx = width / float(size.group(1))
    fy = height / float(size.group(2))
    words = []
    block = -1
    line = -1
    pattern = (
        r'<(block|line|word) xMin="([-\d.]+)" yMin="([-\d.]+)" xMax="([-\d.]+)" yMax="([-\d.]+)">'
        r"(?:([^<]*)</word>)?"
    )
    for m in re.finditer(pattern, xml):
        if m.group(1) == "block":
            block += 1
            continue
        if m.group(1) == "line":
            line += 1
            continue
        x = round(float(m.group(2)) * fx)
        y = round(float(m.group(3)) * fy)
        w = round(float(m.group(4)) * fx) - x
        h = round(float(m.group(5)) * fy) - y
        if w < 1 or h < 1:
            continue
        word = {"x": x, "y": y, "w": w, "h": h, "t": decode(m.group(6) or ""), "line": line, "block": block}
        word["ink"] = ink_box(ink, x, y, w, h)
        words.append(word)
    return words


def images_of(pdf: Path, n: int, width: int, height: int, ink, tmp: str) -> list[dict]:
    """Raster images the PDF places on the page; pdftohtml names their position only when it writes them out."""
    prefix = Path(tmp) / f"html-{n}"
    command = ["pdftohtml", "-xml", "-q", "-zoom", "1", "-f", str(n), "-l", str(n), str(pdf), str(prefix)]
    subprocess.run(command, capture_output=True)
    xml_file = Path(str(prefix) + ".xml")
    if not xml_file.is_file():
        return []
    xml = xml_file.read_text(encoding="utf-8", errors="replace")
    size = re.search(r'<page [^>]*height="(\d+)" width="(\d+)"', xml)
    if not size:
        return []
    fx = width / int(size.group(2))
    fy = height / int(size.group(1))
    images = []
    pattern = r'<image top="(-?\d+)" left="(-?\d+)" width="(\d+)" height="(\d+)"'
    for m in re.finditer(pattern, xml):
        x = round(int(m.group(2)) * fx)
        y = round(int(m.group(1)) * fy)
        w = round(int(m.group(3)) * fx)
        h = round(int(m.group(4)) * fy)
        if w < 1 or h < 1:
            continue
        images.append({"x": x, "y": y, "w": w, "h": h, "ink": ink_box(ink, x, y, w, h)})
    return images


def ink_box(ink, x: int, y: int, w: int, h: int) -> dict | None:
    """The box of the dark pixels inside a box, or None when nothing dark is there."""
    x0, y0 = max(0, x), max(0, y)
    part = ink[y0 : max(y0, y + h), x0 : max(x0, x + w)]
    if part.size == 0 or not part.any():
        return None
    rows = part.any(axis=1).nonzero()[0]
    cols = part.any(axis=0).nonzero()[0]
    return {
        "x": x0 + int(cols[0]),
        "y": y0 + int(rows[0]),
        "w": int(cols[-1] - cols[0] + 1),
        "h": int(rows[-1] - rows[0] + 1),
    }


def decode(s: str) -> str:
    """XML entities back to characters."""

    def one(m: re.Match) -> str:
        if m.group(2):
            return chr(int(m.group(2)))
        if m.group(3):
            return chr(int(m.group(3), 16))
        return ENTITIES[m.group(1)]

    return re.sub(r"&(amp|lt|gt|quot|apos|#(\d+)|#x([0-9a-fA-F]+));", one, s)


if __name__ == "__main__":
    chosen = [Path(a) for a in sys.argv[1:]] or sorted(p for p in (ROOT / "data" / "documents").iterdir() if p.is_dir())
    main(chosen)
