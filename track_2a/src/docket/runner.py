"""One run over PDFs: every document through the chain, the documents keyed and merged into affairs, the
affairs written as files and into the store. The command line and the web server's queue both call this."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from docket.affair.identity import Identity
from docket.affair.merge import Document, merge, values_of
from docket.affair.validator import Contract
from docket.config import Config
from docket.document.bridge import Knowledge
from docket.fields.fields import Fields
from docket.fields.placer import blocks_of, day, find_block
from docket.model.client import Client
from docket.page.painter import draw_blocks
from docket.pipeline import (
    add_kind, build_document, fill_fields, first_pages, identify, load_contract, load_field_file, load_knowledge,
    process_pages,
)
from docket.store import open_store
from docket.store.review import carry_reviews


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


@dataclass
class RunResult:
    documents: list[dict] = field(default_factory=list)
    affairs: list[dict] = field(default_factory=list)
    calls: int = 0
    halted: int = 0
    failed: int = 0


def run_affairs(files: list[Path], out: Path, config: Config, with_model: bool, merge_affairs: bool = True,
                say: Callable[[str], None] = print) -> RunResult:
    """Processes the PDFs into `out`; with merge_affairs the documents become affairs in the store."""
    client = Client(config) if with_model else None
    contract = load_contract(config)
    knowledge = load_knowledge(config)
    fields = load_field_file(config, contract)
    out.mkdir(parents=True, exist_ok=True)
    result = RunResult()
    documents: list[Document] = []
    for pdf in files:
        if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
            say(f"not a PDF: {pdf}")
            continue
        p = _process(pdf, out, client, contract, knowledge, fields)
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(p.report["blocks"].items(), key=lambda item: -item[1]))
        calls = f"  {p.calls} calls" if client else ""
        state = "valid" if not p.errors else f"{len(p.errors)} violations, first: {p.errors[0]}"
        kind = f"  kind {p.report['kind']['kind']}" if p.report.get("kind") else "  kind -"
        summary = f"  {_states(p.filled)}  key {p.identity.key}{kind}" if p.identity is not None else kind
        say(
            f"{p.name:<28} {len(p.pages)} pages  {sum(p.report['blocks'].values())} blocks ({kinds})"
            f"  rest {p.report['rest']}{calls}  {state}{summary}  {p.seconds:.0f}s"
        )
        result.calls += p.calls
        result.failed += 1 if p.errors else 0
        result.documents.append({
            "name": p.name, "pages": len(p.pages), "blocks": sum(p.report["blocks"].values()), "calls": p.calls,
            "valid": not p.errors, "key": p.identity.key if p.identity else None, "seconds": round(p.seconds),
            "identity": asdict(p.identity) if p.identity else None, "kind": p.report.get("kind"),
        })
        body = p.record["docs"]["data"][0]["body"]
        values = values_of(p.filled["fields"])
        date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
        key = p.identity.key if p.identity is not None else "dok-" + p.name
        documents.append(Document(len(documents) + 1, p.name, len(p.pages), body, values, key, date))
        if client is not None and client.halted:
            say(f"halted after HTTP {client.halted}")
            result.halted = client.halted
            break
    if client is not None:
        values_text = json.dumps({"values": knowledge.values}, ensure_ascii=False, indent=2) + "\n"
        (out / "values.json").write_text(values_text, encoding="utf-8")
    if merge_affairs and documents:
        result.affairs = _write_affairs(out, documents, fields, contract, knowledge, config, say)
        result.failed += sum(1 for a in result.affairs if not a["valid"])
    return result


def _process(pdf: Path, out: Path, client: Client | None, contract: Contract, knowledge: Knowledge,
             fields: Fields) -> Processed:
    started = time.monotonic()
    before = client.calls if client else 0
    pages_dir = out / pdf.stem
    pages_dir.mkdir(parents=True, exist_ok=True)
    keep: dict[int, object] = {}
    pages = process_pages(pdf, pages_dir, client, keep)
    record, report = build_document(pdf.stem, pages, knowledge, client, log=pages_dir / "sort.read")
    record, filled = fill_fields(record, pages, fields, contract, client, knowledge, log=pages_dir / "fields.read")
    # the kind of the document from the words of its first page, with the printed type the model read
    printed = _printed_type(filled["fields"], fields)
    found = add_kind(record, pages, knowledge, printed)
    report["kind"] = found
    errors = contract.check(record)
    (out / f"{pdf.stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    identity = None
    if client is not None:
        identity = identify(filled["fields"], fields, pages, pdf.stem, knowledge)
        _write_fields(out, pdf.stem, record, pages, filled, fields, keep, identity)
    calls = client.calls - before if client else 0
    return Processed(pdf.stem, pages, record, report, filled, identity, errors, calls, time.monotonic() - started)


def _printed_type(report: dict[str, dict], fields: Fields) -> str | None:
    """The type the model read from the page (the field at type_name.de), when it stood on the page."""
    name = next((n for n, f in fields.fields.items() if f.path == ["type_name", "de"]), None)
    r = report.get(name or "", {})
    return r.get("value") if r.get("state") == "on the page" else None


def _write_fields(out: Path, name: str, record: dict, pages: list[dict], filled: dict, fields: Fields,
                  keep: dict, identity: Identity) -> None:
    """Writes the fields report with the identity, and the control images of the first pages."""
    first = first_pages(pages)
    text = json.dumps({"first": first, "identity": asdict(identity), **filled}, ensure_ascii=False, indent=2)
    (out / f"{name}-fields.json").write_text(text + "\n", encoding="utf-8")
    body = record["docs"]["data"][0]["body"]
    found: dict[str, str] = {}
    for field_name, r in filled["fields"].items():
        for item in r.get("items", []):
            if item["block"] is None:
                continue
            block = find_block(item["block"], body)
            flagged = bool(block and block.get("approve"))
            look = item["how"] not in ("literal", "derived") or fields.fields[field_name].free or flagged
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
                   knowledge: Knowledge, config: Config, say: Callable[[str], None]) -> list[dict]:
    """One affair per key, as a file each, all in one NDJSON, and into the store with earlier reviews kept."""
    folder = out / "affairs"
    folder.mkdir(parents=True, exist_ok=True)
    store = open_store(config)
    by_id = {d.id: d for d in documents}
    lines = []
    summaries = []
    for affair in merge(documents, fields, contract, knowledge.types):
        safe = re.sub(r"[^\w.-]+", "_", affair.key)
        record = affair.record
        earlier = store.get_affair(affair.key)
        carried = 0
        if earlier is not None:
            record, carried = carry_reviews(earlier["record"], record)
        text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        (folder / f"{safe}.json").write_text(text, encoding="utf-8")
        lines.append(json.dumps(record, ensure_ascii=False))
        members = [{"name": by_id[i].name, "id": i, "pages": by_id[i].pages} for i in affair.documents]
        store.put_affair(affair.key, record, members)
        for i in affair.documents:
            name = by_id[i].name
            report_file = out / f"{name}-fields.json"
            if report_file.is_file():
                store.put_fields(name, json.loads(report_file.read_text(encoding="utf-8")))
            store.put_pages(name, out / name)
        state = "valid" if not affair.errors else f"{len(affair.errors)} violations, first: {affair.errors[0]}"
        count = len(affair.documents)
        kind = (record.get("type_harmonized") or {}).get("de") or "-"
        plural = "s" if count > 1 else ""
        kept = f"  {carried} reviews kept" if carried else ""
        say(f"affair {affair.key:<36} {count} document{plural}  type {kind}  {state}{kept}  -> {safe}.json")
        summaries.append({
            "key": affair.key, "documents": [by_id[i].name for i in affair.documents], "type": kind,
            "valid": not affair.errors, "kept": carried,
        })
    (out / "affairs.ndjson").write_text("\n".join(lines) + "\n", encoding="utf-8")
    say(f"{len(lines)} affairs in the {store.kind} store")
    return summaries
