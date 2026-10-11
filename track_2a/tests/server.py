"""The web server over a file store, without a model: the routes answer, a decision lands at the source and
keeps the record valid, a wrong decision is refused, and a new run over the same document keeps the review.

    python3 tests/server.py --store=<file store dir> [--pages=<analyzed dir>]
"""

from __future__ import annotations

import copy
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.pipeline import load_contract  # noqa: E402
from docket.server import serve  # noqa: E402
from docket.store.files import FileStore  # noqa: E402
from docket.store.review import carry_reviews, sources_of  # noqa: E402


def call(base: str, route: str, body: dict | None = None) -> tuple[int, object]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(base + route, data=data, method="POST" if data else "GET")
    if data:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            raw = r.read()
            kind = r.headers.get("Content-Type", "")
            return r.status, json.loads(raw.decode("utf-8")) if kind.startswith("application/json") else raw
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


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
        status, affairs = call(base, "/api/affairs")
        check(status == 200 and isinstance(affairs, list) and len(affairs) > 0, f"{len(affairs)} affairs listed")
        with_place = next((a for a in affairs if a["counts"]["places"] > 0), None)
        check(with_place is not None, "an affair with a value that has a place")
        if with_place is None:
            return 1
        key = with_place["key"]
        status, affair = call(base, f"/api/affairs/{key}")
        places = len(affair.get("sources") or [])
        check(status == 200 and affair["key"] == key and places > 0, f"affair {key}: {places} places")
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
