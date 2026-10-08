"""The command line.

    python -m docket analyze --out <dir> <file.pdf | page.ppm> ...

analyze writes per page <dir>/<name>-s<n>.json (the geometry), <name>-s<n>.png (the page) and
<name>-s<n>-page.png (the control image). A PDF is rendered through poppler first; a PPM or PGM is one page.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from docket.page.analyze import analyze_page
from docket.page.painter import draw_geometry
from docket.page.raster import write_png
from docket.page.render import render_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docket")
    commands = parser.add_subparsers(dest="command", required=True)
    analyze = commands.add_parser("analyze", help="the geometry of every page, without a model")
    analyze.add_argument("--out", required=True, help="directory for the results")
    analyze.add_argument("files", nargs="+", help="PDF files, or page images as PPM/PGM")
    args = parser.parse_args(argv)
    if args.command == "analyze":
        return run_analyze(Path(args.out), [Path(f) for f in args.files])
    return 1


def run_analyze(out: Path, files: list[Path]) -> int:
    out.mkdir(parents=True, exist_ok=True)
    for file in files:
        if not file.is_file():
            print(f"not found: {file}", file=sys.stderr)
            continue
        if file.suffix.lower() == ".pdf":
            with tempfile.TemporaryDirectory() as tmp:
                for n, image in render_pdf(file, tmp, file.stem):
                    _one(out, f"{file.stem}-s{n}", image, keep_page=True)
        else:
            _one(out, file.stem, file, keep_page=False)
    return 0


def _one(out: Path, name: str, image: Path, keep_page: bool) -> None:
    started = time.monotonic()
    page, result = analyze_page(image)
    (out / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draw_geometry(page.rgb, out / f"{name}-page.png", result)
    if keep_page:
        write_png(out / f"{name}.png", page.rgb)
    print(
        f"{name:<40} {page.width}x{page.height}  paper {page.paper}  unit {result['unit']} px"
        f"  lines {len(result['lines'])}  areas {len(result['areas'])}  objects {len(result['objects'])}"
        f"  {time.monotonic() - started:.1f}s"
    )
