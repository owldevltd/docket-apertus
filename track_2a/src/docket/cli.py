"""The command line.

    python -m docket analyze  --out <dir> <file.pdf | page.ppm> ...
    python -m docket read     --out <dir> <file.pdf> ...
    python -m docket document --out <dir> [--model] <file.pdf> ...
    python -m docket affairs  --out <dir> [--model] <file.pdf> ...
    python -m docket serve    [--port <n>]

analyze writes per page <dir>/<name>-s<n>.json (the geometry and, from a PDF, the text of its text layer in the
elements), <name>-s<n>.png (the page) and <name>-s<n>-page.png (the control image). read does the same and then
reads the pages without a text layer with the model; the raw exchange lands in <dir>/<name>-s<n>.read/.
document runs the whole chain and writes <dir>/<name>.json, the affair record, with the pages under
<dir>/<name>/; with --model it reads scans, lets the model sort the leftover elements of the first pages and
asks the fields: <dir>/<name>-fields.json holds per field what became of it, the calls and the identity,
<dir>/<name>-s<n>-check.png shows the blocks of a first page with the ones holding a value (green: found by
code, red: a person has to look), <dir>/values.json the values that stood on the pages, per field with their
count. affairs does the same for every PDF and then folds the documents with the same key into one affair:
<dir>/affairs/<key>.json per affair and <dir>/affairs.ndjson with all of them; the affairs also go into the
store (files under the storage folder, or Postgres with DATABASE_URL), where a run over a document that is
already there keeps every decision a person took. serve starts the web server over the store.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from docket.config import load_config
from docket.model.client import Client
from docket.page.analyze import analyze_page
from docket.page.painter import draw_elements, draw_geometry
from docket.page.raster import write_png
from docket.page.render import render_pdf
from docket.read.reader import read_page
from docket.runner import run_affairs
from docket.server import start
from docket.text.layer import fill_text_layer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docket")
    commands = parser.add_subparsers(dest="command", required=True)
    helps = (
        ("analyze", "the geometry and the text layer of every page, without a model"),
        ("read", "analyze, then read pages without a text layer with the model"),
        ("document", "the whole document: pages, blocks, the affair record; --model reads scans and asks the fields"),
        ("affairs", "document for every PDF, then one affair per key with its documents, into the store"),
    )
    for name, help_text in helps:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--out", required=True, help="directory for the results")
        if name in ("document", "affairs"):
            command.add_argument("--model", action="store_true", help="use the model for scans, the rest, the fields")
        command.add_argument("files", nargs="+", help="PDF files, or page images as PPM/PGM")
    web = commands.add_parser("serve", help="the web server over the store")
    web.add_argument("--port", type=int, default=None, help="port, default PORT or 8080")
    args = parser.parse_args(argv)
    if args.command == "serve":
        return run_server(args.port)
    if args.command in ("document", "affairs"):
        return run_documents(Path(args.out), [Path(f) for f in args.files], args.model, args.command == "affairs")
    return run(args.command, Path(args.out), [Path(f) for f in args.files])


def run_server(port: int | None) -> int:
    config = load_config()
    server, app = start(config, port)
    print(f"docket serves on http://localhost:{server.server_address[1]} over the {app.store.kind} store")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.jobs.stop()
    return 0


def run_documents(out: Path, files: list[Path], with_model: bool, affairs: bool) -> int:
    config = load_config()
    if with_model and not config.api_key:
        print("no API_KEY: copy .env.example to .env and fill it in", file=sys.stderr)
        return 1
    result = run_affairs(files, out, config, with_model, merge_affairs=affairs)
    if result.halted:
        return 2
    return 1 if result.failed else 0


def run(command: str, out: Path, files: list[Path]) -> int:
    out.mkdir(parents=True, exist_ok=True)
    client = Client(load_config()) if command == "read" else None
    if client is not None and not client.config.api_key:
        print("no API_KEY: copy .env.example to .env and fill it in", file=sys.stderr)
        return 1
    for file in files:
        if not file.is_file():
            print(f"not found: {file}", file=sys.stderr)
            continue
        if file.suffix.lower() == ".pdf":
            with tempfile.TemporaryDirectory() as tmp:
                for n, image in render_pdf(file, tmp, file.stem):
                    _one(out, f"{file.stem}-s{n}", image, pdf=file, n=n, client=client)
        else:
            _one(out, file.stem, file, pdf=None, n=0, client=client)
        if client is not None and client.halted:
            print(f"halted after HTTP {client.halted}", file=sys.stderr)
            return 2
    return 0


def _one(out: Path, name: str, image: Path, pdf: Path | None, n: int, client: Client | None) -> None:
    started = time.monotonic()
    page, result = analyze_page(image)
    result["textLayer"] = fill_text_layer(pdf, n, result) if pdf is not None else False
    calls = 0
    if client is not None and not result["textLayer"]:
        calls = read_page(client, page.rgb, page.gray, result, log=out / f"{name}.read")
    (out / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    draw_geometry(page.rgb, out / f"{name}-page.png", result)
    if result["textLayer"] or calls:
        draw_elements(page.rgb, out / f"{name}-elements.png", result["elements"])
    if pdf is not None:
        write_png(out / f"{name}.png", page.rgb)
    texts = sum(1 for e in result["elements"] if e["type"] == "text")
    print(
        f"{name:<40} {page.width}x{page.height}  unit {result['unit']} px"
        f"  lines {len(result['lines'])}  objects {len(result['objects'])}  text {texts}"
        f"  {'layer' if result['textLayer'] else 'no layer'}{f'  {calls} calls' if calls else ''}"
        f"  {time.monotonic() - started:.1f}s"
    )
