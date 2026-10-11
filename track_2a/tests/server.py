"""The web server over a file store, without a model: the routes answer, the app is served per language and
an address without one goes on to the German build, a record of an older store is given its id, a decision
lands at the source and keeps the record valid, with an account it is by the account, a wrong decision is
refused, and a new run over the same document keeps the review.

    python3 tests/server.py --store=<file store dir> [--pages=<analyzed dir>]
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket import server as web  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.pipeline import load_contract  # noqa: E402
from docket.server import serve  # noqa: E402
from docket.store.files import FileStore  # noqa: E402
from docket.store.review import carry_reviews, sources_of  # noqa: E402


def call(base: str, route: str, body: dict | None = None, session: str = "") -> tuple[int, object]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base + route, data=data, method="POST" if data else "GET")
    if data:
        request.add_header("Content-Type", "application/json")
    if session:
        request.add_header("Cookie", session)
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            raw = r.read()
            kind = r.headers.get("Content-Type", "")
            return r.status, json.loads(raw.decode("utf-8")) if kind.startswith("application/json") else raw
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def languages(base: str) -> bool:
    """The app per language, on two builds of one line each in place of the real ones: a folder with a page
    is a language, an unknown address under it shows its page, a file under it is the file, nothing outside
    the folder is read, and an address without a language lands in the German build with its rest kept."""
    built = web.APP
    with tempfile.TemporaryDirectory() as tmp:
        web.APP = Path(tmp).resolve()
        try:
            for language in ("de", "fr"):
                (web.APP / language).mkdir()
                (web.APP / language / "index.html").write_text(f"<title>{language}</title>", encoding="utf-8")
            (web.APP / "fr" / "main.js").write_text("//fr", encoding="utf-8")
            (web.APP / "secret.txt").write_text("outside", encoding="utf-8")
            want = {
                "/": b"<title>de</title>",
                "/affairs/nr-x?tab=events": b"<title>de</title>",
                "/de/affairs/nr-x": b"<title>de</title>",
                "/fr/": b"<title>fr</title>",
                "/fr/documents/a%20b": b"<title>fr</title>",
                "/fr/main.js": b"//fr",
                "/fr/../secret.txt": b"<title>fr</title>",
                "/it/": b"<title>de</title>",
            }
            got = {route: call(base, route) for route in want}
            with urllib.request.urlopen(base + "/affairs/nr-x?tab=events", timeout=10) as r:
                landed = r.url
            return all(got[route] == (200, page) for route, page in want.items()) \
                and landed == base + "/de/affairs/nr-x?tab=events"
        finally:
            web.APP = built


def main(argv: list[str]) -> int:
    store_dir = next((Path(a[8:]) for a in argv if a.startswith("--store=")), None)
    if store_dir is None or not store_dir.is_dir():
        print("usage: python3 tests/server.py --store=<file store dir>")
        return 1
    store = FileStore(store_dir)
    config = load_config()
    app = App(store, load_contract(config), config)
    server = serve(app, 0, host="127.0.0.1")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    try:
        status, health = call(base, "/api/health")
        check(status == 200 and health.get("store") == "files", f"health: {health}")
        status, page = call(base, "/")
        check(status == 200 and b"<title>" in page, "the app's page is served")
        check(languages(base), "each language has its build, an address without one goes on to the German one")
        status, affairs = call(base, "/api/affairs")
        check(status == 200 and isinstance(affairs, list) and len(affairs) > 0, f"{len(affairs)} affairs listed")
        with_place = next((a for a in affairs if a["counts"]["places"] > 0), None)
        check(with_place is not None, "an affair with a value that has a place")
        word = next((w for a in affairs for w in str(a["title"] or "").split() if len(w) > 6), None)
        if word is not None:
            status, hits = call(base, "/api/affairs?q=" + urllib.parse.quote(word.lower()))
            with_word = {a["key"] for a in affairs if word.lower() in str(a["title"] or "").lower()}
            check(status == 200 and with_word <= {a["key"] for a in hits} and len(hits) <= len(affairs),
                  f"the search for a word of a title finds its affair: {len(hits)} of {len(affairs)} for '{word}'")
        status, none = call(base, "/api/affairs?q=zzzqqqxxx")
        check(status == 200 and none == [] and all("date" in a and "papers" in a and "body" in a for a in affairs),
              "a search for nothing that is there finds nothing; every affair comes with date, parliament, documents")
        if with_place is None:
            return 1
        key = with_place["key"]
        status, affair = call(base, f"/api/affairs/{key}")
        places = len(affair.get("sources") or [])
        check(status == 200 and affair["key"] == key and places > 0, f"affair {key}: {places} places")
        status, alone = call(base, f"/api/records/{key}")
        check(status == 200 and alone == affair["record"] and alone.get("id") == key,
              "the affair alone is served in the affair schema, and names itself")
        # a store filled before a record named itself: the record is given its id again, and its parliament
        # from what the run of its document noted
        held = store.get_affair(key)
        paper = held["documents"][0]["name"]
        report = store.get_fields(paper) or {}
        store.put_fields(paper, {**report, "identity": {**(report.get("identity") or {}), "body": "ZZ"}})
        store.put_affair(key, {k: v for k, v in held["record"].items() if k not in ("id", "body_key")},
                         held["documents"])
        _, bare = call(base, f"/api/records/{key}")
        named = app.name_records()
        _, again = call(base, f"/api/records/{key}")
        check("id" not in bare and named == 1 and list(again)[:3] == ["schema", "id", "body_key"]
              and again == {**alone, "body_key": "ZZ"} and app.name_records() == 0,
              "an affair stored without its id and its parliament is given both at the start, once")
        store.put_fields(paper, report)
        store.put_affair(key, held["record"], held["documents"])
        status, listed = call(base, "/api/records")
        mine = next((r for r in listed["data"] if r.get("id") == key), None)
        no_blocks = all("body" not in d for r in listed["data"] for d in (r.get("docs") or {}).get("data") or [])
        check(status == 200 and listed["meta"]["count"] == len(listed["data"]) == len(affairs) and mine is not None
              and no_blocks and {k: v for k, v in mine.items() if k != "docs"} == {
                  k: v for k, v in alone.items() if k != "docs"},
              f"the list a visitor reads is the affairs in the affair schema, without blocks: {len(listed['data'])}")
        status, nothing = call(base, "/api/records?q=zzzqqqxxx")
        check(status == 200 and nothing["data"] == [] and nothing["meta"]["total"] == len(affairs),
              "its search finds nothing where nothing fits")
        for name in ("contributors", "groups", "meetings", "events"):
            status, rows = call(base, "/api/" + name)
            known = {r.get("id") for r in listed["data"]}
            check(status == 200 and rows["meta"]["count"] == len(rows["data"])
                  and all(r.get("affair_id") in known for r in rows["data"]),
                  f"the table of {name} follows from the affairs: {len(rows['data'])} rows, each with its affair")
        # one person, one group, one meeting: the rows that hold exactly the name, whatever signs it has
        for name, column in (("contributors", "fullname"), ("groups", "name"), ("meetings", "conf-name")):
            _, rows = call(base, "/api/" + name)
            names = sorted({str(r[column]) for r in rows["data"] if r.get(column)}, key=lambda n: ("(" not in n, n))
            if not names:
                continue
            status, mine = call(base, f"/api/{name}?{urllib.parse.quote(column)}={urllib.parse.quote(names[0])}")
            want = [r for r in rows["data"] if r.get(column) == names[0]]
            check(status == 200 and mine["data"] == want and mine["meta"] == {"total": len(rows["data"]),
                                                                              "count": len(want)},
                  f"the table of {name} asked for one name gives its rows alone: {len(want)} of {len(rows['data'])}")
        first = affair["sources"][0]
        name = affair["documents"][0]["name"]
        status, image = call(base, f"/api/documents/{name}/pages/1.png")
        check(status == 200 and image[:8] == b"\x89PNG\r\n\x1a\n", f"page image of {name} served")
        status, _ = call(base, f"/api/documents/{name}/pages/99.png")
        check(status == 404, "a page that is not there is 404")
        status, shown = call(base, f"/api/documents/{name}/blocks")
        in_record = next(d for d in affair["record"]["docs"]["data"] if d["id"] == affair["documents"][0]["id"])
        count = len(in_record["body"]) + sum(len(r["body"]) for r in in_record.get("response") or [])
        check(status == 200 and len(shown["blocks"]) == count and shown["language"] == in_record.get("language", ""),
              f"the blocks of {name} are served on their own: {count}, language {shown['language'] or 'none'}")
        status, _ = call(base, "/api/documents/none/blocks")
        check(status == 404, "the blocks of a document that is not there are 404")
        status, entry = call(base, f"/api/documents/{name}/record")
        check(status == 200 and entry == in_record, "the document alone is served in the affair schema: its entry")
        status, _ = call(base, "/api/documents/none/record")
        check(status == 404, "a document no affair holds is 404")
        status, _ = call(base, "/api/affairs/no-such-key")
        check(status == 404, "an unknown affair is 404")

        status, before_rows = call(base, f"/api/affairs/{key}/decisions")
        status, answer = call(base, f"/api/affairs/{key}/decisions", {"source": first["source"], "decision": "maybe"})
        check(status == 400, f"a decision outside the three is refused: {answer.get('error')}")
        status, answer = call(base, f"/api/affairs/{key}/decisions",
                              {"source": first["source"], "decision": "confirmed", "by": "test"})
        check(status == 200, "confirming a value answers 200")
        done = next(e for e in answer["sources"] if e["source"] == first["source"])
        review = done["review"] or {}
        check(review.get("decision") == "confirmed" and review.get("by") == "test", "the review is at the source")
        check(app.contract.check(answer["record"]) == [], "the record is still valid")
        changed_to = str(first["value"]) + " (changed)"
        status, answer = call(base, f"/api/affairs/{key}/decisions",
                              {"source": first["source"], "decision": "changed", "by": "test", "after": changed_to})
        done = next(e for e in answer["sources"] if e["source"] == first["source"])
        check(status == 200 and done["value"] == changed_to and done["review"]["before"] == str(first["value"]),
              "a change sets the new value and keeps the old one in before")
        status, rows = call(base, f"/api/affairs/{key}/decisions")
        new_rows = len(rows) - len(before_rows)
        check(status == 200 and new_rows == 2 and rows[-1]["decision"] == "changed", f"{new_rows} decisions logged")

        # with an account, a decision is by the account, whoever the request names, and needs its session
        open_config = app.config
        app.config = type(open_config)(**{**open_config.__dict__, "admin_password": "secret"})
        try:
            # on another value than the one changed above, whose review the checks below still read
            other = next(e for e in affair["sources"] if e["source"] != first["source"])
            body = {"source": other["source"], "decision": "confirmed", "by": "visitor"}
            status, _ = call(base, f"/api/affairs/{key}/decisions", body)
            login = urllib.request.Request(base + "/api/login", method="POST",
                                           data=json.dumps({"user": "admin", "password": "secret"}).encode("utf-8"))
            with urllib.request.urlopen(login, timeout=10) as r:
                session = (r.headers.get("Set-Cookie") or "").split(";")[0]
                guarded = "HttpOnly" in (r.headers.get("Set-Cookie") or "")
            status2, answer = call(base, f"/api/affairs/{key}/decisions", body, session)
            done = next(e for e in answer["sources"] if e["source"] == other["source"])
            _, rows = call(base, f"/api/affairs/{key}/decisions", None, session)
            check(status == 401 and status2 == 200 and guarded and done["review"]["by"] == "admin"
                  and rows[-1]["by"] == "admin",
                  "with an account a decision needs its session and is by the account, whoever the request names")
        finally:
            app.config = open_config

        # a new run over the same documents: the review is carried over
        stored = store.get_affair(key)
        fresh = copy.deepcopy(stored["record"])
        for e in sources_of(fresh):
            source = fresh
            for part in e["source"].split("."):
                source = source[int(part)] if isinstance(source, list) else source[part]
            source.pop("review", None)
        kept, count = carry_reviews(stored["record"], fresh)
        again = next(e for e in sources_of(kept) if e["source"] == first["source"])
        check(count >= 1 and again["review"]["decision"] == "changed" and again["value"] == changed_to,
              f"{count} review carried into a new run, with the changed value")
    finally:
        server.shutdown()
        app.jobs.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
