"""The web server: the app as static files, the API under /api/. The standard library's HTTP server with a
small router; one process, one store, one lock per affair for decisions.

    GET  /api/health                              the store in use
    GET  /api/affairs                             every affair: key, number, title, type, counts
    GET  /api/affairs/<key>                       the record, its documents and every value with a place
    GET  /api/affairs/<key>/decisions             the decisions taken on it
    POST /api/affairs/<key>/decisions             {source, decision, by, after?, path?} -> the affair as above
    GET  /api/documents/<name>/fields             the fields report of a document (the model's answers)
    GET  /api/documents/<name>/pages/<n>          the page's elements
    GET  /api/documents/<name>/pages/<n>.png      the page image
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from docket.affair.validator import Contract
from docket.store.base import Store
from docket.store.review import apply_decision, counts, sources_of

APP = Path(__file__).resolve().parent / "app"
BODY_LIMIT = 32 * 1024 * 1024
TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
    ".woff2": "font/woff2",
}


class App:
    """What the handlers share: the store, the contract, the locks."""

    def __init__(self, store: Store, contract: Contract):
        self.store = store
        self.contract = contract
        self.locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    def lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self.locks.setdefault(key, threading.Lock())

    def affair(self, key: str) -> dict | None:
        data = self.store.get_affair(key)
        if data is None:
            return None
        record = data["record"]
        return {
            "key": key,
            "record": record,
            "documents": data.get("documents", []),
            "sources": sources_of(record),
            "counts": counts(record),
            "updated_at": data.get("updated_at"),
        }

    def summaries(self) -> list[dict]:
        out = []
        for a in self.store.list_affairs():
            r = a["record"]
            out.append({
                "key": a["key"],
                "number": r.get("number"),
                "title": (r.get("title") or {}).get("de"),
                "type": (r.get("type_harmonized") or {}).get("de") or (r.get("type_name") or {}).get("de"),
                "documents": [d.get("name") for d in a.get("documents", [])],
                "counts": counts(r),
                "updated_at": a.get("updated_at"),
            })
        return sorted(out, key=lambda s: (-s["counts"]["open"], s["key"]))

    def decide(self, key: str, body: dict) -> tuple[int, dict]:
        with self.lock(key):
            data = self.store.get_affair(key)
            if data is None:
                return 404, {"error": "no such affair"}
            try:
                record = apply_decision(
                    data["record"], str(body.get("source", "")), str(body.get("decision", "")),
                    str(body.get("by", "")), body.get("after"), body.get("path"), body.get("rule"),
                )
            except ValueError as e:
                return 400, {"error": str(e)}
            errors = self.contract.check(record)
            if errors:
                return 409, {"error": "the record would not fit the contract", "violations": errors[:5]}
            self.store.save_record(key, record)
            entry = next(e for e in sources_of(record) if e["source"] == body.get("source"))
            self.store.add_decision({
                "affair": key, "doc": entry["doc"], "block": entry["block"], "path": entry["path"],
                "label": entry["label"], "how": entry["how"], "approve": entry["approve"],
                "decision": entry["review"]["decision"], "before": entry["review"].get("before"),
                "after": entry["value"], "by": entry["review"].get("by"), "at": entry["review"]["at"],
                "rule": entry["review"].get("rule"),
            })
        return 200, self.affair(key) or {}


class Handler(BaseHTTPRequestHandler):
    server_version = "docket"

    def log_message(self, fmt, *args) -> None:  # quiet
        pass

    def do_GET(self) -> None:
        self._handle("GET")

    def do_POST(self) -> None:
        self._handle("POST")

    def _handle(self, method: str) -> None:
        app: App = self.server.app  # type: ignore[attr-defined]
        path = unquote(urlsplit(self.path).path)
        try:
            if path.startswith("/api/"):
                status, payload = self._api(app, method, path[5:])
                self._json(status, payload)
            elif method == "GET":
                self._static(path)
            else:
                self._json(405, {"error": "method not allowed"})
        except Exception as e:  # noqa: BLE001 - the server must answer
            self._json(500, {"error": str(e)})

    def _api(self, app: App, method: str, route: str) -> tuple[int, object]:
        if route == "health" and method == "GET":
            return 200, {"ok": True, "store": app.store.kind}
        if route == "affairs" and method == "GET":
            return 200, app.summaries()
        m = re.fullmatch(r"affairs/([^/]+)", route)
        if m and method == "GET":
            affair = app.affair(m.group(1))
            return (200, affair) if affair else (404, {"error": "no such affair"})
        m = re.fullmatch(r"affairs/([^/]+)/decisions", route)
        if m and method == "GET":
            return 200, app.store.list_decisions(m.group(1))
        if m and method == "POST":
            body = self._body()
            if not isinstance(body, dict):
                return 400, {"error": "a JSON object is expected"}
            return app.decide(m.group(1), body)
        m = re.fullmatch(r"documents/([^/]+)/fields", route)
        if m and method == "GET":
            report = app.store.get_fields(m.group(1))
            return (200, report) if report is not None else (404, {"error": "no such document"})
        m = re.fullmatch(r"documents/([^/]+)/pages/(\d+)(\.png)?", route)
        if m and method == "GET":
            name, n = m.group(1), int(m.group(2))
            if m.group(3):
                image = app.store.page_path(name, n)
                if image is None:
                    return 404, {"error": "no such page"}
                self._file(image, "image/png")
                return 0, None
            page = app.store.page_data(name, n)
            return (200, page) if page is not None else (404, {"error": "no such page"})
        return 404, {"error": "no such route"}

    def _body(self) -> object:
        length = int(self.headers.get("Content-Length") or 0)
        if length > BODY_LIMIT:
            return None
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _json(self, status: int, payload: object) -> None:
        if status == 0:
            return
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str) -> None:
        name = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (APP / name).resolve()
        if not str(target).startswith(str(APP)) or not target.is_file():
            # the app routes its own screens; any unknown path shows the app
            target = APP / "index.html"
        self._file(target, TYPES.get(target.suffix, "application/octet-stream"))

    def _file(self, target: Path, kind: str) -> None:
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)


def serve(app: App, port: int, host: str = "0.0.0.0") -> ThreadingHTTPServer:
    """Binds the server; the caller runs serve_forever or uses it in a thread (tests)."""
    server = ThreadingHTTPServer((host, port), Handler)
    server.app = app  # type: ignore[attr-defined]
    return server
