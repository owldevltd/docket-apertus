"""Learns the second opinion from what a store holds, once and without the model: where in the documents of
a parliament the value of a field usually stands, and a small network that tells from the look of a block
whether it holds a field (docket.fields.second). Both are tried on documents held back, and only what agreed
more often than it disagreed is kept for the runs. What was learnt lies in the store; a run after it holds
the second opinion against the model. Run it again when the store has grown or people have decided more.

    python3 tools/learn.py

Works on the store the configuration names: files under the storage folder, or Postgres with DATABASE_URL.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import load_config  # noqa: E402
from docket.fields import second  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.vocabulary import Vocabulary  # noqa: E402


def main() -> int:
    config = load_config()
    fields = load_field_file(config, load_contract(config))
    store = open_store(config)
    learnt = second.learn(second.from_store(store), fields, load_knowledge(config).forms,
                          Vocabulary(store.get_vocabulary()))
    store.put_learnt(learnt)
    print(f"learnt from {learnt['documents']} documents in the {store.kind} store")
    kept = 0
    for parliament, places in sorted(learnt["places"].items()):
        for name, p in places.items():
            kept += 1 if p["use"] else 0
            print(f"  place    {parliament:8} {name:14} in {p['documents']:3} documents, usual place in "
                  f"{p['share']:.0%}; held back: agreed {p['agree']}, disagreed {p['disagree']}; "
                  + (f"used from a share of {p['cut']:.0%}" if p["use"] else "not used"))
    for net in (learnt["network"], learnt["lists"]):
        for name, c in ((net or {}).get("cuts") or {}).items():
            kept += 1 if c["use"] else 0
            print(f"  network  {'':8} {name:14} held back: agreed {c['agree']}, disagreed {c['disagree']}; "
                  + (f"used from {c['cut']}" if c["use"] else "not used"))
    print(f"{kept} ways kept")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
