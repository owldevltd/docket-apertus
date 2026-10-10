"""The store in Postgres: the records as JSONB, the rows of the documents with entity, field and value as columns
to ask by, the decisions, the vocabulary and the register as rows. The tables are created on first use. Page
images stay on disk under the store's folder (a volume in Docker), the database holds what is queried."""

from __future__ import annotations

import json
from pathlib import Path

from docket.store.base import Store, now

TABLES = """
CREATE TABLE IF NOT EXISTS affairs (
    key text PRIMARY KEY,
    record jsonb NOT NULL,
    documents jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS documents (
    name text PRIMARY KEY,
    fields jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS rows (
    doc text NOT NULL,
    n integer NOT NULL,
    affair text NOT NULL,
    entity text NOT NULL,
    field text NOT NULL,
    value text NOT NULL,
    row jsonb NOT NULL,
    PRIMARY KEY (doc, n)
);
CREATE INDEX IF NOT EXISTS rows_entity_value ON rows (entity, value);
CREATE INDEX IF NOT EXISTS rows_field_value ON rows (field, value);
CREATE INDEX IF NOT EXISTS rows_affair ON rows (affair);
CREATE TABLE IF NOT EXISTS learnt (
    name text PRIMARY KEY,
    data jsonb NOT NULL,
    at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS decisions (
    id bigserial PRIMARY KEY,
    affair text NOT NULL,
    row jsonb NOT NULL,
    at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS decisions_affair ON decisions (affair);
CREATE TABLE IF NOT EXISTS rules (
    id text PRIMARY KEY,
    row jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS vocabulary (
    list text NOT NULL,
    body text NOT NULL,
    name text NOT NULL,
    row jsonb NOT NULL,
    PRIMARY KEY (list, body, name)
);
CREATE TABLE IF NOT EXISTS register (
    body text NOT NULL,
    key text NOT NULL,
    row jsonb NOT NULL,
    PRIMARY KEY (body, key)
);
"""


