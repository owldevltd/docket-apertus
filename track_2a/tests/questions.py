"""Three questions across the parliaments from the rows of a store, without a model (docket.questions).

A store of its own is filled with the shipped documents from the runs stored beside them. Then: every document
is counted once in each of the three answers; the persons who back an affair are the names its rows hold as
authors and co-signers, each once; the kinds are the ones the rows tell; a field is counted for a document
when a value of it was found on a page. Two small exports in the shape of OpenParlData's stand in for theirs:
an affair is found there by parliament and number, or by the id a list of drawn documents gives, and only the
persons held as authors and co-signers count.

    python3 tests/questions.py --pages=<analyzed dir>
"""

from __future__ import annotations

import gzip
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.config import load_config  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.questions import answers, collect, held, label, markdown  # noqa: E402
from docket.runner import run_shipped  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.register import key_of  # noqa: E402


def export(path: Path, rows: list[dict]) -> Path:
    with gzip.open(path, "wt", encoding="utf-8") as f:
        f.write("".join(json.dumps(row) + "\n" for row in rows))
    return path


def main(argv: list[str]) -> int:
    pages = next((Path(a[8:]) for a in argv if a.startswith("--pages=")), None)
    if pages is None or not pages.is_dir():
        print("usage: python3 tests/questions.py --pages=<analyzed dir>")
        return 1
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    base = load_config()
    fields = load_field_file(base, load_contract(base))
    bodies = load_knowledge(base).bodies
    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        run_shipped(Path(tmp) / "out", config, lambda line: None, pages)
        store = open_store(config)
        documents = collect(store, fields)
        found = answers(documents, fields, bodies)
        count = len(documents)
        check(count > 0 and found["documents"] == count
              and sum(r["documents"] for r in found["kinds"]) == count
              and sum(r["documents"] for r in found["printed"]) == count
              and sum(r["affairs"] for r in found["backing"]) == len(store.list_affairs()),
              f"{count} documents of {found['parliaments']} parliaments, each counted once in every answer")

        one = next(d for d in documents if d["name"] == "wettingen-115631")
        rows = [r for r in store.get_rows(one["name"]) if r["state"] == "placed"]
        names = {key_of(r["value"]) for r in rows if r["field"] in ("authors", "cosigners")}
        row = next(r for r in found["backing"] if r["parliament"] == label(one["body"], bodies))
        check(one["persons"] == names and row["affairs"] == 1 and row["most"] == len(names) > 0,
              f"{one['name']}: {len(names)} persons back the affair, the names of its rows, each once")
        told = {d["name"]: d["kind"] for d in documents}
        check(sum(sum(r["kinds"].values()) for r in found["kinds"]) == count
              and all(told[n] == next((r["value"] for r in store.get_rows(n) if r.get("about") == "document"), None)
                      for n in told),
              f"the kinds are the ones the rows tell: {sorted({k for k in told.values() if k})}")
        titled = sum(1 for d in documents if any(r["field"] == "title" and r["state"] == "placed"
                                                 for r in store.get_rows(d["name"])))
        check(sum(r["fields"]["title"] for r in found["printed"]) == titled
              and all(n <= r["documents"] for r in found["printed"] for n in r["fields"].values()),
              f"a title was found on a page of {titled} of {count} documents; no field in more documents than "
              f"there are")

        # two exports in the shape of OpenParlData's: one affair found by parliament and number, one by its id
        affairs = export(Path(tmp) / "affairs.ndjson.gz", [
            {"id": 1, "body_key": int(one["body"]), "number": "2017-0683"},
            {"id": 2, "body_key": int(one["body"]), "number": "2017-0999"},
            {"id": 7, "body_key": "XX", "number": "none"}])
        contributors = export(Path(tmp) / "contributors.ndjson.gz", [
            {"affair_id": 1, "type": "person", "role_harmonized": "author", "person_id": 11},
            {"affair_id": 1, "type": "person", "role_harmonized": "cosign", "person_id": 12},
            {"affair_id": 1, "type": "person", "role_harmonized": "author", "person_id": 11},
            {"affair_id": 1, "type": "person", "role_harmonized": "speaker", "person_id": 13},
            {"affair_id": 1, "type": "group", "role_harmonized": "author", "person_id": None},
            {"affair_id": 2, "type": "person", "role_harmonized": "author", "person_id": 14},
            {"affair_id": 7, "type": "person", "role_harmonized": "author", "person_id": 15}])
        there = held(affairs, contributors, documents)
        check(there == {one["affair"]: 2},
              "by parliament and number one affair is found there, with two persons: authors and co-signers, "
              "each once, no speaker and no group")
        drawn = {"nidau-m185": {"name": "nidau-m185", "body": "XX", "affair": 7}}
        listed = collect(store, fields, drawn)
        other = next(d for d in listed if d["name"] == "nidau-m185")
        there = held(affairs, contributors, listed)
        with_theirs = answers(listed, fields, bodies, there)
        row = next(r for r in with_theirs["backing"] if r["parliament"] == "XX")
        check(other["body"] == "XX" and there.get(other["affair"]) == 1 and row["found"] == 1 and row["theirs"] == 1
              and row["more"] + row["same"] + row["fewer"] == 1,
              "a list of drawn documents tells parliament and affair first: the affair is found there by its id")
        text = markdown(with_theirs)
        check(text.count("\n## ") == 3 and "at OpenParlData" in text and "at OpenParlData" not in markdown(found),
              "three tables; the column of OpenParlData only with the exports")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
