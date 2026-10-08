"""The affair's identity, the type table and the merging, without a model.

For every shipped document with a known affair: the API's number normalised to the key; the first page of the
analyzed pages searched for a number of the parliament's form (the way the identity takes when the read number
is missing or does not fit), and whether that gives the same key; the printed type label through the type
table against the harmonised type the API holds. Then the documents are keyed and merged into affairs, Nidau
twice under the same key, and every affair must validate against the contract.

    python3 tests/affairs.py --pages=<analyzed dir> --documents=<records dir> [--out=<file.md>] [--store=<dir>]
        <document dir> ...

With --store the merged affairs go into a file store there, for the server test.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.identity import make_key, number  # noqa: E402
from docket.affair.merge import Document, merge  # noqa: E402
from docket.affair.types import harmonized  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.fields.placer import locate  # noqa: E402
from docket.pipeline import first_pages, load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.store.files import FileStore  # noqa: E402

# the affair's values in document.json and the role of the field that asks for them
ROLES = {"number": "number", "title": "title", "type": None, "begin_date": "date"}


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith("--")]
    pages_dir = next((Path(a[8:]) for a in argv if a.startswith("--pages=")), None)
    records_dir = next((Path(a[12:]) for a in argv if a.startswith("--documents=")), None)
    out_file = next((Path(a[6:]) for a in argv if a.startswith("--out=")), None)
    store_dir = next((Path(a[8:]) for a in argv if a.startswith("--store=")), None)
    if not dirs or pages_dir is None or records_dir is None:
        print("usage: python3 tests/affairs.py --pages=<dir> --documents=<dir> [--out=<file.md>] [--store=<dir>]"
              " <document dir> ...")
        return 1
    config = load_config()
    contract = load_contract(config)
    fields = load_field_file(config, contract)
    knowledge = load_knowledge(config)
    by_role = fields.by_role()
    print(f"ok   knowledge: {len(knowledge.types)} type labels, number forms for {len(knowledge.forms)} parliaments,"
          f" {len(knowledge.bodies)} parliaments named")

    rows = []
    documents: list[Document] = []
    same_key = known_key = same_type = known_type = 0
    failed = False
    for d in dirs:
        info = d / "document.json"
        pdf = next(d.glob("*.pdf"), None) if d.is_dir() else None
        if pdf is None or not info.is_file():
            continue
        meta = json.loads(info.read_text(encoding="utf-8"))
        affair = meta.get("affair") or {}
        record_file = records_dir / f"{pdf.stem}.json"
        if not record_file.is_file():
            print(f"FAIL {pdf.stem}: no record in {records_dir}")
            failed = True
            continue
        record = json.loads(record_file.read_text(encoding="utf-8"))
        pages = []
        n = 1
        while (pages_dir / f"{pdf.stem}-s{n}.json").is_file():
            pages.append(json.loads((pages_dir / f"{pdf.stem}-s{n}.json").read_text(encoding="utf-8")))
            n += 1
        first = first_pages(pages) if pages else [1]
        body = record["docs"]["data"][0]["body"]
        text = " ".join(e.get("content") or "" for e in pages[0]["elements"]) if pages else ""
        place = meta.get("body", {}).get("name") or ""

        # the key: from the API's number, and from the page by the parliament's form
        api_key = "nr-" + number(str(affair["number"])) if affair.get("number") else ""
        identity = make_key({"place": place}, pdf.stem, text, knowledge.forms, knowledge.bodies)
        if api_key:
            known_key += 1
            same_key += 1 if identity.key == api_key else 0
        # the type label through the table
        kind = harmonized(str(affair["type"]), knowledge.types) if affair.get("type") else None
        got_type = (kind or {}).get("de") or "-"
        want_type = affair.get("type_harmonized") or ""
        if want_type:
            known_type += 1
            same_type += 1 if got_type == want_type else 0

        values: dict[str, list[dict]] = {}
        for key, role in ROLES.items():
            value = affair.get(key)
            field_name = by_role.get(role or "", "")
            if value in (None, "") or not field_name:
                continue
            block = locate(str(value), body, first)
            if block is not None:
                values[field_name] = [{"value": str(value), "block": block, "how": "literal"}]
        doc_key = api_key or identity.key
        date = str(affair.get("begin_date") or "")
        documents.append(Document(len(documents) + 1, pdf.stem, len(pages), body, values, doc_key, date))
        rows.append(
            f"| {pdf.stem} | {affair.get('number') or '—'} | {api_key or '—'} | {identity.key} ({identity.way}"
            f"{', body ' + identity.body if identity.body else ''}) | {affair.get('type') or '—'} | {got_type} | "
            f"{want_type or '—'} |"
        )
        key_fits = not api_key or identity.key == api_key
        type_fits = not want_type or got_type == want_type
        mark = "ok  " if key_fits and type_fits else "note"
        print(f"{mark} {pdf.stem}: key {identity.key} ({identity.way}) against {api_key or 'none known'};"
              f" type {got_type} against {want_type or 'none known'}")

    # Nidau once more under the same key: the affair must hold both documents
    twin = next((d for d in documents if d.name == "nidau-m185"), None)
    if twin is not None:
        again = Document(len(documents) + 1, twin.name + "-again", twin.pages, twin.body, twin.values, twin.key)
        again.date = twin.date
        documents.append(again)
    affairs = merge(documents, fields, contract, knowledge.types)
    for a in affairs:
        state = "valid" if not a.errors else f"{len(a.errors)} violations, first: {a.errors[0]}"
        if a.errors:
            failed = True
        kind = (a.record.get("type_harmonized") or {}).get("de") or "-"
        mark = "ok  " if not a.errors else "FAIL"
        print(f"{mark} affair {a.key}: {len(a.documents)} documents, type {kind}, {state}")
    pair = next((a for a in affairs if len(a.documents) == 2), None)
    if twin is not None and pair is None:
        print("FAIL the two Nidau documents did not land in one affair")
        failed = True
    if store_dir is not None:
        # a fresh store every run, so the server test counts only what it did itself
        if store_dir.is_dir():
            shutil.rmtree(store_dir)
        store = FileStore(store_dir)
        by_id = {d.id: d for d in documents}
        for a in affairs:
            members = [{"name": by_id[i].name, "id": i, "pages": by_id[i].pages} for i in a.documents]
            store.put_affair(a.key, a.record, members)
            for i in a.documents:
                store.put_pages(by_id[i].name, pages_dir)
        print(f"ok   {len(affairs)} affairs in the file store {store_dir}")
    print(f"{same_key} of {known_key} keys from the page as from the API's number; "
          f"{same_type} of {known_type} type labels onto the API's harmonised type; "
          f"{len(affairs)} affairs from {len(documents)} documents")

    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        head = (
            "# Identity and type against the API\n\n"
            f"Generated by `tests/affairs.py` on {time.strftime('%Y-%m-%d')}, no model call. Per shipped document: the "
            "affair's number as OpenParlData holds it and the key it gives; the key the identity finds from the first "
            "page by the parliament's number form, with the way it took; the printed type label through the type table "
            "from the export against the harmonised type of the API.\n\n"
            "| Document | API number | Key from it | Key from the page | Type label | Through the table | API |\n"
            "|---|---|---|---|---|---|---|\n"
        )
        foot = (
            f"\n{same_key} of {known_key} keys from the page as from the API's number; "
            f"{same_type} of {known_type} type labels onto the API's harmonised type; "
            f"{len(affairs)} affairs from {len(documents)} documents, all {'valid' if not failed else 'NOT valid'}.\n"
        )
        out_file.write_text(head + "\n".join(rows) + "\n" + foot, encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
