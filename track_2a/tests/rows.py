"""The rows of a document and the way back to the record, without a model.

For every shipped document with a stored run: the rows are formed from the model's answers and the blocks;
every row carries an entity, every placed row its page and box. Then the round trip: the rows go into a store
and come back, the values taken from them are the ones the answers held, and the affair built from them is
the stored affair, character by character. A run writes the same rows into its store, and a store that was
filled before the rows existed gets them from its reports. Over all documents a value is found by its entity.

    python3 tests/rows.py <document dir> ...
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.merge import Document, values_of  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.fields.placer import day  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.runner import _write_affairs  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.files import FileStore  # noqa: E402
from docket.store.review import sources_of  # noqa: E402
from docket.store.rows import DROPPED, PLACED, fill_rows, rows_of, values_from  # noqa: E402

# what a row says about the value itself; the rest is where it sits in the affair and what was decided
OWN = ("doc", "n", "entity", "role", "field", "entry", "value", "state", "how", "block", "page", "box")


def own(rows: list[dict]) -> list[dict]:
    return [{k: r[k] for k in OWN} for r in rows]


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith("--")]
    if not dirs:
        print("usage: python3 tests/rows.py <document dir> ...")
        return 1
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    base = load_config()
    contract = load_contract(base)
    fields = load_field_file(base, contract)
    knowledge = load_knowledge(base)
    by_entity = Counter(f.entity for f in fields.fields.values())
    names = list(fields.entities)
    check(set(by_entity) <= set(names),
          f"fields file: {len(fields.fields)} fields, " + ", ".join(f"{e} {by_entity[e]}" for e in names))

    with tempfile.TemporaryDirectory() as all_tmp:
        together = FileStore(Path(all_tmp) / "store")
        motions: set[str] = set()
        count = 0
        for d in dirs:
            stored_run = d / "run.json"
            pdf = next(d.glob("*.pdf"), None) if d.is_dir() else None
            if pdf is None or not stored_run.is_file():
                continue
            count += 1
            name = pdf.stem
            run = json.loads(stored_run.read_text(encoding="utf-8"))
            rows = rows_of(name, run["fields"], fields, run["body"], run.get("kind"))
            placed = [r for r in rows if r["state"] == PLACED]
            dropped = [r for r in rows if r["state"] == DROPPED]
            whole = all(r["entity"] in names and [r["n"] for r in rows] == list(range(len(rows))) for r in rows)
            located = all(r["page"] and r["box"] and all(isinstance(v, (int, float)) for v in r["box"]) for r in placed)
            about = sum(1 for r in rows if r.get("about"))
            check(whole and located and all(r["block"] is None and r["box"] is None for r in dropped),
                  f"{name}: {len(rows)} rows, {len(placed)} placed with page and box, {len(dropped)} dropped without"
                  + (", one of them the kind of the document" if about else ""))

            together.put_rows(name, rows)
            back = together.get_rows(name)
            values = values_from(back)
            held = values_of(run["fields"])
            # the order of the fields and of their values counts too
            same_values = json.dumps(values, ensure_ascii=False) == json.dumps(held, ensure_ascii=False)
            check(back == rows and same_values,
                  f"{name}: the rows come back from the store and give the values the answers held")
            if any(r["field"] == "type" and r["value"] == "Motion" for r in placed):
                motions.add(name)

            # the affair from the rows, the way a run forms it, in a store of its own
            with tempfile.TemporaryDirectory() as tmp:
                config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
                out = Path(tmp) / "out"
                out.mkdir()
                report = {"identity": run["identity"], "kind": run.get("kind"), "fields": run["fields"]}
                (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
                date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
                identity = run["identity"]
                document = Document(1, name, run["pages"], run["body"], values, identity.get("key") or "dok-" + name,
                                    date, identity.get("body") or "")
                affair = _write_affairs(out, [document], fields, contract, knowledge, config, lambda line: None)[0]
                file = out / "affairs" / (re.sub(r"[^\w.-]+", "_", affair["key"]) + ".json")
                now = file.read_text(encoding="utf-8")
                store = open_store(config)
                written = store.get_rows(name)
                store.put_rows(name, [])
                refilled = fill_rows(store, fields, contract, knowledge.types)
                again = store.get_rows(name)
            stored = d / "affair.json"
            check(stored.is_file() and stored.read_text(encoding="utf-8") == now,
                  f"{name}: the affair built from the rows is the stored one")
            check(own(written) == own(rows) and refilled == 1 and again == written,
                  f"{name}: a run writes these rows into its store, and a store without them gets them from its report")
            # every value with a place in the record is the place of a row
            places = {(p["source"], p["path"]) for r in written for p in r["places"]}
            entries = sources_of(json.loads(now))
            check(all((e["source"], e["path"]) in places for e in entries) and all(r["affair"] for r in written),
                  f"{name}: each of the {len(entries)} places in the record belongs to a row")

        everything = together.find_rows()
        entities = Counter(r["entity"] for r in everything if r["state"] == PLACED)
        found = {r["doc"] for r in together.find_rows(entity="category", value="Motion")}
        check(count > 0 and found == motions,
              f"{count} documents, {len(everything)} rows; the category \"Motion\" is found in {len(found)} of them")
        print("     placed by entity: " + ", ".join(f"{e} {entities[e]}" for e in names if entities[e]))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
