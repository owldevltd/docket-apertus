"""The vocabulary, without a model and without the network: a stem fills an empty store and a second filling
writes nothing; a type label is harmonised through the parliament's names before the table of all
parliaments; a person sets what a name stands for and takes it back, and adds a standard name of their own a
name can then stand for; a newer stem replaces what nobody changed and leaves a person's word; the routes
answer, and with a password set they need the account of the administration, reading as well. A small stem
of the test's own serves for that, so the checks do not move when OpenParlData changes its lists. The
shipped stem is only checked for its form.

    python3 tests/vocabulary.py
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.types import harmonize, harmonized  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract  # noqa: E402
from docket.server import serve  # noqa: E402
from docket.store.files import FileStore  # noqa: E402
from docket.store.vocabulary import LISTS, Vocabulary, load_stem, stem_rows, sync  # noqa: E402

MOTION = {"id": 1, "de": "Motion", "fr": "Motion", "it": "Mozione", "en": "Motion"}
POSTULATE = {"id": 2, "de": "Postulat", "fr": "Postulat", "it": "Postulato", "en": "Postulate"}
AMENDMENT = {"id": 3, "de": "Ergänzungsantrag", "fr": "Amendement", "it": "Emendamento", "en": "Amendment"}
GOVERNMENT = {"id": 4, "de": "Regierungsgeschäft", "fr": "Affaires gouvernementales", "it": "Affari governativi",
              "en": "Government affairs"}

STEM = {
    "source": "the test's own stem",
    "fetched": "2026-10-01",
    "lists": {
        "types": {
            "standards": [MOTION, POSTULATE, AMENDMENT, GOVERNMENT],
            "names": [
                {"body": "BS", "name": "Anzug", "lang": "de", "standard": 2},
                {"body": "BS", "name": "Antrag", "lang": "de", "standard": 3},
                {"body": "BS", "name": "Resolution", "lang": "de", "standard": None},
                {"body": "GR", "name": "Auftrag", "lang": "de", "standard": 1},
                {"body": "743", "name": "Richtlinienmotion", "lang": "de", "standard": 1},
            ],
        },
        "events": {"standards": [{"id": 1, "de": "Eingereicht", "fr": "Déposé", "it": "Presentato",
                                  "en": "Submitted", "count": 5}], "names": []},
        "groups": {"standards": [{"id": 1, "de": "Fraktion", "fr": "Groupe", "it": "Gruppo", "en": "Faction"}],
                   "names": []},
    },
}

# the table of all parliaments, as the export gives it: the label alone
TABLE = {
    "antrag": {"type": {k: GOVERNMENT[k] for k in ("de", "fr", "it", "en")}, "share": 0.88, "count": 100},
    "resolution": {"type": {k: MOTION[k] for k in ("de", "fr", "it", "en")}, "share": 1.0, "count": 10},
    "motion": {"type": {k: MOTION[k] for k in ("de", "fr", "it", "en")}, "share": 1.0, "count": 1000},
}


def call(base: str, route: str, body: dict | None = None, session: str = "") -> tuple[int, object]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base + route, data=data, method="POST" if data else "GET")
    if session:
        request.add_header("Cookie", session)
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def sign_in(base: str, user: str = "admin", password: str = "secret") -> str:
    """Signs in to the administration; the cookie of the session, empty when the server said no."""
    data = json.dumps({"user": user, "password": password}).encode("utf-8")
    try:
        with urllib.request.urlopen(urllib.request.Request(base + "/api/login", data=data, method="POST"),
                                    timeout=10) as r:
            return (r.headers.get("Set-Cookie") or "").split(";")[0]
    except urllib.error.HTTPError:
        return ""


def main() -> int:
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    def de(found: dict | None) -> str:
        return (found or {}).get("de") or "-"

    with tempfile.TemporaryDirectory() as tmp:
        store = FileStore(Path(tmp) / "store")
        counts = sync(store, STEM)
        check(counts == {"added": 11, "replaced": 0, "removed": 0, "kept": 0} and len(store.get_vocabulary()) == 11,
              f"the stem fills an empty store: {counts}")
        before = (Path(tmp) / "store" / "vocabulary.json").stat().st_mtime_ns
        counts = sync(store, STEM)
        same = (Path(tmp) / "store" / "vocabulary.json").stat().st_mtime_ns == before
        check(counts == {"added": 0, "replaced": 0, "removed": 0, "kept": 0} and same,
              "the same stem again writes nothing")

        # the type through the parliament's names, then through the table
        vocabulary = Vocabulary(store.get_vocabulary())
        check(de(harmonized("Antrag", TABLE)) == "Regierungsgeschäft", "the table alone: Antrag is government business")
        check(de(harmonized("Antrag", TABLE, vocabulary, "BS")) == "Ergänzungsantrag",
              "with the parliament: Antrag is an amendment in Basel-Stadt")
        got = harmonized("Antrag auf Einreichung einer Standesinitiative", TABLE, vocabulary, "BS")
        check(de(got) == "Ergänzungsantrag", "a longer label is found by its first word in the parliament's names")
        check(de(harmonized("Anzug (dringlich)", TABLE, vocabulary, "BS")) == "Postulat",
              "an addition in brackets does not hide the name")
        check(harmonized("Resolution", TABLE, vocabulary, "BS") is None,
              "a name the parliament lists without a standard has none, though the table knows one")
        check(de(harmonized("Motion", TABLE, vocabulary, "BS")) == "Motion",
              "a label the parliament does not list goes through the table")
        check(de(harmonized("Antrag", TABLE, vocabulary, "")) == "Regierungsgeschäft",
              "without a parliament the table answers as before")
        record = harmonize({"type_name": {"de": "Richtlinienmotion"}}, TABLE, vocabulary, "743")
        check(record.get("type_harmonized") == {"de": "Motion", "fr": "Motion", "it": "Mozione", "en": "Motion"},
              "the affair gets the harmonised type in four languages")

        # a person's word
        row = vocabulary.set("types", "GR", "Incarico", "Mozione", "tester")
        store.put_vocabulary([row])
        check(row["origin"] == "person" and row["standard"]["de"] == "Motion" and "stem" not in row
              and row["by"] == "tester", "a person adds a name, the standard named in any of its languages")
        check(de(harmonized("Incarico", TABLE, Vocabulary(store.get_vocabulary()), "GR")) == "Motion",
              "the added name is found")
        row = vocabulary.set("types", "BS", "Resolution", "Motion", "tester")
        store.put_vocabulary([row])
        check(row["origin"] == "person" and row["stem"] == {"standard": None, "fetched": "2026-10-01"},
              "a changed row keeps what the stem said")
        for wrong in (("types", "BS", "Resolution", "Dekret"), ("kinds", "BS", "Resolution", "Motion"),
                      ("types", "", "Resolution", "Motion")):
            try:
                vocabulary.set(*wrong, "tester")
                check(False, f"refused: {wrong}")
            except ValueError as e:
                check(True, f"refused: {e}")

        # a newer stem: Anzug stands for another type, Nidau's name is gone, Zürich's is new, and the stem
        # now has a standard for the name a person changed
        newer = copy.deepcopy(STEM)
        newer["fetched"] = "2026-11-01"
        names = newer["lists"]["types"]["names"]
        names[0]["standard"] = 1
        names[2]["standard"] = 2
        del names[4]
        names.append({"body": "ZH", "name": "Motion", "lang": "de", "standard": 1})
        counts = sync(store, newer)
        check(counts == {"added": 1, "replaced": 1, "removed": 1, "kept": 2}, f"a newer stem: {counts}")
        vocabulary = Vocabulary(store.get_vocabulary())
        check(de(harmonized("Anzug", TABLE, vocabulary, "BS")) == "Motion"
              and vocabulary.row("types", "743", "Richtlinienmotion") is None
              and vocabulary.row("types", "ZH", "motion")["fetched"] == "2026-11-01",
              "what nobody changed follows the newer stem")
        row = vocabulary.row("types", "BS", "Resolution")
        check(row["standard"]["de"] == "Motion" and row["stem"] == {"standard": {k: POSTULATE[k] for k in
              ("de", "fr", "it", "en")}, "fetched": "2026-11-01"},
              "a person's word stays, and beside it stands what the newer stem says")
        check(vocabulary.row("types", "GR", "Incarico")["origin"] == "person", "a name a person added stays")
        back, gone = vocabulary.reset("types", "BS", "Resolution")
        check(back is not None and gone is None and back["origin"] == "stem" and back["standard"]["de"] == "Postulat"
              and "by" not in back, "taken back, the row says what the stem says")
        back, gone = vocabulary.reset("types", "GR", "Incarico")
        check(back is None and gone is not None, "taken back, a name the stem never had goes")
        check(vocabulary.reset("types", "GR", "Auftrag") == (None, None), "a row of the stem has nothing to take back")

        # a standard name of a person's own
        own = vocabulary.add("types", {"de": "Volksmotion", "fr": " Motion  populaire ", "en": ""}, "tester")
        store.put_vocabulary([own])
        check(own["body"] == "" and own["origin"] == "person" and own["by"] == "tester" and own["label"] == "Volksmotion"
              and own["standard"] == {"de": "Volksmotion", "fr": "Motion populaire", "it": None, "en": None},
              "a person adds a standard name to a list, with the wordings given")
        for wrong in (("types", {"de": "volksmotion"}), ("types", {"de": "Neu", "it": "Mozione"}),
                      ("types", {"fr": "Sans allemand"}), ("kinds", {"de": "Neu"})):
            try:
                vocabulary.add(*wrong, "tester")
                check(False, f"refused: {wrong}")
            except ValueError as e:
                check(True, f"refused: {e}")
        row = vocabulary.set("types", "743", "Volksvorstoss", "Motion populaire", "tester")
        store.put_vocabulary([row])
        check(de(harmonized("Volksvorstoss", TABLE, Vocabulary(store.get_vocabulary()), "743")) == "Volksmotion",
              "a name of a parliament stands for the added standard name, and a type is harmonised to it")
        try:
            vocabulary.reset("types", "", "Volksmotion")
            check(False, "an added standard name a parliament's name stands for cannot be taken back")
        except ValueError as e:
            check(True, f"an added standard name in use stays: {e}")
        counts = sync(store, newer)
        check(counts["kept"] == 4 and Vocabulary(store.get_vocabulary()).row("types", "", "Volksmotion") is not None,
              f"a stem that does not know the added standard name leaves it: {counts}")
        _, gone = vocabulary.reset("types", "743", "Volksvorstoss")
        store.drop_vocabulary([gone])
        back, gone = vocabulary.reset("types", "", "Volksmotion")
        store.drop_vocabulary([gone])
        check(back is None and gone is not None and Vocabulary(store.get_vocabulary()).row("types", "", "Volksmotion")
              is None, "once no name stands for it, the added standard name is taken back")

        # the routes
        base_config = load_config()
        config = type(base_config)(**{**base_config.__dict__, "storage_dir": Path(tmp), "admin_password": "secret"})
        app = App(store, load_contract(config), config, Jobs(config))
        server = serve(app, 0, host="127.0.0.1")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            status, answer = call(base, "/api/vocabulary?list=types&body=BS")
            check(status == 401, f"without the account the vocabulary is not read: {answer.get('error')}")
            session = sign_in(base)
            check(bool(session), "the account signs in")
            status, rows = call(base, "/api/vocabulary?list=types&body=BS", None, session)
            check(status == 200 and [r["label"] for r in rows] == ["Antrag", "Anzug", "Resolution"],
                  "the names of a parliament are listed")
            status, rows = call(base, "/api/vocabulary?list=events", None, session)
            check(status == 200 and len(rows) == 1 and rows[0]["count"] == 5, "the standard names of a list are listed")
            body = {"list": "types", "body": "GR", "name": "Incarico", "standard": "Motion", "by": "tester"}
            status, answer = call(base, "/api/vocabulary", body)
            check(status == 401, f"changing without the account is refused: {answer.get('error')}")
            status, answer = call(base, "/api/vocabulary", body, session)
            check(status == 200 and answer["origin"] == "person" and answer["by"] == "admin",
                  "with the account a name is set, and it is by the account, whoever the request names")
            status, answer = call(base, "/api/vocabulary", {**body, "standard": "Dekret"}, session)
            check(status == 400, f"a standard the list does not have is refused: {answer.get('error')}")
            status, rows = call(base, "/api/vocabulary?list=types&body=GR", None, session)
            check(status == 200 and [r["label"] for r in rows] == ["Auftrag", "Incarico"], "the set name is stored")
            status, answer = call(base, "/api/vocabulary", {**body, "reset": True}, session)
            check(status == 200 and answer.get("removed") is True, "with reset it is taken back")
            status, answer = call(base, "/api/vocabulary", {**body, "reset": True}, session)
            check(status == 404, "taking back what nobody changed is 404")
            # a standard name of the administration's own, over the route
            new = {"list": "events", "standard": {"de": "Zurückgestellt", "fr": "Reporté", "it": "", "en": "Deferred"}}
            status, answer = call(base, "/api/vocabulary", new, session)
            check(status == 200 and answer["body"] == "" and answer["origin"] == "person" and answer["by"] == "admin"
                  and answer["standard"] == {"de": "Zurückgestellt", "fr": "Reporté", "it": None, "en": "Deferred"},
                  "the account adds a standard name to a list")
            status, answer = call(base, "/api/vocabulary", new, session)
            check(status == 400, f"the same standard name a second time is refused: {answer.get('error')}")
            status, rows = call(base, "/api/vocabulary?list=events", None, session)
            check(status == 200 and sorted(r["label"] for r in rows if r["body"] == "") == ["Eingereicht",
                                                                                           "Zurückgestellt"],
                  "the added standard name stands in the list")
            used = {"list": "events", "body": "GR", "name": "sistiert", "standard": "Zurückgestellt"}
            call(base, "/api/vocabulary", used, session)
            status, answer = call(base, "/api/vocabulary", {"list": "events", "body": "", "name": "Zurückgestellt",
                                                            "reset": True}, session)
            check(status == 409, f"while a name stands for it, it is not taken back: {answer.get('error')}")
            call(base, "/api/vocabulary", {**used, "reset": True}, session)
            status, answer = call(base, "/api/vocabulary", {"list": "events", "body": "", "name": "Zurückgestellt",
                                                            "reset": True}, session)
            check(status == 200 and answer.get("removed") is True, "afterwards it is")
            status, named = call(base, "/api/parliaments")
            check(status == 200 and isinstance(named, dict) and all("name" in p for p in named.values()),
                  f"the parliaments are listed by their key with their names ({len(named)})")
        finally:
            server.shutdown()
            app.jobs.stop()

    # the shipped stem: its form only
    shipped = load_stem(load_config().data_dir / "knowledge" / "vocabulary.json")
    check(shipped is not None and bool(shipped.get("fetched")), "the checkout ships a stem with the day it was fetched")
    if shipped is not None:
        rows = stem_rows(shipped)
        keys = {(r["list"], r["body"], r["name"]) for r in rows}
        check(len(keys) == len(rows) and {r["list"] for r in rows} == set(LISTS),
              f"its {len(rows)} rows are unique by list, body and name, in the {len(LISTS)} lists")
        named = [r for r in rows if r["body"]]
        ids = {s["id"] for s in shipped["lists"]["types"]["standards"]}
        known = all(n["standard"] is None or n["standard"] in ids for n in shipped["lists"]["types"]["names"])
        check(known, f"every name points at a standard of its list or at none ({len(named)} names of "
              f"{len({r['body'] for r in named})} parliaments)")
        # the roles: a parliament's name for a role stands for a standard role, known by OpenParlData's word
        roles = Vocabulary(rows)
        named_role = roles.row("roles", "BS", "Miturheber")
        added = roles.set("roles", "BS", "Erstunterzeichnende", "cosign", "tester")
        check(named_role is not None and named_role["key"] == "author" and named_role["standard"]["fr"] == "Auteur"
              and added["key"] == "cosign" and added["standard"]["de"] == "Mitunterzeichner/in",
              f"{len(roles.standards('roles'))} standard roles; a parliament's name stands for one, and a person "
              f"can add a name by the role's word")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
