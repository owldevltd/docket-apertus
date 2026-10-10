"""The store: affairs with their documents, the decisions people took and the vocabulary, in files or in
Postgres."""

from __future__ import annotations

from docket.config import Config
from docket.store.base import Store
from docket.store.files import FileStore
from docket.store.vocabulary import load_stem, sync


def open_store(config: Config) -> Store:
    """Postgres when DATABASE_URL is set, else files under the storage folder. The vocabulary of the store is
    brought up to the stem of the checkout: an empty store is filled, a newer stem replaces what nobody
    changed."""
    if config.database_url:
        from docket.store.postgres import PostgresStore

        store: Store = PostgresStore(config.database_url, config.storage_dir / "store")
    else:
        store = FileStore(config.storage_dir / "store")
    stem = load_stem(config.data_dir / "knowledge" / "vocabulary.json")
    if stem is not None:
        sync(store, stem)
    return store
