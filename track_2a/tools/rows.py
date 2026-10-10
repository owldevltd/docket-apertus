"""Writes the rows of every document a store already holds, once and without the model: for a store that was
filled before the rows existed. The rows are formed from what the store keeps of a document, its fields report
and its blocks (docket.store.rows); the reviews the records hold are taken into them. A second run changes
nothing.

    python3 tools/rows.py

Works on the store the configuration names: files under the storage folder, or Postgres with DATABASE_URL.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import load_config  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.rows import fill_rows  # noqa: E402


def main() -> int:
    config = load_config()
    contract = load_contract(config)
    store = open_store(config)
    count = fill_rows(store, load_field_file(config, contract), contract, load_knowledge(config).types)
    print(f"rows written for {count} documents in the {store.kind} store, {len(store.find_rows())} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
