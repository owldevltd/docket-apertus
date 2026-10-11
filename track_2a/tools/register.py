"""Loads the persons of the parliaments from OpenParlData into the store, once and without the model: who sits
or sat in which parliament, with the id OpenParlData gives the person. The pipeline looks printed names up
there (docket.store.register).

    python3 tools/register.py [<persons.ndjson.gz> [<person_identities.ndjson.gz>]]

This is a preparation step, run once by hand by whoever sets an installation up; in operation Docket fetches
nothing, what comes in are PDFs. The persons are the one list that is not shipped with the repository,
because they are people: without files the two exports are fetched from OpenParlData's file server, one after
the other with a pause. Taken are the id, the name, the parliament and the party. The export also holds
addresses, telephone numbers and birthdays: none of that is read, and nothing is written into the repository;
the persons go into the store only (files under the storage folder, or Postgres with DATABASE_URL). A person
OpenParlData holds under several ids gets the primary one. Running it again with a newer export replaces what
came from there and leaves what the register learnt.
"""

from __future__ import annotations

import gzip
import json
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import load_config  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.register import sync  # noqa: E402

EXPORTS = "https://files.openparldata.ch/exports/"
AGENT = "docket-knowledge (one request every few seconds)"
PAUSE = 6.0

# the only keys read from a person
KEYS = ("id", "body_key", "firstname", "lastname", "party_de", "party_fr", "party_it")


def fetch(name: str, folder: Path) -> Path:
    target = folder / name
    request = urllib.request.Request(EXPORTS + name, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=300) as r, target.open("wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    return target


def rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv if not a.startswith("--")]
    with tempfile.TemporaryDirectory() as tmp:
        if not files:
            files = [fetch("persons.ndjson.gz", Path(tmp))]
            time.sleep(PAUSE)
            files.append(fetch("person_identities.ndjson.gz", Path(tmp)))
        primary = {}
        if len(files) > 1:
            primary = {r["id"]: r["identity_primary_id"] for r in rows(files[1]) if r.get("identity_primary_id")}
        persons = []
        for r in rows(files[0]):
            p = {k: r.get(k) for k in KEYS}
            persons.append({
                "id": primary.get(p["id"], p["id"]), "body": p["body_key"], "first": p["firstname"],
                "last": p["lastname"], "party": p["party_de"] or p["party_fr"] or p["party_it"],
            })
    store = open_store(load_config())
    counts = sync(store, persons, time.strftime("%Y-%m-%d"))
    bodies = store.register_bodies()
    print(f"{len(persons)} persons read, register of {len(bodies)} parliaments in the {store.kind} store: "
          + ", ".join(f"{k} {v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
