"""The store: affairs with their documents and the decisions people took, in files or in Postgres."""

from __future__ import annotations

from docket.config import Config
from docket.store.base import Store
from docket.store.files import FileStore


def open_store(config: Config) -> Store:
    """Postgres when DATABASE_URL is set, else files under the storage folder."""
    if config.database_url:
        from docket.store.postgres import PostgresStore

        return PostgresStore(config.database_url, config.storage_dir / "store")
    return FileStore(config.storage_dir / "store")
