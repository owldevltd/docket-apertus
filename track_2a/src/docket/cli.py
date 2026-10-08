"""The command line.

    python -m docket analyze  --out <dir> <file.pdf | page.ppm> ...
    python -m docket read     --out <dir> <file.pdf> ...
    python -m docket document --out <dir> [--model] <file.pdf> ...

analyze writes per page <dir>/<name>-s<n>.json (the geometry and, from a PDF, the text of its text layer in the
elements), <name>-s<n>.png (the page) and <name>-s<n>-page.png (the control image). read does the same and then
reads the pages without a text layer with the model; the raw exchange lands in <dir>/<name>-s<n>.read/.
document runs the whole chain and writes <dir>/<name>.json, the affair record, with the pages under
<dir>/<name>/; with --model it reads scans, lets the model sort the leftover elements of the first pages and
asks the fields: <dir>/<name>-fields.json holds per field what became of it and the calls, <dir>/<name>-s<n>-
check.png shows the blocks of a first page with the ones holding a value (green: found by code, red: a person
has to look), <dir>/values.json the values that stood on the pages, per field with their count.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path

from docket.config import load_config
from docket.fields.fields import Fields
from docket.fields.placer import blocks_of, find_block
from docket.model.client import Client
from docket.page.analyze import analyze_page
from docket.page.painter import draw_blocks, draw_elements, draw_geometry
from docket.page.raster import write_png
from docket.page.render import render_pdf
from docket.pipeline import (
    build_document, fill_fields, first_pages, load_contract, load_field_file, load_knowledge, process_pages,
)
from docket.read.reader import read_page
from docket.text.layer import fill_text_layer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docket")
    commands = parser.add_subparsers(dest="command", required=True)
    helps = (
        ("analyze", "the geometry and the text layer of every page, without a model"),
        ("read", "analyze, then read pages without a text layer with the model"),
        ("document", "the whole document: pages, blocks, the affair record; --model reads scans and sorts the rest"),
    )
    for name, help_text in helps:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--out", required=True, help="directory for the results")
        if name == "document":
            command.add_argument("--model", action="store_true", help="use the model for scans and the rest")
        command.add_argument("files", nargs="+", help="PDF files, or page images as PPM/PGM")
    args = parser.parse_args(argv)
    if args.command == "document":
        return run_document(Path(args.out), [Path(f) for f in args.files], args.model)
    return run(args.command, Path(args.out), [Path(f) for f in args.files])


def run_document(out: Path, files: list[Path], with_model: bool) -> int:
    config = load_config()
    client = Client(config) if with_model else None
    if client is not None and not config.api_key:
        print("no API_KEY: copy .env.example to .env and fill it in", file=sys.stderr)
        return 1
    contract = load_contract(config)
    knowledge = load_knowledge(config)
    fields = load_field_file(config, contract)
    out.mkdir(parents=True, exist_ok=True)
    for pdf in files:
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            print(f"not a PDF: {pdf}", file=sys.stderr)
            continue
        started = time.monotonic()
        before = client.calls if client else 0
        pages_dir = out / pdf.stem
        pages_dir.mkdir(parents=True, exist_ok=True)
        keep: dict[int, object] = {}
        pages = process_pages(pdf, pages_dir, client, keep)
        record, report = build_document(pdf.stem, pages, knowledge, client, log=pages_dir / "sort.read")
        record, filled = fill_fields(record, pages, fields, contract, client, knowledge, log=pages_dir / "fields.read")
        errors = contract.check(record)
        (out / f"{pdf.stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(report["blocks"].items(), key=lambda item: -item[1]))
        calls = f"  {client.calls - before} calls" if client else ""
        state = "valid" if not errors else f"{len(errors)} violations, first: {errors[0]}"
        summary = ""
        if client is not None:
            summary = "  " + _fields_out(out, pdf.stem, record, pages, filled, fields, keep)
        print(
            f"{pdf.stem:<28} {len(pages)} pages  {sum(report['blocks'].values())} blocks ({kinds})"
            f"  rest {report['rest']}{calls}  {state}{summary}  {time.monotonic() - started:.0f}s"
        )
        if client is not None and client.halted:
            print(f"halted after HTTP {client.halted}", file=sys.stderr)
            return 2
    if client is not None:
        values = json.dumps({"values": knowledge.values}, ensure_ascii=False, indent=2) + "\n"
        (out / "values.json").write_text(values, encoding="utf-8")
    return 0


def _fields_out(out: Path, name: str, record: dict, pages: list[dict], filled: dict, fields: Fields,
                keep: dict) -> str:
    """Writes the fields report and the control images of the first pages; returns the states in a line."""
    first = first_pages(pages)
    text = json.dumps({"first": first, **filled}, ensure_ascii=False, indent=2) + "\n"
    (out / f"{name}-fields.json").write_text(text, encoding="utf-8")
    body = record["docs"]["data"][0]["body"]
    found: dict[str, str] = {}
    for field, r in filled["fields"].items():
        for item in r.get("items", []):
            if item["block"] is None:
                continue
            block = find_block(item["block"], body)
            flagged = bool(block and block.get("approve"))
            look = item["how"] not in ("literal", "derived") or fields.fields[field].free or flagged
            found[item["block"]] = "look" if look else found.get(item["block"], "ok")
    for n in first:
        if n in keep:
            draw_blocks(keep[n], out / f"{name}-s{n}-check.png", blocks_of(body), n, found)
    states: dict[str, int] = {}
    for r in filled["fields"].values():
        states[r["state"]] = states.get(r["state"], 0) + 1
    return f"fields {len(filled['fields'])}: " + ", ".join(f"{k} {v}" for k, v in sorted(states.items()))


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
