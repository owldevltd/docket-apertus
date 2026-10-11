"""A clean checkout has something to show: the affairs of the shipped documents, without a model.

`make run` starts with an empty store. The server then forms the affairs of the shipped documents from the
runs stored beside them (run.json), as a run in its queue. The test does the same into a store of its own,
with the pages `make test` analysed before: every shipped document with a stored run sits in an affair, every
affair is valid and is the one stored beside its document (affair.json, but for the number the document has
within its run: there it ran alone, here with the others), the first page of every document can be shown,
doing it a second time changes nothing, and what a visitor is given from that store hangs together: every
affair names itself and its parliament, every row of the tables that follow from the affairs names an affair
that is there, one person, group or meeting asked for by its name comes with its rows alone, and every
document is found as its entry in the record of its affair.

    python3 tests/shipped.py --pages=<analyzed dir>
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.pipeline import load_contract  # noqa: E402
from docket.runner import run_shipped  # noqa: E402
from docket.store import open_store  # noqa: E402


def unnumbered(record: dict) -> dict:
    """The record without the number its documents had within their run (source.doc, docs.data[].id)."""
    def walk(value: object) -> object:
        if isinstance(value, dict):
            return {k: None if k == "doc" else walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        return value

    out = walk(record)
    for entry in (out.get("docs") or {}).get("data") or []:
        entry["id"] = None
    return out


def main(argv: list[str]) -> int:
    pages = next((Path(a[8:]) for a in argv if a.startswith("--pages=")), None)
    if pages is None or not pages.is_dir():
        print("usage: python3 tests/shipped.py --pages=<analyzed dir>")
        return 1
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    base = load_config()
    shipped = {next(iter(sorted(d.glob("*.pdf")))).stem: d for d in sorted((base.data_dir / "documents").glob("*/"))
               if (d / "run.json").is_file() and any(d.glob("*.pdf"))}
    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        result = run_shipped(Path(tmp) / "out", config, lambda line: None, pages)
        store = open_store(config)
        affairs = store.list_affairs()
        held = {d["name"]: a for a in affairs for d in a["documents"]}
        check(len(shipped) > 0 and set(held) == set(shipped) and not result.calls,
              f"{len(shipped)} shipped documents with a stored run sit in {len(affairs)} affairs, no call to the model")
        check(all(a["valid"] for a in result.affairs), "every affair is valid")
        same = [name for name, d in shipped.items()
                if unnumbered(json.loads((d / "affair.json").read_text(encoding="utf-8")))
                == unnumbered(held[name]["record"])]
        check(len(same) == len(shipped), f"{len(same)} of {len(shipped)} affairs are the ones stored beside their "
                                         f"documents" + ("" if len(same) == len(shipped) else ", not: " + ", ".join(
                                             sorted(set(shipped) - set(same)))))
        check(all(store.page_path(name, 1) is not None for name in shipped),
              "the first page of every document can be shown")
        again = run_shipped(Path(tmp) / "out", config, lambda line: None, pages)
        after = {d["name"]: a["record"] for a in store.list_affairs() for d in a["documents"]}
        check(len(again.affairs) == len(result.affairs) and all(after[n] == held[n]["record"] for n in shipped),
              "a second time changes nothing")

        # what a visitor is given from this store
        app = App(store, load_contract(config), config)
        try:
            listed = app.records()["data"]
            keys = {a["key"] for a in store.list_affairs()}
            check({r.get("id") for r in listed} == keys and len(listed) == len(keys)
                  and all(r.get("body_key") for r in listed),
                  f"each of the {len(listed)} affairs a visitor is given names itself by its key, and its parliament")
            for name, column in (("contributors", "fullname"), ("groups", "name"), ("meetings", "conf-name"),
                                 ("events", "")):
                rows = app.table(name)["data"]
                check(len(rows) > 0 and all(r.get("affair_id") in keys for r in rows),
                      f"the table of {name} has {len(rows)} rows, each of an affair that is there")
                # the name with the most signs in it first: round brackets, commas
                names = sorted({str(r[column]) for r in rows if column and r.get(column)},
                               key=lambda n: (-sum(n.count(c) for c in "(),/"), n))
                if names:
                    mine = app.table(name, {column: names[0]})
                    want = [r for r in rows if r.get(column) == names[0]]
                    check(mine["data"] == want and 0 < len(want) < len(rows) and mine["meta"]["count"] == len(want),
                          f"asked for the one name '{names[0][:40]}', it gives its rows alone: {len(want)}")
            # a type is found by its standard name in every language it has one, and by the name printed
            typed = next((r for r in listed if len(r.get("type_harmonized") or {}) > 1), None)
            names = [*(typed or {}).get("type_harmonized", {}).values(), *(typed or {}).get("type_name", {}).values()]
            check(typed is not None and len(set(names)) > 2 and all(
                typed["id"] in {r["id"] for r in app.records({"type": n})["data"]} for n in names)
                  and app.records({"type": "zzzqqqxxx"})["data"] == [],
                  f"an affair is found by every wording of its type: {', '.join(sorted(set(names)))}")
            entries = {d["name"]: d for r in (app.record(k) for k in keys) for d in r["docs"]["data"]}
            check(set(entries) == set(shipped) and all(app.document_record(n) == entries[n] for n in shipped),
                  "every document is found alone as its entry in the record of its affair")
            check(app.name_records() == 0, "no affair has to be given its id afterwards")
        finally:
            app.jobs.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
