"""What a person decides is kept at the row of the value, and the record follows the rows; without a model.

Affairs are formed from the stored runs of shipped documents the way a run does. Decisions are made through
the server's logic as the app makes them: a value changed, a value in the entry of another changed (the party
of a person), a value confirmed, a value rejected. Then: each decision stands at its row, with the value as
read left untouched; the record before any decision, made to follow the rows, is the record the decisions left;
a new run over the same documents, with the reviews taken out of the stored record, brings them all back from
the rows; a store whose rows are written anew takes the reviews from its records. A rule applied to many values
is written to their rows as well, and the affairs a rule would reach are the same asked of the rows as counted
over every record. A rule people accepted holds for what a later run reads: a value the rule fits is changed by
it at its row, once, with a review that names the rule.

    python3 tests/decisions.py <document dir> ...
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.merge import Document, values_of  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.fields.placer import blocks_of, day, get_at  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.runner import _write_affairs  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.review import sources_of  # noqa: E402
from docket.store.rows import fill_rows, find_value, follow  # noqa: E402
from docket.store.rules import apply, shape  # noqa: E402

RULE = {"id": "r-test", "field": "polity", "kind": "prefix-off", "parameter": "Kanton ", "state": "active"}


def known_person(config) -> dict:
    """A row of the register for the first name the Zürich document carries, read from the affair stored beside
    it: the test itself names nobody."""
    record = json.loads((config.data_dir / "documents" / "zuerich-219587" / "affair.json").read_text(encoding="utf-8"))
    label = record["contributors"]["data"][0]["fullname"]
    first, last = label.split(" ", 1)
    return {"body": "X", "key": label.lower(), "label": label, "first": first, "last": last, "ids": [4711],
            "origin": "stem"}


def main(argv: list[str]) -> int:
    dirs = {d.name: d for d in (Path(a) for a in argv if not a.startswith("--")) if (d / "run.json").is_file()}
    if not dirs:
        print("usage: python3 tests/decisions.py <document dir> ...")
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

    def run(config, out: Path, names: list[str], one_party: bool = False, parliament: str = "",
            printed: tuple[str, str] | None = None) -> dict[str, str]:
        """Forms the affairs of these documents from their stored runs; returns the affair's key per document.
        With `parliament` the documents count as that parliament's, whatever the run told; with `printed` the
        first labelled list of every document prints this label with this value as well."""
        out.mkdir(exist_ok=True)
        documents = []
        for name in names:
            stored = json.loads((dirs[name] / "run.json").read_text(encoding="utf-8"))
            if one_party:
                # one party for all the names: a single read value that goes into several entries
                stored["fields"]["party"]["items"] = stored["fields"]["party"]["items"][:1]
            if printed:
                listed = next(b for b in blocks_of(stored["body"]) if b["type"] == "def-list")
                listed["items"].append({"term": printed[0], "def": printed[1]})
            report = {"identity": stored["identity"], "kind": stored.get("kind"), "fields": stored["fields"]}
            (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            values = values_of(stored["fields"])
            date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
            identity = stored["identity"]
            documents.append(Document(len(documents) + 1, name, stored["pages"], stored["body"], values,
                                      identity.get("key") or "dok-" + name, date,
                                      parliament or identity.get("body") or ""))
        made = _write_affairs(out, documents, fields, contract, knowledge, config, lambda line: None)
        return {name: a["key"] for a in made for name in a["documents"]}

    def decided(store, name: str) -> list[tuple[str, str, object, object]]:
        return [(r["field"], d["review"]["decision"], d["of"], d["value"])
                for r in store.get_rows(name) for d in r.get("decisions") or []]

    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        name = "zuerich-219587"
        store = open_store(config)
        # a register that knows one of the names, so that the affair holds the id of a person
        store.put_register([known_person(base)])
        key = run(config, Path(tmp) / "out", [name], one_party=True, parliament="X")[name]
        app = App(store, contract, config, Jobs(config))
        before = store.get_affair(key)["record"]
        told = next(e for e in sources_of(before) if e["label"] == "contributors.person_id")
        head = app.head(before)
        kind = (before.get("type_harmonized") or {}).get("de") or before["type_name"]["de"]
        check(head["number"] == before.get("number") and head["title"] == before["title"]["de"]
              and head["type"] == kind and told["value"] == 4711,
              f"{name}: number, title and type for the head come by role and entity; a name is told as a person")
        entries = {e["label"]: e for e in reversed(sources_of(before))}
        # the entries of the authors: the ones with a party beside the name
        people = [e for e in sources_of(before) if any(".party." in p for p in e.get("values") or {})]
        second = people[1]
        party_path = next(p for p in second["values"] if ".party." in p)
        rows = store.get_rows(name)
        party_rows = [r for r in rows if r["field"] == "party" and r["places"]]
        check(len(party_rows) == 1 and len(party_rows[0]["places"]) == len(people) > 1,
              f"{name}: one read party sits in the entries of {len(people)} names")

        # what the app is shown: every value with the id of its row, which names it in a decision
        shown = {e["source"]: e for e in app.affair(key)["sources"]}
        ids = [i for e in shown.values() for i in (e.get("ids") or {e["path"]: e["id"]}).values()]
        found = [find_value(rows, i) for i in ids]
        check(len(set(ids)) == len(ids) and all(h is not None for h in found)
              and all(e.get("field") for e in shown.values()),
              f"{name}: each of the {len(ids)} values shown carries the id of its row and the field it was read under")
        asked = [
            {"id": shown[entries["title"]["source"]]["id"], "decision": "changed", "by": "test",
             "after": "Ein neuer Titel"},
            {"id": shown[second["source"]]["ids"][party_path], "decision": "changed", "by": "test", "after": "GLP"},
            {"id": shown[second["source"]]["id"], "decision": "confirmed", "by": "test"},
            # the place in the record still names a value, as before the ids
            {"source": entries["polity"]["source"], "decision": "rejected", "by": "test"},
            {"id": shown[told["source"]]["id"], "decision": "rejected", "by": "test"},
        ]
        check(shown[told["source"]]["id"].endswith("/id") and ":" in shown[second["source"]]["ids"][party_path],
              f"{name}: the id of a person and a party in the entry of a name are told apart from the row's own value")
        check(all(app.decide(key, body)[0] == 200 for body in asked),
              f"{name}: five decisions taken, four by the id of the row and one by the place in the record")
        status, answer = app.decide(key, {"id": name + "#99999", "decision": "confirmed", "by": "test"})
        check(status == 400, f"{name}: an id no row carries is refused")
        counted = [(r["field"], r["kind"], r["parameter"]) for r in store.get_rules()]
        logged = [(d["field"], d["before"], d["after"]) for d in store.list_decisions(key)]
        check(("party", "value", "Grüne") in counted and not any(f.startswith("contributors") for f, _, _ in counted)
              and ("party", "Grüne", "GLP") in logged,
              f"{name}: the changed party counts for the field of the party, not for the name beside it")
        after = store.get_affair(key)["record"]
        rows = store.get_rows(name)
        owner = next(r for r in rows if r["field"] == "authors" and any(
            p["source"] == second["source"] for p in r["places"]))
        got = sorted(decided(store, name), key=str)
        want = sorted([("title", "changed", None, "Ein neuer Titel"), ("party", "changed", owner["n"], "GLP"),
                       ("authors", "confirmed", None, None), ("polity", "rejected", None, None),
                       ("authors", "rejected", None, None)], key=str)
        on_id = [d for r in rows for d in r.get("decisions") or [] if d.get("part") == "id"]
        check(len(on_id) == 1 and on_id[0]["review"]["decision"] == "rejected",
              f"{name}: the decision on the id of the person stands at the row of the name")
        check(got == want,
              f"{name}: each decision stands at the row of its value, the party's for the entry it was made on")
        read = {r["field"]: r["value"] for r in rows if r.get("decisions")}
        check(read["title"] == entries["title"]["value"] and read["party"] != "GLP",
              f"{name}: the rows keep the values as read")
        others = [get_at(after, p.split(".")) for e in people if e is not second for p in e["values"] if ".party." in p]
        check(get_at(after, party_path.split(".")) == "GLP" and "GLP" not in others,
              f"{name}: the change of one entry leaves the same party in the other entries")
        check(follow(before, rows)[0] == after,
              f"{name}: the record from before, following the rows, is the record now")

        # a new run, the stored record without its reviews: only the rows still hold the decisions
        store.save_record(key, before)
        made = run(config, Path(tmp) / "out", [name], one_party=True, parliament="X")
        check(made[name] == key and store.get_affair(key)["record"] == after,
              f"{name}: a new run brings every decision back from the rows")
        run(config, Path(tmp) / "out", [name], one_party=True, parliament="X")
        check(store.get_affair(key)["record"] == after and sorted(decided(store, name), key=str) == want,
              f"{name}: and a further run changes nothing")

        # rows written anew for a store that has the reviews in its records only
        store.put_rows(name, [])
        fill_rows(store, fields, contract, knowledge.types)
        adopted = store.get_rows(name)
        check(len(decided(store, name)) == 4 and follow(after, adopted)[0] == after,
              f"{name}: rows written anew take the reviews from the record, one per source")

    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        keys = run(config, Path(tmp) / "out", sorted(dirs))
        store = open_store(config)
        app = App(store, contract, config, Jobs(config))
        everything = store.list_affairs()

        def over_all(rule: dict) -> tuple[int, set[str]]:
            hits = [(a["key"], e) for a in everything for e in sources_of(a["record"])
                    if e["label"] == rule["field"] and e["review"] is None and e["value"] is not None
                    and apply(rule, str(e["value"])) is not None]
            return len(hits), {k for k, _ in hits}

        count, reached = over_all(RULE)
        read = app._affairs_with([(RULE["field"], lambda v: apply(RULE, v) is not None)])
        reach = app._reach(RULE)
        check(count > 1 and reach["count"] == count and reach["affairs"] == len(reached)
              and {a["key"] for a in read} == reached,
              f"a rule reaches {reach['count']} values in {reach['affairs']} affairs, asked of the rows; "
              f"{len(read)} of {len(everything)} records read")
        same_old = {}
        for a in everything:
            for e in sources_of(a["record"]):
                if e["open"]:
                    same_old[(a["key"], e["source"])] = sum(
                        1 for b in everything if b["key"] != a["key"] for o in sources_of(b["record"])
                        if (o["label"], o["how"]) == (e["label"], e["how"])
                        and shape(str(o["value"])) == shape(str(e["value"])))
        same_new = {(k, e["source"]): e["same"]["count"] for k in set(keys.values())
                    for e in app.affair(k)["sources"] if e["open"]}
        check(same_new == same_old, f"the count of similar values in other affairs is the same for all "
                                    f"{len(same_old)} open values, asked of the rows")
        # what a document was asked: counted over the store, so that "never asked" is told from "nothing found"
        told = app.definition()
        check(told["documents"] == len(dirs) and not told["gone"]
              and all(f["asked"] == len(dirs) and f["never"] == 0 for f in told["fields"]),
              f"every one of the {len(told['fields'])} fields was asked in all {told['documents']} documents")
        earlier = {n: {} for n in fields.fields if n != "summary"}
        store.put_fields("read-earlier", {"fields": {**earlier, "left": {}}})
        told = app.definition()
        by = {f["name"]: f for f in told["fields"]}
        check(by["summary"]["never"] == 1 and by["title"]["never"] == 0
              and told["gone"] == [{"name": "left", "asked": 1}]
              and by["type"]["lookup"] == "vocabulary" and by["authors"]["lookup"] == "register",
              "a document read before a field existed counts as never asked for it; a field the definition "
              "dropped is told as gone")
        applied = app._apply_rule(RULE)
        by_rule = [(r["doc"], d["value"]) for r in store.find_rows(field="polity")
                   for d in r.get("decisions") or [] if d["review"].get("rule") == RULE["id"]]
        check(applied == count and len(by_rule) == count and all(not v.startswith("Kanton ") for _, v in by_rule),
              f"a rule applied to {applied} values is written to their rows")

    # a rule people accepted holds for what a later run reads: the number is what stands at a label
    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        name = "nidau-m185"
        store = open_store(config)
        store.put_rules([{"id": "r-0001", "field": "number", "kind": "label", "parameter": "vorstoss-nr.",
                          "count": 2, "against": 0, "confirmed": 0, "withdrawn": 0, "applied": 0, "active": True,
                          "state": "active", "since": None, "examples": []}])
        read = json.loads((dirs[name] / "run.json").read_text(encoding="utf-8"))["fields"]["number"]["items"][0]
        key = run(config, Path(tmp) / "out", [name], printed=("Vorstoss-Nr.:", "M 185"))[name]
        record = store.get_affair(key)["record"]
        entry = next(e for e in sources_of(record) if e["label"] == "number")
        review = entry["review"] or {}
        logged = [d for d in store.list_decisions(key) if d.get("rule") == "r-0001"]
        check(entry["value"] == "M 185" and review.get("by") == "rule" and review.get("rule") == "r-0001"
              and review.get("before") == read["value"] and len(logged) == 1 and logged[0]["after"] == "M 185"
              and store.get_rules()[0]["applied"] == 1,
              f"{name}: the run reads {read['value']!r}, the accepted rule sets what stands at the label, M 185, "
              f"and it is logged")
        kept = next(r for r in store.get_rows(name) if r["field"] == "number" and r["state"] == "placed")
        check(kept["value"] == read["value"] and len(kept.get("decisions") or []) == 1,
              f"{name}: the row keeps the value as read and holds the rule's decision")
        run(config, Path(tmp) / "out", [name], printed=("Vorstoss-Nr.:", "M 185"))
        again = next(e for e in sources_of(store.get_affair(key)["record"]) if e["label"] == "number")
        check(again["value"] == "M 185" and store.get_rules()[0]["applied"] == 1
              and len([d for d in store.list_decisions(key) if d.get("rule") == "r-0001"]) == 1,
              f"{name}: a further run applies it no second time")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
