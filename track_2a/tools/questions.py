"""Answers three questions across the parliaments from what a store holds, without the model: how many members
back an affair, what kinds of documents hang on the affairs, which details a parliament prints at all
(docket.questions). OpenParlData cannot answer them from its own data today; the documents can.

    python3 tools/questions.py [--affairs=<export> --contributors=<export>] [--drawn=<list>] [--out=<file>]

With the two exports of OpenParlData (affairs and contributors, NDJSON, gzip), the number of persons held
there for the same affair stands beside the first answer; nothing but counts is taken from the exports. An
affair is found there by its parliament and its number. Where the documents were drawn from OpenParlData, the
list they were drawn with says both for certain: a JSON list of {name, body, affair}, the name of the document
as the store holds it, the key of the parliament and the id of the affair there. Works on the store the
configuration names: files under the storage folder, or Postgres with DATABASE_URL.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import load_config  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.questions import answers, collect, held, markdown  # noqa: E402
from docket.store import open_store  # noqa: E402


def main(argv: list[str]) -> int:
    given = {a.split("=", 1)[0]: a.split("=", 1)[1] for a in argv if a.startswith("--") and "=" in a}
    if ("--affairs" in given) != ("--contributors" in given):
        print("usage: python3 tools/questions.py [--affairs=<export> --contributors=<export>] [--drawn=<list>] "
              "[--out=<file>]")
        return 1
    config = load_config()
    fields = load_field_file(config, load_contract(config))
    store = open_store(config)
    drawn = None
    if "--drawn" in given:
        drawn = {d["name"]: d for d in json.loads(Path(given["--drawn"]).read_text(encoding="utf-8"))}
    knowledge = load_knowledge(config)
    documents = collect(store, fields, drawn, knowledge.forms)
    there = None
    if "--affairs" in given:
        there = held(Path(given["--affairs"]), Path(given["--contributors"]), documents)
    text = markdown(answers(documents, fields, knowledge.bodies, there))
    if "--out" in given:
        Path(given["--out"]).write_text(text, encoding="utf-8")
        print(f"{len(documents)} documents of the {store.kind} store, written to {given['--out']}")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
