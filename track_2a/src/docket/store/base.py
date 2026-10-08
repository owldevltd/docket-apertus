"""What every store does. Page images stay on disk under the store's folder in both backends; the records,
the fields reports and the decisions go where the backend keeps them."""

from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path


def safe_name(key: str) -> str:
    return re.sub(r"[^\w.-]+", "_", key)


def stamp() -> str:
    """The time now, ISO 8601 with the server's zone (TZ=Europe/Zurich in the container)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def now() -> str:
    return stamp()


class Store:
    """The operations; the backends fill them in. `folder` holds the page images."""

    kind = "none"

    def __init__(self, folder: Path):
        self.folder = folder

    # affairs
    def put_affair(self, key: str, record: dict, documents: list[dict]) -> None:
        """Stores an affair with its documents ({name, id, pages}); replaces an earlier one under the key."""
        raise NotImplementedError

    def get_affair(self, key: str) -> dict | None:
        """{key, record, documents, updated_at} or None."""
        raise NotImplementedError

    def save_record(self, key: str, record: dict) -> None:
        """Replaces the record of a stored affair (after a decision)."""
        raise NotImplementedError

    def list_affairs(self) -> list[dict]:
        """Every affair as {key, record, documents, updated_at}, newest first."""
        raise NotImplementedError

    # documents
    def put_fields(self, name: str, report: dict) -> None:
        """The fields report of a document (what the model answered, per field)."""
        raise NotImplementedError

    def get_fields(self, name: str) -> dict | None:
        raise NotImplementedError

    # decisions
    def add_decision(self, row: dict) -> None:
        raise NotImplementedError

    def list_decisions(self, key: str | None = None) -> list[dict]:
        raise NotImplementedError

    # rules of the general repair
    def get_rules(self) -> list[dict]:
        raise NotImplementedError

    def put_rules(self, rules: list[dict]) -> None:
        raise NotImplementedError

    # pages, on disk in every backend
    def put_pages(self, name: str, source: Path) -> int:
        """Copies the page images and page files of a document from a run folder; returns the count."""
        target = self.folder / "pages" / safe_name(name)
        target.mkdir(parents=True, exist_ok=True)
        count = 0
        for file in sorted(source.glob(f"{name}-s*.png")):
            if re.fullmatch(rf"{re.escape(name)}-s\d+\.png", file.name):
                shutil.copyfile(file, target / file.name)
                count += 1
        for file in sorted(source.glob(f"{name}-s*.json")):
            shutil.copyfile(file, target / file.name)
        return count

    def page_path(self, name: str, n: int) -> Path | None:
        path = self.folder / "pages" / safe_name(name) / f"{name}-s{n}.png"
        return path if path.is_file() else None

    def page_data(self, name: str, n: int) -> dict | None:
        path = self.folder / "pages" / safe_name(name) / f"{name}-s{n}.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