class PostgresStore(Store):
    kind = "postgres"

    def __init__(self, url: str, folder: Path):
        super().__init__(folder)
        import psycopg

        self._psycopg = psycopg
        self.url = url
        (folder / "pages").mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute(TABLES)

    def _connect(self):
        return self._psycopg.connect(self.url)

    def put_affair(self, key: str, record: dict, documents: list[dict]) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO affairs (key, record, documents, updated_at) VALUES (%s, %s::jsonb, %s::jsonb, now()) "
                "ON CONFLICT (key) DO UPDATE SET record = EXCLUDED.record, documents = EXCLUDED.documents, "
                "updated_at = now()",
                (key, json.dumps(record, ensure_ascii=False), json.dumps(documents, ensure_ascii=False)),
            )

    def get_affair(self, key: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT key, record, documents, updated_at FROM affairs WHERE key = %s", (key,)).fetchone()
        return self._affair(row) if row else None

    def save_record(self, key: str, record: dict) -> None:
        with self._connect() as db:
            done = db.execute(
                "UPDATE affairs SET record = %s::jsonb, updated_at = now() WHERE key = %s",
                (json.dumps(record, ensure_ascii=False), key),
            )
            if done.rowcount == 0:
                raise KeyError(key)

    def list_affairs(self) -> list[dict]:
        with self._connect() as db:
            query = "SELECT key, record, documents, updated_at FROM affairs ORDER BY updated_at DESC"
            rows = db.execute(query).fetchall()
        return [self._affair(r) for r in rows]

    def put_fields(self, name: str, report: dict) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO documents (name, fields, updated_at) VALUES (%s, %s::jsonb, now()) "
                "ON CONFLICT (name) DO UPDATE SET fields = EXCLUDED.fields, updated_at = now()",
                (name, json.dumps(report, ensure_ascii=False)),
            )

    def get_fields(self, name: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT fields FROM documents WHERE name = %s", (name,)).fetchone()
        return row[0] if row else None

    def asked_counts(self) -> dict:
        with self._connect() as db:
            documents = db.execute("SELECT count(*) FROM documents").fetchone()[0]
            names = db.execute(
                "SELECT asked, count(*) FROM documents, "
                "jsonb_object_keys(coalesce(fields->'fields', '{}'::jsonb)) AS asked GROUP BY asked"
            ).fetchall()
            marks = db.execute(
                "SELECT coalesce(fields->'definition'->>'version', ''), count(*) FROM documents GROUP BY 1"
            ).fetchall()
        return {"documents": documents, "fields": dict(names), "versions": dict(marks)}

    def put_rows(self, doc: str, rows: list[dict]) -> None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.execute("DELETE FROM rows WHERE doc = %s", (doc,))
            cursor.executemany(
                "INSERT INTO rows (doc, n, affair, entity, field, value, row) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)",
                [(doc, r["n"], r.get("affair") or "", r["entity"], r["field"], str(r["value"]),
                  json.dumps(r, ensure_ascii=False)) for r in rows],
            )

    def get_rows(self, doc: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT row FROM rows WHERE doc = %s ORDER BY n", (doc,)).fetchall()
        return [r[0] for r in rows]

    def find_rows(self, entity: str | None = None, field: str | None = None, value: str | None = None) -> list[dict]:
        given = [(k, v) for k, v in (("entity", entity), ("field", field), ("value", value)) if v is not None]
        where = " WHERE " + " AND ".join(f"{k} = %s" for k, _ in given) if given else ""
        with self._connect() as db:
            rows = db.execute(f"SELECT row FROM rows{where} ORDER BY doc, n", [v for _, v in given]).fetchall()
        return [r[0] for r in rows]

    def affairs_without_rows(self) -> list[str]:
        with self._connect() as db:
            query = "SELECT key FROM affairs WHERE NOT EXISTS (SELECT 1 FROM rows WHERE rows.affair = affairs.key)"
            rows = db.execute(query + " ORDER BY key").fetchall()
        return [r[0] for r in rows]

    def get_learnt(self) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT data FROM learnt WHERE name = 'second'").fetchone()
        return row[0] if row else None

    def put_learnt(self, data: dict) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO learnt (name, data, at) VALUES ('second', %s::jsonb, now()) "
                "ON CONFLICT (name) DO UPDATE SET data = EXCLUDED.data, at = now()",
                (json.dumps(data, ensure_ascii=False),),
            )

    def add_decision(self, row: dict) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO decisions (affair, row) VALUES (%s, %s::jsonb)",
                (row.get("affair", ""), json.dumps(row, ensure_ascii=False)),
            )

    def list_decisions(self, key: str | None = None) -> list[dict]:
        with self._connect() as db:
            if key is None:
                rows = db.execute("SELECT row FROM decisions ORDER BY id").fetchall()
            else:
                rows = db.execute("SELECT row FROM decisions WHERE affair = %s ORDER BY id", (key,)).fetchall()
        return [r[0] for r in rows]

    def get_rules(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT row FROM rules ORDER BY id").fetchall()
        return [r[0] for r in rows]

    def put_rules(self, rules: list[dict]) -> None:
        with self._connect() as db:
            for rule in rules:
                db.execute(
                    "INSERT INTO rules (id, row) VALUES (%s, %s::jsonb) "
                    "ON CONFLICT (id) DO UPDATE SET row = EXCLUDED.row",
                    (rule["id"], json.dumps(rule, ensure_ascii=False)),
                )

    def get_vocabulary(self) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT row FROM vocabulary ORDER BY list, body, name").fetchall()
        return [r[0] for r in rows]

    def put_vocabulary(self, rows: list[dict]) -> None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO vocabulary (list, body, name, row) VALUES (%s, %s, %s, %s::jsonb) "
                "ON CONFLICT (list, body, name) DO UPDATE SET row = EXCLUDED.row",
                [(r["list"], r["body"], r["name"], json.dumps(r, ensure_ascii=False)) for r in rows],
            )

    def drop_vocabulary(self, rows: list[dict]) -> None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.executemany(
                "DELETE FROM vocabulary WHERE list = %s AND body = %s AND name = %s",
                [(r["list"], r["body"], r["name"]) for r in rows],
            )

    def get_register(self, body: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("SELECT row FROM register WHERE body = %s ORDER BY key", (body,)).fetchall()
        return [r[0] for r in rows]

    def put_register(self, rows: list[dict]) -> None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO register (body, key, row) VALUES (%s, %s, %s::jsonb) "
                "ON CONFLICT (body, key) DO UPDATE SET row = EXCLUDED.row",
                [(r["body"], r["key"], json.dumps(r, ensure_ascii=False)) for r in rows],
            )

    def drop_register(self, rows: list[dict]) -> None:
        with self._connect() as db, db.cursor() as cursor:
            cursor.executemany(
                "DELETE FROM register WHERE body = %s AND key = %s", [(r["body"], r["key"]) for r in rows]
            )

    def register_bodies(self) -> list[str]:
        with self._connect() as db:
            rows = db.execute("SELECT DISTINCT body FROM register ORDER BY body").fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def _affair(row) -> dict:
        key, record, documents, updated_at = row
        stamp = updated_at.strftime("%Y-%m-%dT%H:%M:%S%z") if updated_at else now()
        return {"key": key, "record": record, "documents": documents, "updated_at": stamp}
