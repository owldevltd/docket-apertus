"""The administration over the API, without a model. Its account: with a password set, nothing of the
administration is read or changed without signing in, a wrong name or password is refused, the session rides
in a cookie the page cannot read, and signing out ends it; what a visitor reads stays open. (That a decision
is by the account is checked where a store has values to decide on, in tests/server.py.) Without a password the administration is open. Its runs: a shipped
one-page PDF is uploaded, the queue runs it through the chain, the run ends as done and its affair stands in
the store. The rules route answers.

    python3 tests/admin.py <file.pdf>
"""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract  # noqa: E402
from docket.server import serve  # noqa: E402
from docket.store.files import FileStore  # noqa: E402

WAIT = 180


def call(base: str, route: str, data: bytes | None = None, headers: dict | None = None) -> tuple[int, object]:
    request = urllib.request.Request(base + route, data=data, method="POST" if data is not None else "GET")
    for k, v in (headers or {}).items():
        request.add_header(k, v)
    try:
        with urllib.request.urlopen(request, timeout=30) as r:
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


def main(argv: list[str]) -> int:
    pdf = next((Path(a) for a in argv if a.endswith(".pdf")), None)
    if pdf is None or not pdf.is_file():
        print("usage: python3 tests/admin.py <file.pdf>")
        return 1
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    with tempfile.TemporaryDirectory() as tmp:
        base_config = load_config()
        config = type(base_config)(**{**base_config.__dict__, "storage_dir": Path(tmp), "admin_password": "secret"})
        store = FileStore(Path(tmp) / "store")
        app = App(store, load_contract(config), config, Jobs(config))
        server = serve(app, 0, host="127.0.0.1")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            status, health = call(base, "/api/health")
            check(status == 200 and health["admin"] == "account", "health: the administration has an account")
            status, who = call(base, "/api/session")
            check(status == 200 and who == {"account": True, "user": None}, "nobody is signed in at first")
            data = pdf.read_bytes()
            status, answer = call(base, "/api/runs", data, {"Content-Type": "application/pdf", "X-Name": pdf.name})
            check(status == 401, f"a run without the account is refused: {answer.get('error')}")
            closed = [call(base, route)[0] for route in ("/api/affairs", "/api/decisions", "/api/rules", "/api/runs",
                                                         "/api/vocabulary", "/api/definition", "/api/learnt",
                                                         "/api/register", "/api/documents/x/pages/1.png",
                                                         "/api/documents/x/blocks", "/api/documents/x/fields")]
            check(set(closed) == {401}, f"nothing of the administration is read without the account: {closed}")
            opened = [call(base, route)[0] for route in ("/api/records", "/api/contributors", "/api/groups",
                                                         "/api/meetings", "/api/events", "/api/parliaments")]
            check(set(opened) == {200}, f"what a visitor reads needs no account: {opened}")
            check(sign_in(base, "admin", "wrong") == "" and sign_in(base, "someone", "secret") == "",
                  "a wrong password and a wrong name are refused")
            session = sign_in(base)
            status, who = call(base, "/api/session", None, {"Cookie": session})
            check(session.startswith("docket=") and who == {"account": True, "user": "admin"},
                  "the account signs in, and the session knows who it is")
            headers = {"Content-Type": "application/pdf", "X-Name": pdf.name, "X-Model": "0", "Cookie": session}
            status, job = call(base, "/api/runs", data, {**headers, "X-Body": "NE"})
            queued = status == 202 and job["state"] in ("queued", "running") and job["body"] == "NE"
            check(queued, f"the upload is queued as run {job.get('id')}, with the parliament told for it")
            status, answer = call(base, "/api/runs", b"not a pdf", headers)
            check(status == 400, f"an upload that is no PDF is refused: {answer.get('error')}")
            status, answer = call(base, "/api/runs", json.dumps({"document": 1}).encode(), {"Cookie": session})
            check(status == 400, f"only a PDF comes in, nothing is fetched by an id: {answer.get('error')}")
            status, answer = call(base, "/api/runs", data, {**headers, "X-Body": "no-such"})
            check(status == 400, f"a parliament that is not known is refused: {answer.get('error')}")
            started = time.monotonic()
            while time.monotonic() - started < WAIT:
                status, job = call(base, f"/api/runs/{job['id']}", None, {"Cookie": session})
                if job["state"] in ("done", "failed"):
                    break
                time.sleep(2)
            check(job["state"] == "done", f"the run ended as {job['state']} after {time.monotonic() - started:.0f} s"
                  + (f": {job.get('error')}" if job.get("error") else ""))
            keys = [a["key"] for a in job.get("affairs", [])]
            check(len(keys) == 1, f"the run gave one affair: {keys}")
            status, affairs = call(base, "/api/runs", None, {"Cookie": session})
            check(status == 200 and affairs and affairs[0]["id"] == job["id"], "the run is listed first")
            if keys:
                status, affair = call(base, "/api/affairs/" + keys[0], None, {"Cookie": session})
                check(status == 200 and affair["documents"][0]["name"] == pdf.stem, "the affair is in the store")
                status, rows = call(base, "/api/affairs", None, {"Cookie": session})
                check(status == 200 and len(rows) == 1, "the list shows it")
                # deciding on a value is the administration's part: a visitor of the public pages cannot
                decision = json.dumps({"id": "none", "decision": "confirmed", "by": "visitor"}).encode()
                status, answer = call(base, f"/api/affairs/{keys[0]}/decisions", decision)
                check(status == 401, "a decision without the account is refused")
                status, answer = call(base, f"/api/affairs/{keys[0]}/decisions", decision, {"Cookie": session})
                check(status not in (401, 403), f"with the account the decision reaches the review ({status})")
                status, visitor = call(base, f"/api/records/{keys[0]}")
                check(status == 200 and visitor.get("id") == keys[0], "a visitor reads the affair without an account")
            status, rules = call(base, "/api/rules", None, {"Cookie": session})
            check(status == 200 and rules == [], "no rules yet")
            body = json.dumps({"active": False}).encode()
            status, answer = call(base, "/api/rules/r-0001", body, {"Cookie": session})
            check(status == 404, "switching a rule that is not there is 404")
            status, who = call(base, "/api/logout", b"{}", {"Cookie": session})
            status, answer = call(base, "/api/affairs", None, {"Cookie": session})
            check(who == {"account": True, "user": None} and status == 401, "signing out ends the session")
            # without a password the administration is open, and acts under the name of the account
            app.config = type(config)(**{**config.__dict__, "admin_password": ""})
            status, who = call(base, "/api/session")
            status2, rows = call(base, "/api/affairs")
            check(who == {"account": False, "user": "admin"} and status2 == 200,
                  "without a password the administration is open")
        finally:
            server.shutdown()
            app.jobs.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
