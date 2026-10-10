"""The store's operations, without a model: an affair is stored, read, replaced and listed, a fields report
and the decisions come back, rules, vocabulary rows and rows of the register are replaced by their key and
dropped, and a second opening sees what the first one wrote. Over the file store, and over Postgres when a
database is named: the test works there in a schema of its own and removes it at the end, so a store in use
is not touched.

    python3 tests/store.py [--postgres=<url>]
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.store.base import Store  # noqa: E402
from docket.store.files import FileStore  # noqa: E402

MOTION = {"de": "Motion", "fr": "Motion", "it": "Mozione", "en": "Motion"}


def run(name: str, open_again, check) -> None:
    """The same operations on a store; open_again() opens the store a second time."""
    store: Store = open_again()
    record = {"schema": "0.8", "title": {"de": "Prüfung mit Umlauten: Zürich"}}
    store.put_affair("nr-1", record, [{"name": "a", "id": 1, "pages": 2}])
    got = store.get_affair("nr-1")
    check(got is not None and got["record"] == record and got["documents"][0]["pages"] == 2,
          f"{name}: an affair comes back as stored")
    store.put_affair("nr-1", {**record, "number": "1"}, [{"name": "a", "id": 1, "pages": 2}])
    check(store.get_affair("nr-1")["record"].get("number") == "1" and len(store.list_affairs()) == 1,
          f"{name}: a second put under the key replaces")
    store.save_record("nr-1", {**record, "number": "2"})
    check(store.get_affair("nr-1")["record"]["number"] == "2", f"{name}: the record is replaced after a decision")
    try:
        store.save_record("nr-none", record)
        check(False, f"{name}: the record of an unknown affair is refused")
    except KeyError:
        check(True, f"{name}: the record of an unknown affair is refused")
    check(store.get_affair("nr-none") is None, f"{name}: an unknown affair is none")

    store.put_fields("a", {"fields": {"title": {"state": "placed"}}})
    check(store.get_fields("a") == {"fields": {"title": {"state": "placed"}}} and store.get_fields("b") is None,
          f"{name}: a fields report comes back")
    store.add_decision({"affair": "nr-1", "decision": "confirmed", "by": "test"})
    store.add_decision({"affair": "nr-2", "decision": "changed", "by": "test"})
    check([d["affair"] for d in store.list_decisions()] == ["nr-1", "nr-2"] and len(store.list_decisions("nr-2")) == 1,
          f"{name}: the decisions come in their order, and per affair")

    rule = {"id": "r-0001", "field": "polity", "kind": "prefix-off", "parameter": "Kanton ", "active": False}
    store.put_rules([rule])
    store.put_rules([{**rule, "active": True}])
    check(store.get_rules() == [{**rule, "active": True}], f"{name}: a rule is replaced by its id")

    rows = [
        {"list": "types", "body": "", "name": "motion", "label": "Motion", "standard": MOTION, "origin": "stem"},
        {"list": "types", "body": "GR", "name": "auftrag", "label": "Auftrag", "standard": MOTION, "origin": "stem"},
        {"list": "types", "body": "BS", "name": "resolution", "label": "Resolution", "standard": None,
         "origin": "stem"},
    ]
    store.put_vocabulary(rows)
    check(len(store.get_vocabulary()) == 3, f"{name}: vocabulary rows are stored")
    store.put_vocabulary([{**rows[2], "standard": MOTION, "origin": "person", "by": "test"}])
    held = {(r["list"], r["body"], r["name"]): r for r in store.get_vocabulary()}
    check(len(held) == 3 and held[("types", "BS", "resolution")]["origin"] == "person"
          and held[("types", "", "motion")]["standard"]["it"] == "Mozione",
          f"{name}: a vocabulary row is replaced by list, body and name")
    store.drop_vocabulary([rows[1]])
    check([r["body"] for r in store.get_vocabulary()] == ["", "BS"], f"{name}: a vocabulary row is dropped")

    people = [
        {"body": "X", "key": "ignaz pellaton", "label": "Ignaz Pellaton", "ids": [1], "origin": "stem"},
        {"body": "X", "key": "katja brand", "label": "Katja Brand", "origin": "candidate", "documents": ["a"]},
        {"body": "Y", "key": "ignaz pellaton", "label": "Ignaz Pellaton", "ids": [2], "origin": "stem"},
    ]
    store.put_register(people)
    store.put_register([{**people[1], "documents": ["a", "b"]}])
    held = {r["key"]: r for r in store.get_register("X")}
    check(len(held) == 2 and held["katja brand"]["documents"] == ["a", "b"] and store.get_register("Y")[0]["ids"] == [2]
          and store.register_bodies() == ["X", "Y"] and store.get_register("Z") == [],
          f"{name}: the register is kept per parliament, a row replaced by its key")
    store.drop_register([people[1]])
    check([r["key"] for r in store.get_register("X")] == ["ignaz pellaton"], f"{name}: a row of the register is dropped")

    again: Store = open_again()
    check(len(again.list_affairs()) == 1 and len(again.get_rules()) == 1 and len(again.get_vocabulary()) == 2
          and len(again.list_decisions()) == 2 and len(again.get_register("X")) == 1,
          f"{name}: a second opening sees the same")


def main(argv: list[str]) -> int:
    url = next((a[11:] for a in argv if a.startswith("--postgres=")), "")
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    with tempfile.TemporaryDirectory() as tmp:
        run("files", lambda: FileStore(Path(tmp) / "store"), check)
        if url:
            import psycopg

            from docket.store.postgres import PostgresStore

            schema = f"docket_test_{os.getpid()}"
            inside = url + ("&" if "?" in url else "?") + f"options=-csearch_path%3D{schema}"
            with psycopg.connect(url, autocommit=True) as db:
                db.execute(f"CREATE SCHEMA {schema}")
            try:
                run("postgres", lambda: PostgresStore(inside, Path(tmp) / "pg"), check)
                with psycopg.connect(url) as db:
                    row = db.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = %s",
                                     (schema,)).fetchone()
                check(row[0] == 6, f"postgres: the six tables stand in the test's own schema ({row[0]})")
            finally:
                with psycopg.connect(url, autocommit=True) as db:
                    db.execute(f"DROP SCHEMA {schema} CASCADE")
        else:
            print("     postgres: not run, no --postgres=<url>")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
