"""One run over PDFs: every document through the chain, the documents keyed and merged into affairs, the
affairs written as files and into the store. The command line and the web server's queue both call this."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from docket.affair.identity import Identity
from docket.affair.merge import Document, merge, values_of
from docket.affair.persons import link_persons
from docket.affair.validator import Contract
from docket.config import Config
from docket.document.bridge import Knowledge
from docket.fields import second
from docket.fields.fields import Fields, definition_of
from docket.fields.filler import fill_document
from docket.fields.placer import blocks_of, day, find_block
from docket.model.client import Client
from docket.page.painter import draw_blocks
from docket.pipeline import (
    add_kind, build_document, fill_fields, first_pages, identify, load_contract, load_field_file, load_knowledge,
    process_pages,
)
from docket.store import open_store
from docket.store.review import carry_reviews
from docket.store.register import stop_words
from docket.store.rows import adopt, carry_decisions, follow, kind_of, rows_of, set_matches, set_places, values_from
from docket.store.vocabulary import Vocabulary


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
        parliament = p.identity.body if p.identity is not None else ""
        documents.append(Document(len(documents) + 1, p.name, len(p.pages), body, values, key, date, parliament))
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


def run_shipped(out: Path, config: Config, say: Callable[[str], None] = print,
                pages: Path | None = None) -> RunResult:
    """Forms the affairs of the shipped documents from the runs stored beside them, without the model: the
    answers come from run.json, the pages are rendered and measured anew (or taken from `pages`, a folder that
    holds them already). What a clean checkout has to show before anyone has set a key."""
    contract = load_contract(config)
    knowledge = load_knowledge(config)
    fields = load_field_file(config, contract)
    out.mkdir(parents=True, exist_ok=True)
    result = RunResult()
    documents: list[Document] = []
    for folder in sorted((config.data_dir / "documents").glob("*/")):
        pdf = next(iter(sorted(folder.glob("*.pdf"))), None)
        stored = folder / "run.json"
        if pdf is None or not stored.is_file():
            continue
        started = time.monotonic()
        run = json.loads(stored.read_text(encoding="utf-8"))
        name = pdf.stem
        (out / name).mkdir(parents=True, exist_ok=True)
        if pages is None:
            process_pages(pdf, out / name, None)
        else:
            for file in sorted(pages.glob(f"{name}-s*")):
                if file.is_file():
                    shutil.copyfile(file, out / name / file.name)
        # the report as a run leaves it beside the record, for the store
        report = {"identity": run["identity"], "kind": run.get("kind"), "fields": run["fields"]}
        (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
        values = values_of(run["fields"])
        date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
        identity = run["identity"]
        key = identity.get("key") or "dok-" + name
        documents.append(Document(len(documents) + 1, name, run["pages"], run["body"], values, key, date,
                                  identity.get("body") or ""))
        seconds = time.monotonic() - started
        say(f"{name:<28} {run['pages']} pages  from its stored run  key {key}  {seconds:.0f}s")
        result.documents.append({
            "name": name, "pages": run["pages"], "blocks": len(blocks_of(run["body"])), "calls": 0, "valid": True,
            "key": key, "seconds": round(seconds), "identity": identity, "kind": run.get("kind"),
        })
    if documents:
        result.affairs = _write_affairs(out, documents, fields, contract, knowledge, config, say)
        result.failed = sum(1 for a in result.affairs if not a["valid"])
    return result


def ask_missing(config: Config, names: list[str] | None = None, limit: int | None = None,
                say: Callable[[str], None] = print) -> RunResult:
    """Asks the documents of the store what they were never asked: the fields that came into the fields file
    after a document was read. Only those questions go to the model, over the pages the store kept; nothing
    is read again. The answers join the document's report, and its affair is formed anew from the reports of
    its documents, with every decision kept. `names` limits it to these fields, `limit` to so many
    documents."""
    client = Client(config)
    contract = load_contract(config)
    knowledge = load_knowledge(config)
    fields = load_field_file(config, contract)
    store = open_store(config)
    result = RunResult()
    date_field = fields.by_role().get("date", "")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        for affair in store.list_affairs():
            entries = {e.get("id"): e for e in (affair["record"].get("docs") or {}).get("data", [])}
            documents: list[Document] = []
            touched = False
            for document in affair["documents"]:
                name, entry = document["name"], entries.get(document["id"])
                report = store.get_fields(name)
                if report is None or entry is None:
                    continue
                missing = [n for n in fields.fields if n not in report["fields"] and (not names or n in names)]
                open_for_more = not client.halted and (limit is None or len(result.documents) < limit)
                if missing and open_for_more:
                    count = int(document.get("pages") or 1)
                    pages = [p for p in (store.page_data(name, n) for n in range(1, count + 1)) if p is not None]
                    if len(pages) < count:
                        say(f"{name}: the store did not keep its pages, not asked")
                    else:
                        part = Fields(fields.task, {n: fields.fields[n] for n in missing}, fields.entities)
                        before = client.calls
                        stub = {"docs": {"data": [{"id": 1, "body": entry.get("body") or []}]}}
                        _, filled = fill_document(stub, pages, first_pages(pages), part, contract, client, knowledge)
                        if filled["asked"]:
                            report["fields"].update(filled["fields"])
                            report.setdefault("asked", []).extend(filled["asked"])
                            if all(n in report["fields"] for n in fields.fields):
                                report["definition"] = definition_of(fields)
                            store.put_fields(name, report)
                            touched = True
                            calls = client.calls - before
                            result.calls += calls
                            result.documents.append({"name": name, "asked": missing, "calls": calls})
                            say(f"{name}: asked {', '.join(missing)}  {calls} calls")
                (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
                values = values_of(report["fields"])
                date = next((day(i["value"]) for i in values.get(date_field, [])), "")
                documents.append(Document(document["id"], name, int(document.get("pages") or 1),
                                          entry.get("body") or [], values, affair["key"], date,
                                          str((report.get("identity") or {}).get("body") or "")))
            if touched:
                result.affairs.extend(_write_affairs(out, documents, fields, contract, knowledge, config, say))
            if client.halted:
                say(f"halted after HTTP {client.halted}")
                result.halted = client.halted
                break
    if not result.documents and not result.halted:
        say("no document lacks a field of the fields file" if client.config.api_key
            else "no LLM_API_KEY: nothing asked")
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
        _write_fields(out, pdf.stem, record, pages, filled, fields, keep, identity, found)
    calls = client.calls - before if client else 0
    return Processed(pdf.stem, pages, record, report, filled, identity, errors, calls, time.monotonic() - started)


def _printed_type(report: dict[str, dict], fields: Fields) -> str | None:
    """The type the model read from the page (the field at type_name.de), when it stood on the page."""
    name = next((n for n, f in fields.fields.items() if f.path == ["type_name", "de"]), None)
    r = report.get(name or "", {})
    return r.get("value") if r.get("state") == "on the page" else None


def _write_fields(out: Path, name: str, record: dict, pages: list[dict], filled: dict, fields: Fields,
                  keep: dict, identity: Identity, kind: dict | None) -> None:
    """Writes the fields report with the identity and the kind the document was found to be, and the control
    images of the first pages."""
    first = first_pages(pages)
    report = {"first": first, "identity": asdict(identity), "definition": definition_of(fields), "kind": kind,
              **filled}
    text = json.dumps(report, ensure_ascii=False, indent=2)
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
    names = store.get_vocabulary()
    vocabulary = Vocabulary(names)
    stop = stop_words(names)
    found: dict[str, list[dict]] = {}
    learnt = store.get_learnt()
    # what was found in every document, one row per value; the values go into the merge with the number of
    # their row, so that it can note where each row sits in the record
    rows_of_doc: dict[int, list[dict]] = {}
    for d in documents:
        report_file = out / f"{d.name}-fields.json"
        if not report_file.is_file():
            continue
        report = json.loads(report_file.read_text(encoding="utf-8"))
        rows = rows_of(d.name, report["fields"], fields, d.body, report.get("kind"))
        d.kind = kind_of(rows)
        given = {name: [{k: v for k, v in hit.items() if k != "n"} for hit in hits] for name, hits in d.values.items()}
        # only when the report is the one the document's values came from
        if values_from(rows) == given:
            rows_of_doc[d.id] = rows
            # the second opinion beside the model, where the store has learnt one
            if learnt and d.parliament:
                second.apply(d.name, rows, d.body, d.parliament, fields, learnt, knowledge.forms, vocabulary)
            d.values = values_from(rows, numbered=True)
    placed: list[dict] = []
    for affair in merge(documents, fields, contract, knowledge.types, vocabulary, placed):
        safe = re.sub(r"[^\w.-]+", "_", affair.key)
        record = affair.record
        # who the named persons are, by the register of each document's parliament
        linked = link_persons(record, {i: by_id[i].parliament for i in affair.documents},
                              {i: by_id[i].name for i in affair.documents}, store, stop, fields)
        if linked:
            found.update(linked)
            affair.errors = contract.check(record)
        # what was decided lives at the rows: the rows of an earlier run are found again and hand their
        # decisions to the new ones, and the record follows the rows
        together, known = [], True
        for i in affair.documents:
            if i not in rows_of_doc:
                known = False
                continue
            set_places(rows_of_doc[i], affair.key, [p for p in placed if p["doc"] == i])
            together.extend(rows_of_doc[i])
        set_matches(record, together, fields, linked, {by_id[i].name: by_id[i].parliament for i in affair.documents})
        for i in affair.documents:
            if i in rows_of_doc:
                before = store.get_rows(by_id[i].name)
                known = known and bool(before)
                carry_decisions(before, rows_of_doc[i])
        earlier = store.get_affair(affair.key)
        carried = 0
        if earlier is not None and not known:
            # an affair stored before its documents had rows: its reviews are found the earlier way once more,
            # by document, block and path, and taken into the rows
            record, carried = carry_reviews(earlier["record"], record)
            adopt(record, together)
        record, followed = follow(record, together)
        carried = max(carried, followed)
        text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        (folder / f"{safe}.json").write_text(text, encoding="utf-8")
        lines.append(json.dumps(record, ensure_ascii=False))
        members = [{"name": by_id[i].name, "id": i, "pages": by_id[i].pages} for i in affair.documents]
        store.put_affair(affair.key, record, members)
        for i in affair.documents:
            name = by_id[i].name
            report_file = out / f"{name}-fields.json"
            if report_file.is_file():
                report = json.loads(report_file.read_text(encoding="utf-8"))
                if name in found:
                    # what became of every name stays with the document's report
                    report["persons"] = found[name]
                    report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                store.put_fields(name, report)
            if i in rows_of_doc:
                store.put_rows(name, rows_of_doc[i])
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
