"""The web server: the app as static files, the API under /api/. The standard library's HTTP server with a
small router; what it answers with is in api.py.

    GET  /api/health                              the store, the model, the admin mode
    GET  /api/affairs                             every affair: key, number, title, type, counts
    GET  /api/affairs/<key>                       the record, its documents and every value with a place
    GET  /api/affairs/<key>/decisions             the decisions taken on it
    POST /api/affairs/<key>/decisions             {source, decision, by, after?, path?} -> the affair as above
    GET  /api/decisions                           every decision in the store
    GET  /api/documents/<name>/fields             the fields report of a document (the model's answers)
    GET  /api/documents/<name>/pages/<n>          the page's elements
    GET  /api/documents/<name>/pages/<n>.png      the page image
    GET  /api/rules                               the rules of the general repair
    POST /api/rules/<id>                          {active, by} switches a rule (admin)
    GET  /api/runs                                the runs of the admin, newest first
    GET  /api/runs/<id>                           one run with all its lines
    POST /api/runs                                a PDF (Content-Type application/pdf, X-Name) or
                                                  {document: <OpenParlData doc id>}, {model?} (admin)
"""

from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from docket.api import App
from docket.config import Config
from docket.pipeline import load_contract
from docket.store import open_store

APP = Path(__file__).resolve().parent / "app"
BODY_LIMIT = 64 * 1024 * 1024
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
            return 200, app.health()
        if route == "affairs" and method == "GET":
            return 200, app.summaries()
        if route == "decisions" and method == "GET":
            return 200, app.store.list_decisions()
        m = re.fullmatch(r"affairs/([^/]+)", route)
        if m and method == "GET":
            affair = app.affair(m.group(1))
            return (200, affair) if affair else (404, {"error": "no such affair"})
        m = re.fullmatch(r"affairs/([^/]+)/decisions", route)
        if m and method == "GET":
            return 200, app.store.list_decisions(m.group(1))
        if m and method == "POST":
            body = self._json_body()
            if not isinstance(body, dict):
                return 400, {"error": "a JSON object is expected"}
            return app.decide(m.group(1), body)
        m = re.fullmatch(r"documents/([^/]+)/fields", route)
        if m and method == "GET":
            report = app.store.get_fields(m.group(1))
            return (200, report) if report is not None else (404, {"error": "no such document"})
        m = re.fullmatch(r"documents/([^/]+)/pages/(\d+)(\.png)?", route)
        if m and method == "GET":
            return self._page(app, m.group(1), int(m.group(2)), bool(m.group(3)))
        if route == "rules" and method == "GET":
            return 200, app.rules()
        m = re.fullmatch(r"rules/([^/]+)", route)
        if m and method == "POST":
            if not app.allowed(self.headers.get("X-Token")):
                return 403, {"error": "the admin token is missing or wrong"}
            body = self._json_body()
            if not isinstance(body, dict):
                return 400, {"error": "a JSON object is expected"}
            return app.switch_rule(m.group(1), bool(body.get("active")), str(body.get("by", "")))
        if route == "runs" and method == "GET":
            return 200, app.jobs.list()
        m = re.fullmatch(r"runs/([^/]+)", route)
        if m and method == "GET":
            job = app.jobs.get(m.group(1))
            return (200, job) if job else (404, {"error": "no such run"})
        if route == "runs" and method == "POST":
            return self._run(app)
        return 404, {"error": "no such route"}

    def _page(self, app: App, name: str, n: int, image: bool) -> tuple[int, object]:
        if image:
            path = app.store.page_path(name, n)
            if path is None:
                return 404, {"error": "no such page"}
            self._file(path, "image/png")
            return 0, None
        page = app.store.page_data(name, n)
        return (200, page) if page is not None else (404, {"error": "no such page"})

    def _run(self, app: App) -> tuple[int, object]:
        if not app.allowed(self.headers.get("X-Token")):
            return 403, {"error": "the admin token is missing or wrong"}
        kind = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        raw = self._raw_body()
        if raw is None:
            return 413, {"error": "the body is too large"}
        if kind == "application/pdf":
            model = self.headers.get("X-Model")
            return app.run_pdf(self.headers.get("X-Name") or "upload.pdf", raw, None if model is None else model == "1")
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            return 400, {"error": "a JSON object or a PDF is expected"}
        if not isinstance(body, dict) or "document" not in body:
            return 400, {"error": "a JSON object with document, or a PDF, is expected"}
        try:
            doc_id = int(body["document"])
        except (TypeError, ValueError):
            return 400, {"error": "document must be the id of a document at OpenParlData"}
        return app.run_document(doc_id, body.get("model"))

    def _raw_body(self) -> bytes | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length > BODY_LIMIT:
            return None
        return self.rfile.read(length) if length else b""

    def _json_body(self) -> object:
        raw = self._raw_body()
        if raw is None:
            return None
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
        if not target.is_file():
            self._notice()
            return
        self._file(target, TYPES.get(target.suffix, "application/octet-stream"))

    def _notice(self) -> None:
        """Without a built app the API still answers; the page says how to build the app."""
        text = (
            "<!doctype html><meta charset=utf-8><title>Docket</title>"
            "<p>The API answers under /api/. The browser app is not built: run <code>make app</code> "
            "(needs Node for the build only), or start the container, which builds it.</p>"
        )
        data = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

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


def start(config: Config, port: int | None = None, host: str = "0.0.0.0") -> tuple[ThreadingHTTPServer, App]:
    """The app over the configured store, bound to the port."""
    app = App(open_store(config), load_contract(config), config)
    return serve(app, port if port is not None else config.port, host), app
