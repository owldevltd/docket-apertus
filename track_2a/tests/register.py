"""The register of persons, without a model and without the network: a printed name is cleaned of what
follows it; it is found exactly in either order, by the last name alone, or with one character off, and only
when exactly one person fits; a name nobody carries becomes a candidate and, from the third document on, a
learnt person; a newer list replaces what came from OpenParlData and leaves what was learnt; the contributors
of an affair get the person's id with a place, flagged where the name was not found exactly; the routes answer.
A small register of the test's own serves for that.

    python3 tests/register.py
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.persons import link_persons  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract  # noqa: E402
from docket.server import serve  # noqa: E402
from docket.store.files import FileStore  # noqa: E402
from docket.store.register import LEARN_AT, Register, clean_name, near, stop_words, sync  # noqa: E402

PERSONS = [
    {"id": 1, "body": "X", "first": "Ignaz", "last": "Pellaton", "party": "Les Verts"},
    {"id": 2, "body": "X", "first": "Hans", "last": "Graf"},
    {"id": 3, "body": "X", "first": "Eva", "last": "Graf"},
    {"id": 4, "body": "X", "first": "Katrin", "last": "Lüthold", "party": "SP"},
    # the same name twice in one parliament: two persons
    {"id": 5, "body": "X", "first": "Peter", "last": "Meier"},
    {"id": 6, "body": "X", "first": "Peter", "last": "Meier"},
    {"id": 7, "body": "Y", "first": "Katrin", "last": "Lüthold"},
]
GROUPS = [{"list": "groups", "body": "", "name": "kommission", "label": "Kommission",
           "standard": {"de": "Kommission", "fr": "Commission", "it": "Commissione", "en": "Committee"}}]


def call(base: str, route: str, body: dict | None = None, token: str = "") -> tuple[int, object]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base + route, data=data, method="POST" if data else "GET")
    if token:
        request.add_header("X-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def main() -> int:
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    for printed, want in (("Armin Feldhaus, Uster", "Armin Feldhaus"), ("Linus Strehl (SVP)", "Linus Strehl"),
                          ("Dr. Remo Moret", "Remo Moret"), ("Hofer Ruedi und Mit.", "Hofer Ruedi"),
                          ("Hugentobler (Bremgarten", "Hugentobler"), ("Luca Tamborini PLR", "Luca Tamborini"),
                          ("Ignaz PELLATON", "Ignaz PELLATON")):
        got = clean_name(printed)
        check(got == want, f"a printed name without what follows it: {printed!r} -> {got!r}")
    check(near("graf", "gras") and near("graf", "graaf") and near("graf", "raf") and not near("graf", "gross"),
          "one character apart: replaced, one too many, one missing; two are too far")

    with tempfile.TemporaryDirectory() as tmp:
        store = FileStore(Path(tmp) / "store")
        counts = sync(store, PERSONS, "2026-10-01")
        check(counts == {"added": 6, "replaced": 0, "removed": 0, "kept": 0} and store.register_bodies() == ["X", "Y"],
              f"a list of persons fills the register, the same name of one parliament as one row: {counts}")
        check(sync(store, PERSONS, "2026-10-01") == {"added": 0, "replaced": 0, "removed": 0, "kept": 0},
              "the same list again changes nothing")

        register = Register(store, "X")
        cases = [
            ("Ignaz Pellaton", "exact", 1), ("PELLATON Ignaz", "exact", 1),
            ("Dr. Ignaz Pellaton (Les Verts)", "exact", 1),
            ("M. lgnaz PELLATON", "near", 1), ("Lüthold Katrin, SP", "exact", 4), ("Pellaton", "surname", 1),
            ("Graf", "several", None), ("Hans Graf", "exact", 2), ("Hans Gras", "near", 2), ("Eva Gra", "none", None),
            ("Peter Meier", "several", None), ("Unbekannt Person", "none", None),
        ]
        for printed, how, pid in cases:
            m = register.find(printed)
            ids = (m.person or {}).get("ids") if m.person else None
            check(m.how == how and (ids == [pid] if pid else m.person is None), f"{printed!r} is found as {m.how}"
                  + (f", person {ids[0]}" if ids else ""))
        elsewhere, nowhere = Register(store, "Y").find("Pellaton"), Register(store, "").find("Ignaz Pellaton")
        check(elsewhere.how == "none" and nowhere.how == "none",
              "a name is looked up in its own parliament only, and nowhere without one")

        # learning
        stop = stop_words(GROUPS)
        check("kommission" in stop and "commission" in stop,
              f"the words of organs come from the vocabulary: {sorted(stop)}")
        no_names = ("Ratssekretär", "Kommission für Sicherheit", "Finanzkommission Riehen", "b20", "AfGE",
                    "22.11.2018 Bern")
        for value in no_names:
            check(register.learn(value, "doc-0", stop) is None, f"{value!r} is no name to learn")
        row = register.learn("Katja Brand (glp)", "doc-1", stop)
        check(row is not None and row["origin"] == "candidate" and row["label"] == "Katja Brand"
              and row["documents"] == ["doc-1"], "an unknown name becomes a candidate with the document it stood in")
        register.learn("Katja Brand", "doc-1", stop)
        row = Register(store, "X").learn("Brand Katja", "doc-9", stop)
        check(row["origin"] == "candidate" and row["key"] == "brand katja",
              "the other order of the name is another candidate: nothing says which word is the last name")
        register = Register(store, "X")
        register.learn("Katja Brand", "doc-1", stop)
        row = register.learn("Katja Brand", "doc-2", stop)
        check(row["origin"] == "candidate" and len(row["documents"]) == 2
              and register.find("Katja Brand").how == "none",
              "the same document counts once; with two documents it is still a candidate and not found")
        row = register.learn("Katja Brand, Riehen", "doc-3", stop)
        check(LEARN_AT == 3 and row["origin"] == "learned" and row["last"] == "Brand" and row["ids"] == [],
              "from the third document on it is a learnt person, without an id")
        fresh = Register(store, "X")
        check(fresh.find("Katja Brand").how == "exact" and fresh.find("Katja Brant").how == "near"
              and fresh.find("Katja Brand").person["origin"] == "learned",
              "a learnt person is found, also one character off")

        # a newer list: Hans Graf is gone, Katja Brand is now known there, a new person comes
        newer = [p for p in PERSONS if p["id"] != 2] + [{"id": 8, "body": "X", "first": "Katja", "last": "Brand"},
                                                         {"id": 9, "body": "X", "first": "Beat", "last": "Braun"}]
        counts = sync(store, newer, "2026-11-01")
        check(counts["added"] == 1 and counts["removed"] == 1 and counts["kept"] == 1, f"a newer list: {counts}")
        fresh = Register(store, "X")
        known = fresh.find("Katja Brand").person
        check(known["origin"] == "stem" and known["ids"] == [8]
              and known["seen"]["documents"] == ["doc-1", "doc-2", "doc-3"],
              "a learnt person the new list knows becomes theirs, with what was seen kept")
        check(fresh.find("Hans Graf").how == "none" and fresh.find("Graf").how == "surname"
              and fresh.find("Beat Braun").how == "exact", "what the list dropped is gone, what it brought is there")
        check(any(r["key"] == "brand katja" and r["origin"] == "candidate" for r in store.get_register("X")),
              "a candidate the list does not know stays")

        # the contributors of an affair
        config = load_config()
        contract = load_contract(config)

        def person(name: str, how: str = "literal") -> dict:
            return {"role": {"de": "Urheber/in"}, "fullname": name, "source": {"doc": 1, "block": "b3", "how": how}}

        record = {"schema": "0.8", "docs": {"data": [{"id": 1, "name": "doc-a", "page-count": 1, "body": [
            {"id": "b3", "page": 1, "type": "p", "x": 0, "y": 0, "width": 10, "height": 10, "text": "names"}]}]},
            "contributors": {"data": [
                person("Ignaz Pellaton"), person("Pellaton"), person("M. lgnaz PELLATON"), person("Meier"),
                person("Neue Person"), person("Erfundener Name", "cited"),
                {"fullname": "From the API", "person_id": 77},
            ]}}
        report = link_persons(record, {1: "X"}, {1: "doc-a"}, store, stop)
        data = record["contributors"]["data"]
        check([d.get("person_id") for d in data] == [1, 1, 1, None, None, None, 77],
              "exact, last name and one character off give the person's id; several and none give nothing")
        places = {s["path"]: s for s in record["sources"]}
        check(set(places) == {f"contributors.data.{i}.person_id" for i in (0, 1, 2)}
              and "approve" not in places["contributors.data.0.person_id"]
              and places["contributors.data.1.person_id"].get("approve") is True
              and places["contributors.data.2.person_id"].get("approve") is True
              and places["contributors.data.0.person_id"]["how"] == "derived",
              "the id has a place of its own, for a person to look at where the name was not found exactly")
        check(data[2]["fullname"] == "M. lgnaz PELLATON", "the printed name stays as it stands")
        hows = [(line["value"], line["how"]) for line in report["doc-a"]]
        wanted = [("Ignaz Pellaton", "exact"), ("Pellaton", "surname"), ("M. lgnaz PELLATON", "near"),
                  ("Meier", "several"), ("Neue Person", "none"), ("Erfundener Name", "none")]
        check(hows == wanted, "the report says what became of every name")
        rows = {r["key"]: r for r in store.get_register("X")}
        check(rows.get("neue person", {}).get("origin") == "candidate" and "erfundener name" not in rows,
              "only a name that stands literally in the document is given to the register to learn")
        check(contract.check(record) == [], "the record with the ids fits the contract")
        alone = {"contributors": {"data": [person("Ignaz Pellaton")]}}
        check(link_persons(alone, {1: ""}, {1: "doc-b"}, store, stop)
              == {"doc-b": [{"value": "Ignaz Pellaton", "how": "no parliament"}]},
              "without a parliament nothing is looked up")

        # the routes, and the name beside the id
        store.put_affair("nr-1", record, [{"name": "doc-a", "id": 1, "pages": 1}])
        store.put_fields("doc-a", {"identity": {"body": "X"}, "fields": {}})
        secret = type(config)(**{**config.__dict__, "storage_dir": Path(tmp), "admin_token": "secret"})
        app = App(store, contract, secret, Jobs(secret))
        server = serve(app, 0, host="127.0.0.1")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            status, affair = call(base, "/api/affairs/nr-1")
            hints = [e.get("hint") for e in affair["sources"] if e["label"] == "contributors.person_id"]
            check(status == 200 and hints == ["Ignaz Pellaton (Les Verts)"] * 3,
                  f"beside the id stands who is meant: {hints[:1]}")
            status, rows = call(base, "/api/register?body=X")
            check(status == 200 and len(rows) == len(store.get_register("X")),
                  f"the persons of a parliament are listed ({len(rows)})")
            status, rows = call(base, "/api/register")
            check(status == 200 and sorted(r["key"] for r in rows) == ["brand katja", "neue person"],
                  "without a parliament: what the register learnt and what it still counts")
            body = {"body": "X", "key": "neue person"}
            status, answer = call(base, "/api/register", body)
            check(status == 403, f"taking a row out without the token is refused: {answer.get('error')}")
            status, answer = call(base, "/api/register", body, "secret")
            left = {r["key"] for r in store.get_register("X")}
            check(status == 200 and answer.get("removed") is True and "neue person" not in left,
                  "with the token a candidate is taken out")
            status, answer = call(base, "/api/register", {"body": "X", "key": "ignaz pellaton"}, "secret")
            check(status == 409, f"a person of OpenParlData's list is not taken out: {answer.get('error')}")
        finally:
            server.shutdown()
            app.jobs.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
