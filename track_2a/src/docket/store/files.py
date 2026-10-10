"""The store in files: one JSON per affair, one per document's fields report, the decisions as NDJSON. For a
run without a database, and for the tests."""

from __future__ import annotations

import json
from pathlib import Path

from docket.store.base import Store, now, safe_name


class FileStore(Store):
    kind = "files"

    def __init__(self, folder: Path):
        super().__init__(folder)
        for part in ("affairs", "documents", "pages"):
            (folder / part).mkdir(parents=True, exist_ok=True)

    def _affair_file(self, key: str) -> Path:
        return self.folder / "affairs" / f"{safe_name(key)}.json"

    def put_affair(self, key: str, record: dict, documents: list[dict]) -> None:
        data = {"key": key, "record": record, "documents": documents, "updated_at": now()}
        self._affair_file(key).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def get_affair(self, key: str) -> dict | None:
        path = self._affair_file(key)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if data.get("key") == key else None

    def save_record(self, key: str, record: dict) -> None:
        data = self.get_affair(key)
        if data is None:
            raise KeyError(key)
        data["record"] = record
        data["updated_at"] = now()
        self._affair_file(key).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def list_affairs(self) -> list[dict]:
        out = []
        for path in (self.folder / "affairs").glob("*.json"):
            out.append(json.loads(path.read_text(encoding="utf-8")))
        return sorted(out, key=lambda a: a.get("updated_at", ""), reverse=True)

    def put_fields(self, name: str, report: dict) -> None:
        path = self.folder / "documents" / f"{safe_name(name)}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def get_fields(self, name: str) -> dict | None:
        path = self.folder / "documents" / f"{safe_name(name)}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None

    def add_decision(self, row: dict) -> None:
        with (self.folder / "decisions.ndjson").open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def list_decisions(self, key: str | None = None) -> list[dict]:
        path = self.folder / "decisions.ndjson"
        if not path.is_file():
            return []
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return [r for r in rows if key is None or r.get("affair") == key]

    def get_rules(self) -> list[dict]:
        path = self.folder / "rules.json"
        return json.loads(path.read_text(encoding="utf-8"))["rules"] if path.is_file() else []

    def put_rules(self, rules: list[dict]) -> None:
        text = json.dumps({"rules": rules}, ensure_ascii=False, indent=2) + "\n"
        (self.folder / "rules.json").write_text(text, encoding="utf-8")

    def get_vocabulary(self) -> list[dict]:
        path = self.folder / "vocabulary.json"
        return json.loads(path.read_text(encoding="utf-8"))["rows"] if path.is_file() else []

    def put_vocabulary(self, rows: list[dict]) -> None:
        held = {(r["list"], r["body"], r["name"]): r for r in self.get_vocabulary()}
        held.update({(r["list"], r["body"], r["name"]): r for r in rows})
        self._write_vocabulary(held)

    def drop_vocabulary(self, rows: list[dict]) -> None:
        held = {(r["list"], r["body"], r["name"]): r for r in self.get_vocabulary()}
        for r in rows:
            held.pop((r["list"], r["body"], r["name"]), None)
        self._write_vocabulary(held)

    def _write_vocabulary(self, held: dict[tuple[str, str, str], dict]) -> None:
        # one row per line: the file holds some fifteen hundred of them
        lines = ",\n".join("  " + json.dumps(held[key], ensure_ascii=False) for key in sorted(held))
        (self.folder / "vocabulary.json").write_text('{"rows": [\n' + lines + "\n]}\n", encoding="utf-8")
