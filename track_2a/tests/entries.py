"""The review goes by the rows, without a model: what the app is shown of an affair is built from the rows of
its documents and is, value for value, what the record of the affair holds with a place; every value carries
the id of its row, and a decision names it by that id. The decision stands at the row first and the record
follows the rows. The blocks of a document come from the store, not from the record. And with the record
replaced by the same affair in another shape, one without room for places or blocks, the review still shows
every value, takes a decision and leaves that record alone.

    python3 tests/entries.py --pages=<analyzed dir>
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.affair.validator import Contract  # noqa: E402
from docket.affair.view import view  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.fields.fields import load_fields  # noqa: E402
from docket.fields.placer import find_block  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.runner import run_shipped  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.entries import entries_of  # noqa: E402
from docket.store.review import sources_of  # noqa: E402
from docket.store.rows import find_value, follow  # noqa: E402


def main(argv: list[str]) -> int:
    pages = next((Path(a[8:]) for a in argv if a.startswith("--pages=")), None)
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    base = load_config()
    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        run_shipped(Path(tmp) / "out", config, say=lambda line: None, pages=pages)
        store = open_store(config)
        contract = load_contract(config)
        fields = load_field_file(config, contract)
        knowledge = load_knowledge(config)
        app = App(store, contract, config, Jobs(config))

        def as_record(key: str) -> bool:
            """Whether what the app shows is what the record holds with a place, in every part of it."""
            held = sources_of(store.get_affair(key)["record"])
            shown = app.affair(key)["sources"]
            return len(shown) == len(held) and all(s.get(k) == h[k] for s, h in zip(shown, held) for k in h)

        affairs = store.list_affairs()
        values = sum(len(sources_of(a["record"])) for a in affairs)
        check(all(as_record(a["key"]) for a in affairs),
              f"{len(affairs)} affairs: each of the {values} values shown, built from the rows, is the one the "
              "record holds at its place")
        alone, ids = 0, 0
        for a in affairs:
            rows = [r for d in a["documents"] for r in store.get_rows(d["name"])]
            numbers = {d["name"]: d["id"] for d in a["documents"]}
            blocks = {d["name"]: store.get_blocks(d["name"]) or [] for d in a["documents"]}
            without = entries_of(rows, numbers, fields, lambda name, i, b=blocks: find_block(i, b[name]))
            shown = {e["id"]: e for e in app.affair(a["key"])["sources"]}
            # the app adds to an entry what it finds across the affairs (alike values, the name of a person)
            same = all(e["id"] in shown and all(shown[e["id"]].get(k) == v for k, v in e.items()) for e in without)
            alone += len(without) == len(shown) and same
            ids += all(find_value(rows, i) is not None for e in shown.values()
                       for i in (e.get("ids") or {"": e["id"]}).values())
        check(alone == len(affairs), "without the record the rows give the same values, flags and decisions")
        check(ids == len(affairs), "every value carries the id of a row")

        # decisions by id: the row first, the record follows
        key = next(a["key"] for a in affairs if any(d["name"] == "zuerich-219587" for d in a["documents"]))
        before = store.get_affair(key)["record"]
        shown = app.affair(key)["sources"]
        title = next(e for e in shown if e.get("field") == "title")
        several = next(e for e in shown if len(e.get("values") or {}) > 1)
        open_one = next(e for e in shown if e["open"] and e is not title and e is not several)
        beside = next(p for p in several["values"] if p != several["path"])
        asked = [
            {"id": title["id"], "decision": "changed", "by": "test", "after": "Anders"},
            {"id": several["ids"][beside], "decision": "changed", "by": "test", "after": "Daneben"},
            {"id": open_one["id"], "decision": "rejected", "by": "test"},
        ]
        check(all(app.decide(key, body)[0] == 200 for body in asked), "three decisions are taken by the id of a row")
        rows = store.get_rows("zuerich-219587")
        after = store.get_affair(key)["record"]
        decided = sum(len(r.get("decisions") or []) for r in rows)
        check(decided == 3 and follow(before, rows)[0] == after,
              "each stands at its row, and the record now is the one from before with the rows' decisions on it")
        check(as_record(key), "what the app shows is again what the record holds: the changed values, the reviews")
        counts = app.affair(key)["counts"]
        listed = next(s for s in app.summaries() if s["key"] == key)
        check(counts["done"] == 3 and listed["counts"] == counts and listed["kinds"] == ["submission"],
              f"the list of affairs counts by the rows as well: {counts}")

        # the document from the store
        shown_doc = app.document("zuerich-219587")
        in_record = after["docs"]["data"][0]
        check(shown_doc is not None and shown_doc["blocks"] == in_record["body"]
              and shown_doc["language"] == in_record["language"] and app.document("none") is None,
              f"the blocks of a document come from the store: {len(shown_doc['blocks'])}, language "
              f"{shown_doc['language']}")

        # the same affair in another shape, without room for places or blocks
        other = ROOT / "data" / "schema" / "plain"
        plain_contract = Contract.load(other / "contract.json")
        plain_fields = load_fields(other / "fields.json", plain_contract, fields.entities)
        plain = view(store, key, plain_fields, plain_contract, knowledge.types, knowledge.answers)
        store.save_record(key, plain)
        still = app.affair(key)
        check("sources" not in plain and "docs" not in plain and len(still["sources"]) == len(shown)
              and still["counts"]["done"] == 3,
              f"with the record in another shape the review still shows the {len(shown)} values and their decisions")
        last = next(e for e in still["sources"] if e["open"])
        status, answer = app.decide(key, {"id": last["id"], "decision": "confirmed", "by": "test"})
        rows = store.get_rows("zuerich-219587")
        check(status == 200 and sum(len(r.get("decisions") or []) for r in rows) == 4
              and store.get_affair(key)["record"] == plain and answer["counts"]["done"] == 4,
              "a decision is taken there as well: it stands at the row, and the record of the other shape is left "
              "as it is")
        check(app.document("zuerich-219587")["blocks"] == in_record["body"],
              "the document is shown from the store, though that record holds no blocks")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
