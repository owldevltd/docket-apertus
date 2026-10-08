"""Pages of a PDF as images, through poppler's pdftoppm at 300 dpi. The input is always the PDF."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

DPI = 300


def render_pdf(pdf: str | Path, out_dir: str | Path, name: str) -> list[tuple[int, Path]]:
    """Writes <out_dir>/<name>-<n>.ppm per page and returns (page number, path) in page order."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prefix = out / name
    subprocess.run(["pdftoppm", "-r", str(DPI), str(pdf), str(prefix)], check=True, capture_output=True)
    pages = []
    for file in out.glob(f"{name}-*.ppm"):
        m = re.search(r"-(\d+)\.ppm$", file.name)
        if m:
            pages.append((int(m.group(1)), file))
    return sorted(pages)


def page_count(pdf: str | Path) -> int:
    info = subprocess.run(["pdfinfo", str(pdf)], check=True, capture_output=True, text=True).stdout
    m = re.search(r"^Pages:\s+(\d+)", info, re.MULTILINE)
    return int(m.group(1)) if m else 0
