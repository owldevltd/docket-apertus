"""The web server: the app as static files, the API under /api/. The standard library's HTTP server with a
small router; what it answers with is in api.py.

    GET  /<language>/...                          the app in that language (de, fr, it, en: one build each, in
                                                  its own folder); an address without a language goes on to
                                                  the German one

    GET  /api/health                              the store, the model, the admin mode
    GET  /api/session                             whether the administration has an account, and who is signed in
    POST /api/login                               {user, password} signs in to the administration; the session
                                                  rides in a cookie the page cannot read
    POST /api/logout                              ends the session

  what a visitor reads, all of it in the affair schema (docket.public):
    GET  /api/records?q=&body_key=&type=&kind=&language=   the affairs that fit, {meta, data}, without blocks
    GET  /api/records/<id>                        one affair, whole
    GET  /api/contributors|groups|meetings|events the tables that follow from the affairs, same search; a name
                                                  of the table (fullname=, name=, conf-name=) asks for the rows
                                                  with exactly that value
    GET  /api/documents/<name>/record             a document alone: its entry in the record of its affair

  the administration and the review. With a password set (ADMIN_PASSWORD) every route below needs the
  session of the account, reading as well; without one the administration is open. Who decided is the name
  of the account:
    GET  /api/affairs?q=&body=&type=&kind=&language=  every affair that fits: key, number, title, date, type,
                                                  parliament, documents, counts
    GET  /api/affairs/<key>                       the record, its documents and every value with a place
    GET  /api/affairs/<key>/decisions             the decisions taken on it
    POST /api/affairs/<key>/decisions             {id, decision, after?} -> the affair as above,
                                                  with the rules the decision leaves proposed (proposals)
    GET  /api/decisions                           every decision in the store
    GET  /api/documents/<name>/fields             the fields report of a document (the model's answers)
    GET  /api/documents/<name>/blocks             its blocks in reading order, its language, the answers in it
    GET  /api/documents/<name>/pages/<n>          the page's elements
    GET  /api/documents/<name>/pages/<n>.png      the page image
    GET  /api/rules                               the rules learnt from decisions; a proposed one with its reach
    POST /api/rules/<id>/answer                   {accept} a person's yes or no to a proposed rule
    POST /api/rules/<id>                          {active} switches a rule
    GET  /api/definition                          the fields with their entity, and in how many documents each
                                                  was asked and never asked
    POST /api/definition/ask                      {field} queues a run that asks the stored documents a field
                                                  they were never asked; without a field, all such
    GET  /api/learnt                              what the second opinion learnt, way by way, with how often
                                                  each agreed on documents held back and whether it is used
    GET  /api/vocabulary?list=&body=              the names of the parliaments with their standard names
    POST /api/vocabulary                          {list, body, name, standard} sets what a name stands
                                                  for, {list, body, name, reset} takes that back; {list,
                                                  standard: {de, fr, it, en}} adds a standard name
    GET  /api/parliaments                         the parliaments by their key, with their names
    GET  /api/register?body=                      the persons of a parliament; without one, what was learnt
    POST /api/register                            {body, key} takes a learnt person or a candidate out
    GET  /api/runs                                the runs of the admin, newest first
    GET  /api/runs/<id>                           one run with all its lines
    POST /api/runs                                a PDF (Content-Type application/pdf, X-Name; X-Model 1 or 0;
                                                  X-Body the key of its parliament, where known)
"""

from __future__ import annotations

import json
import re
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from docket import public
from docket.api import App
from docket.config import Config
from docket.pipeline import load_contract
from docket.store import open_store

