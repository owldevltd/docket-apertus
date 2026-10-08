"""The admin's runs over the API, without a model: a shipped one-page PDF is uploaded, the queue runs it
through the chain, the run ends as done and its affair stands in the store; the admin token is checked when
set; the rules route answers.

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
        config = type(base_config)(**{**base_config.__dict__, "storage_dir": Path(tmp), "admin_token": "secret"})
        store = FileStore(Path(tmp) / "store")
        app = App(store, load_contract(config), config, Jobs(config))
        server = serve(app, 0, host="127.0.0.1")
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            status, health = call(base, "/api/health")
            check(status == 200 and health["admin"] == "token", f"health: admin by token")
            data = pdf.read_bytes()
            status, answer = call(base, "/api/runs", data, {"Content-Type": "application/pdf", "X-Name": pdf.name})
            check(status == 403, f"a run without the token is refused: {answer.get('error')}")
            headers = {"Content-Type": "application/pdf", "X-Name": pdf.name, "X-Model": "0", "X-Token": "secret"}
            status, job = call(base, "/api/runs", data, headers)
            queued = status == 202 and job["state"] in ("queued", "running")
            check(queued, f"the upload is queued as run {job.get('id')}")
            status, answer = call(base, "/api/runs", b"not a pdf", headers)
            check(status == 400, f"an upload that is no PDF is refused: {answer.get('error')}")
            status, answer = call(base, "/api/runs", json.dumps({"document": "x"}).encode(), {"X-Token": "secret"})
            check(status == 400, f"a document id that is no number is refused: {answer.get('error')}")
            started = time.monotonic()
            while time.monotonic() - started < WAIT:
                status, job = call(base, f"/api/runs/{job['id']}")
                if job["state"] in ("done", "failed"):
                    break
                time.sleep(2)
            check(job["state"] == "done", f"the run ended as {job['state']} after {time.monotonic() - started:.0f} s"
                  + (f": {job.get('error')}" if job.get("error") else ""))
            keys = [a["key"] for a in job.get("affairs", [])]
            check(len(keys) == 1, f"the run gave one affair: {keys}")
            status, affairs = call(base, "/api/runs")
            check(status == 200 and affairs and affairs[0]["id"] == job["id"], "the run is listed first")
            if keys:
                status, affair = call(base, "/api/affairs/" + keys[0])
                check(status == 200 and affair["documents"][0]["name"] == pdf.stem, "the affair is in the store")
                status, rows = call(base, "/api/affairs")
                check(status == 200 and len(rows) == 1, "the list shows it")
            status, rules = call(base, "/api/rules")
            check(status == 200 and rules == [], "no rules yet")
            body = json.dumps({"active": False}).encode()
            status, answer = call(base, "/api/rules/r-0001", body, {"X-Token": "secret"})
            check(status == 404, "switching a rule that is not there is 404")
        finally:
            server.shutdown()
            app.jobs.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
