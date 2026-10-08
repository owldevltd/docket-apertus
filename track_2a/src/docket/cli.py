"""The command line.

    python -m docket analyze  --out <dir> <file.pdf | page.ppm> ...
    python -m docket read     --out <dir> <file.pdf> ...
    python -m docket document --out <dir> [--model] <file.pdf> ...
    python -m docket affairs  --out <dir> [--model] <file.pdf> ...

analyze writes per page <dir>/<name>-s<n>.json (the geometry and, from a PDF, the text of its text layer in the
elements), <name>-s<n>.png (the page) and <name>-s<n>-page.png (the control image). read does the same and then
reads the pages without a text layer with the model; the raw exchange lands in <dir>/<name>-s<n>.read/.
document runs the whole chain and writes <dir>/<name>.json, the affair record, with the pages under
<dir>/<name>/; with --model it reads scans, lets the model sort the leftover elements of the first pages and
asks the fields: <dir>/<name>-fields.json holds per field what became of it, the calls and the identity,
<dir>/<name>-s<n>-check.png shows the blocks of a first page with the ones holding a value (green: found by
code, red: a person has to look), <dir>/values.json the values that stood on the pages, per field with their
count. affairs does the same for every PDF and then folds the documents with the same key into one affair:
<dir>/affairs/<key>.json per affair and <dir>/affairs.ndjson with all of them.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from docket.affair.identity import Identity
from docket.affair.merge import Document, merge, values_of
from docket.affair.validator import Contract
from docket.config import load_config
from docket.document.bridge import Knowledge
from docket.fields.fields import Fields
from docket.fields.placer import blocks_of, day, find_block
from docket.model.client import Client
from docket.page.analyze import analyze_page
from docket.page.painter import draw_blocks, draw_elements, draw_geometry
from docket.page.raster import write_png
from docket.page.render import render_pdf
from docket.pipeline import (
    build_document, fill_fields, first_pages, identify, load_contract, load_field_file, load_knowledge, process_pages,
)
from docket.read.reader import read_page
from docket.text.layer import fill_text_layer


@dataclass
class Processed:
    """One document after the whole chain."""

    name: str
    pages: list[dict]
    record: dict
    report: dict
    filled: dict
    identity: Identity | None
    errors: list[str]
    calls: int
    seconds: float


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="docket")
    commands = parser.add_subparsers(dest="command", required=True)
    helps = (
        ("analyze", "the geometry and the text layer of every page, without a model"),
        ("read", "analyze, then read pages without a text layer with the model"),
        ("document", "the whole document: pages, blocks, the affair record; --model reads scans and asks the fields"),
        ("affairs", "document for every PDF, then one affair per key with its documents"),
    )
    for name, help_text in helps:
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--out", required=True, help="directory for the results")
        if name in ("document", "affairs"):
            command.add_argument("--model", action="store_true", help="use the model for scans, the rest, the fields")
        command.add_argument("files", nargs="+", help="PDF files, or page images as PPM/PGM")
    args = parser.parse_args(argv)
    if args.command in ("document", "affairs"):
        return run_documents(Path(args.out), [Path(f) for f in args.files], args.model, args.command == "affairs")
    return run(args.command, Path(args.out), [Path(f) for f in args.files])


def run_documents(out: Path, files: list[Path], with_model: bool, affairs: bool) -> int:
    config = load_config()
    client = Client(config) if with_model else None
    if client is not None and not config.api_key:
        print("no API_KEY: copy .env.example to .env and fill it in", file=sys.stderr)
        return 1
    contract = load_contract(config)
    knowledge = load_knowledge(config)
    fields = load_field_file(config, contract)
    out.mkdir(parents=True, exist_ok=True)
    documents: list[Document] = []
    for pdf in files:
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            print(f"not a PDF: {pdf}", file=sys.stderr)
            continue
        p = _process(pdf, out, client, contract, knowledge, fields, len(documents) + 1)
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(p.report["blocks"].items(), key=lambda item: -item[1]))
        calls = f"  {p.calls} calls" if client else ""
        state = "valid" if not p.errors else f"{len(p.errors)} violations, first: {p.errors[0]}"
        summary = f"  {_states(p.filled)}  key {p.identity.key}" if p.identity is not None else ""
        print(
            f"{p.name:<28} {len(p.pages)} pages  {sum(p.report['blocks'].values())} blocks ({kinds})"
            f"  rest {p.report['rest']}{calls}  {state}{summary}  {p.seconds:.0f}s"
        )
        if client is not None and client.halted:
            print(f"halted after HTTP {client.halted}", file=sys.stderr)
            return 2
        body = p.record["docs"]["data"][0]["body"]
        values = values_of(p.filled["fields"])
        date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
        key = p.identity.key if p.identity is not None else "dok-" + p.name
        documents.append(Document(len(documents) + 1, p.name, len(p.pages), body, values, key, date))
    if client is not None:
        values = json.dumps({"values": knowledge.values}, ensure_ascii=False, indent=2) + "\n"
        (out / "values.json").write_text(values, encoding="utf-8")
    if not affairs:
        return 0
    return _write_affairs(out, documents, fields, contract, knowledge)


def _process(pdf: Path, out: Path, client: Client | None, contract: Contract, knowledge: Knowledge,
             fields: Fields, doc_id: int) -> Processed:
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
    identity = None
    if client is not None:
        identity = identify(filled["fields"], fields, pages, pdf.stem, knowledge)
        _write_fields(out, pdf.stem, record, pages, filled, fields, keep, identity)
    calls = client.calls - before if client else 0
    return Processed(pdf.stem, pages, record, report, filled, identity, errors, calls, time.monotonic() - started)


def _write_fields(out: Path, name: str, record: dict, pages: list[dict], filled: dict, fields: Fields,
                  keep: dict, identity: Identity) -> None:
    """Writes the fields report with the identity, and the control images of the first pages."""
    first = first_pages(pages)
    text = json.dumps({"first": first, "identity": asdict(identity), **filled}, ensure_ascii=False, indent=2)
    (out / f"{name}-fields.json").write_text(text + "\n", encoding="utf-8")
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


def _states(filled: dict) -> str:
    states: dict[str, int] = {}
    for r in filled["fields"].values():
        states[r["state"]] = states.get(r["state"], 0) + 1
    return f"fields {len(filled['fields'])}: " + ", ".join(f"{k} {v}" for k, v in sorted(states.items()))


def _write_affairs(out: Path, documents: list[Document], fields: Fields, contract: Contract,
                   knowledge: Knowledge) -> int:
    """One affair per key, as a file each and all in one NDJSON."""
    folder = out / "affairs"
    folder.mkdir(parents=True, exist_ok=True)
    failed = 0
    lines = []
    for affair in merge(documents, fields, contract, knowledge.types):
        safe = re.sub(r"[^\w.-]+", "_", affair.key)
        text = json.dumps(affair.record, ensure_ascii=False, indent=2) + "\n"
        (folder / f"{safe}.json").write_text(text, encoding="utf-8")
        lines.append(json.dumps(affair.record, ensure_ascii=False))
        state = "valid" if not affair.errors else f"{len(affair.errors)} violations, first: {affair.errors[0]}"
        failed += 1 if affair.errors else 0
        count = len(affair.documents)
        kind = (affair.record.get("type_harmonized") or {}).get("de") or "-"
        plural = "s" if count > 1 else ""
        print(f"affair {affair.key:<36} {count} document{plural}  type {kind}  {state}  -> {safe}.json")
    (out / "affairs.ndjson").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0


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