APP = Path(__file__).resolve().parent / "app"
# the language the app is written in: where an address without a language goes
HOME = "de"
# what a visitor reads, and the door to the administration: open to everyone. Everything else under /api/
# belongs to the administration and needs its account, where it has a password
OPEN = re.compile(r"health|session|parliaments|records(/[^/]+)?|documents/[^/]+/record|" + "|".join(public.TABLES))
# the cookie a session of the administration rides in
COOKIE = "docket"
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
        self.cookie = ""
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
        session = self._session()
        who = app.account(session)
        if route == "session" and method == "GET":
            return 200, {"account": bool(app.config.admin_password), "user": who}
        if route == "login" and method == "POST":
            body = self._json_body()
            body = body if isinstance(body, dict) else {}
            session = app.sign_in(str(body.get("user", "")), str(body.get("password", "")))
            if session is None:
                # a wrong guess costs a second, so trying many takes long
                time.sleep(1)
                return 401, {"error": "the name or the password is wrong"}
            self.cookie = f"{COOKIE}={session}; Path=/api; HttpOnly; SameSite=Strict; Max-Age=43200"
            return 200, {"account": True, "user": app.account(session)}
        if route == "logout" and method == "POST":
            app.sign_out(session)
            self.cookie = f"{COOKIE}=; Path=/api; HttpOnly; SameSite=Strict; Max-Age=0"
            return 200, {"account": bool(app.config.admin_password), "user": app.account(None)}
        if who is None and not (method == "GET" and OPEN.fullmatch(route)):
            return 401, {"error": "sign in to the administration"}
        if route == "affairs" and method == "GET":
            asked = parse_qs(urlsplit(self.path).query)
            return 200, app.summaries({k: v[0] for k, v in asked.items()})
        if route == "decisions" and method == "GET":
            return 200, app.store.list_decisions()
        m = re.fullmatch(r"affairs/([^/]+)", route)
        if m and method == "GET":
            affair = app.affair(m.group(1))
            return (200, affair) if affair else (404, {"error": "no such affair"})
        if method == "GET" and (route == "records" or route in public.TABLES):
            asked = {k: v[0] for k, v in parse_qs(urlsplit(self.path).query).items()}
            return 200, app.records(asked) if route == "records" else app.table(route, asked)
        m = re.fullmatch(r"records/([^/]+)", route)
        if m and method == "GET":
            record = app.record(m.group(1))
            return (200, record) if record is not None else (404, {"error": "no such affair"})
        m = re.fullmatch(r"affairs/([^/]+)/decisions", route)
        if m and method == "GET":
            return 200, app.store.list_decisions(m.group(1))
        if m and method == "POST":
            body = self._json_body()
            if not isinstance(body, dict):
                return 400, {"error": "a JSON object is expected"}
            return app.decide(m.group(1), {**body, "by": self._by(app, who, body)})
        m = re.fullmatch(r"documents/([^/]+)/fields", route)
        if m and method == "GET":
            report = app.store.get_fields(m.group(1))
            return (200, report) if report is not None else (404, {"error": "no such document"})
        m = re.fullmatch(r"documents/([^/]+)/record", route)
        if m and method == "GET":
            entry = app.document_record(m.group(1))
            return (200, entry) if entry is not None else (404, {"error": "no such document"})
        m = re.fullmatch(r"documents/([^/]+)/blocks", route)
        if m and method == "GET":
            document = app.document(m.group(1))
            return (200, document) if document is not None else (404, {"error": "no such document"})
        m = re.fullmatch(r"documents/([^/]+)/pages/(\d+)(\.png)?", route)
        if m and method == "GET":
            return self._page(app, m.group(1), int(m.group(2)), bool(m.group(3)))
        if route == "rules" and method == "GET":
            return 200, app.rules()
        m = re.fullmatch(r"rules/([^/]+)/answer", route)
        if m and method == "POST":
            body = self._json_body()
            if not isinstance(body, dict) or not isinstance(body.get("accept"), bool):
                return 400, {"error": "a JSON object with accept (true or false) is expected"}
            return app.answer_rule(m.group(1), body["accept"], self._by(app, who, body))
        m = re.fullmatch(r"rules/([^/]+)", route)
        if m and method == "POST":
            body = self._json_body()
            if not isinstance(body, dict):
                return 400, {"error": "a JSON object is expected"}
            return app.switch_rule(m.group(1), bool(body.get("active")), self._by(app, who, body))
        if route == "definition" and method == "GET":
            return 200, app.definition()
        if route == "learnt" and method == "GET":
            return 200, app.learnt()
        if route == "definition/ask" and method == "POST":
            body = self._json_body()
            return app.ask_again(body.get("field") if isinstance(body, dict) else None)
        if route == "vocabulary" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            return 200, app.vocabulary(query.get("list", [None])[0], query.get("body", [None])[0])
        if route == "parliaments" and method == "GET":
            return 200, app.parliaments()
        if route == "vocabulary" and method == "POST":
            body = self._json_body()
            if not isinstance(body, dict):
                return 400, {"error": "a JSON object is expected"}
            return app.set_name({**body, "by": self._by(app, who, body)})
        if route == "register" and method == "GET":
            query = parse_qs(urlsplit(self.path).query)
            return 200, app.register(query.get("body", [None])[0])
        if route == "register" and method == "POST":
            body = self._json_body()
            if not isinstance(body, dict):
                return 400, {"error": "a JSON object is expected"}
            return app.forget(body)
        if route == "runs" and method == "GET":
            return 200, app.jobs.list()
        m = re.fullmatch(r"runs/([^/]+)", route)
        if m and method == "GET":
            job = app.jobs.get(m.group(1))
            return (200, job) if job else (404, {"error": "no such run"})
        if route == "runs" and method == "POST":
            return self._run(app)
        return 404, {"error": "no such route"}

    def _session(self) -> str | None:
        """The session a request carries in its cookie, if any."""
        held = SimpleCookie(self.headers.get("Cookie") or "").get(COOKIE)
        return held.value if held is not None and held.value else None

    @staticmethod
    def _by(app: App, who: str | None, body: dict) -> str:
        """Who a decision is by: the account that is signed in. Where the administration is open, a caller
        may still name the person, as before there was an account."""
        if app.config.admin_password:
            return str(who or "")
        return str(body.get("by") or who or "")

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
        kind = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        raw = self._raw_body()
        if raw is None:
            return 413, {"error": "the body is too large"}
        if kind != "application/pdf":
            return 400, {"error": "a PDF is expected"}
        model = self.headers.get("X-Model")
        return app.run_pdf(self.headers.get("X-Name") or "upload.pdf", raw, None if model is None else model == "1",
                           (self.headers.get("X-Body") or "").strip())

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
        if getattr(self, "cookie", ""):
            self.send_header("Set-Cookie", self.cookie)
        self.end_headers()
        self.wfile.write(data)

    def _static(self, path: str) -> None:
        """The files of the app. It is built once per language, each build in a folder of its own that is the
        first part of its addresses; a folder with a page in it is a language."""
        first, _, rest = path.lstrip("/").partition("/")
        home = APP / first
        if not first or not (home / "index.html").is_file():
            if (APP / HOME / "index.html").is_file():
                # an address without a language, as it was before the app had several: on to the first one
                self._moved("/" + HOME + self.path)
            else:
                self._notice()
            return
        target = (home / rest).resolve()
        if home not in target.parents or not target.is_file():
            # the app routes its own screens; any unknown path shows the app
            target = home / "index.html"
        self._file(target, TYPES.get(target.suffix, "application/octet-stream"))

    def _moved(self, address: str) -> None:
        self.send_response(302)
        self.send_header("Location", address)
        self.send_header("Content-Length", "0")
        self.end_headers()

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
