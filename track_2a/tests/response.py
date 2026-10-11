"""The answer within a document, without a model: what stands under a heading that announces an answer becomes
the response of the document, beside its body. The heading counts in the languages of the documents, with or
without accents, short or long, with a counter before it; a word that only begins alike does not. The answer
runs to the next section with a known name or to the end, a second such heading opens a second answer, and
the blocks keep their ids, so body and answers together are the document again. On the shipped documents: the
kickoff example carries its answer, the affair is valid, and no other document gets one.

    python3 tests/response.py data/documents/*
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.config import load_config  # noqa: E402
from docket.document.response import lift, whole  # noqa: E402
from docket.fields.placer import blocks_of  # noqa: E402
from docket.pipeline import load_contract, load_knowledge  # noqa: E402


def blocks(*parts: tuple[str, str | None] | str) -> list[dict]:
    """Blocks in reading order: a string is a paragraph, a pair is a heading with its section name or None."""
    out = []
    for n, part in enumerate(parts, 1):
        place = {"id": f"b{n}", "page": 1, "x": 0, "y": n * 10, "width": 10, "height": 10}
        if isinstance(part, str):
            out.append({**place, "type": "p", "text": part})
        else:
            sec = {**place, "type": "sec", "title": part[0], "content": []}
            out.append(sec | ({"sec-type": part[1]} if part[1] else {}))
    return out


def main(argv: list[str]) -> int:
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    config = load_config()
    knowledge = load_knowledge(config)
    names = knowledge.answers

    def ids(found: list[dict]) -> list[list[str]]:
        return [[b["id"] for b in r["body"]] for r in found]

    doc = blocks("head", ("Text", "text"), "asks", ("Antwort des Gemeinderates", "antwort"), "answers", "more")
    body, found = lift(doc, names)
    check([b["id"] for b in body] == ["b1", "b2", "b3"] and ids(found) == [["b4", "b5", "b6"]]
          and found[0]["title"] == "Antwort des Gemeinderates" and found[0]["response-type"] == "answer",
          "what stands from the heading of the answer on is the response, with the heading as its title")
    check(whole({"body": body, "response": found}) == doc and whole({"body": doc}) == doc,
          "body and response together are the blocks of the document in their order again")

    # the heading as the documents print it, in a body stored before the name was known
    for title in ("REPONSE DU CONSEIL D’ETAT", "RÉPONSE DU CONSEIL D'ETAT", "2. Beantwortung der Fragen:",
                  "Risposta del 14 marzo 2019 all'interpellanza presentata il 2 marzo 2019 da una deputata"):
        body, found = lift(blocks("asks", (title, None), "answers"), names)
        check(ids(found) == [["b2", "b3"]] and len(body) == 1, f"a heading opens the answer: {title[:48]}")
    for title in ("Antworten auf häufige Fragen", "Die Antwort steht aus", "Begründung"):
        body, found = lift(blocks("asks", (title, None), "more"), names)
        check(not found and len(body) == 3, f"a heading that only looks alike opens none: {title}")

    doc = blocks(("Antwort", "antwort"), "one", ("Zur Lage", None), "inside", ("Beschluss", "beschluss"), "decided",
                 ("Antwort auf die Nachfrage", None), "two")
    body, found = lift(doc, names)
    check(ids(found) == [["b1", "b2", "b3", "b4"], ["b7", "b8"]] and [b["id"] for b in body] == ["b5", "b6"],
          "the answer keeps a heading without a known name, ends at the next known section, and a second "
          "heading opens a second answer")
    check(whole({"body": body, "response": found}) == doc, "put back, the blocks stand in their order")
    check(lift(doc, []) == (doc, []), "without the names nothing is lifted")

    # the shipped documents: only the one that prints its answer under such a heading carries a response
    contract = load_contract(config)
    with_answer = {}
    for folder in sorted(Path(a) for a in argv if not a.startswith("--")):
        stored, run = folder / "affair.json", folder / "run.json"
        if not stored.is_file() or not run.is_file():
            continue
        record = json.loads(stored.read_text(encoding="utf-8"))
        entry = record["docs"]["data"][0]
        if entry.get("response"):
            with_answer[folder.name] = [r["title"] for r in entry["response"]]
        same = whole(entry) == json.loads(run.read_text(encoding="utf-8"))["body"]
        unique = len({b["id"] for b in blocks_of(whole(entry))}) == len(blocks_of(whole(entry)))
        if not (same and unique and not contract.check(record)):
            check(False, f"{folder.name}: body and response are the blocks of the run, each id once, and valid")
    check(with_answer == {"nidau-m185": ["Antwort des Gemeinderates"]},
          f"of the shipped documents the kickoff example carries its answer, no other: {with_answer}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
