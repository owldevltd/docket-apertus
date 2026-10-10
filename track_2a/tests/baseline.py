"""The affairs from a stored run, without a model: what the code makes of the same answers has to stay the same.

Every shipped document carries what a run with the model left for it (run.json: its blocks, its identity, the
kind it was found to be and the model's answer for every field) and the affair that run became (affair.json).
The test forms the affairs again the way a run does, every document alone and in a store of its own, and
compares each with the stored one character by character. A change to the core that moves a value or a place
shows here before it shows anywhere else.

    python3 tests/baseline.py [--write] <document dir> ...

With --write the stored affairs are replaced by what the code makes now, for a change that is meant.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.merge import Document, values_of  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.fields.placer import day  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.runner import _write_affairs  # noqa: E402
from docket.store.review import sources_of  # noqa: E402


def first_difference(a: str, b: str) -> str:
    """Where two texts part, with a few characters of each."""
    at = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    return f"at character {at}: stored {a[at:at + 50]!r}, now {b[at:at + 50]!r}"


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith("--")]
    write = "--write" in argv
    if not dirs:
        print("usage: python3 tests/baseline.py [--write] <document dir> ...")
        return 1
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    base = load_config()
    contract = load_contract(base)
    fields = load_field_file(base, contract)
    knowledge = load_knowledge(base)
    count = places = 0
    for d in dirs:
        stored_run = d / "run.json"
        pdf = next(d.glob("*.pdf"), None) if d.is_dir() else None
        if pdf is None or not stored_run.is_file():
            continue
        count += 1
        name = pdf.stem
        run = json.loads(stored_run.read_text(encoding="utf-8"))
        # every document alone and in a store of its own: what one makes does not hang on the others
        with tempfile.TemporaryDirectory() as tmp:
            config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
            out = Path(tmp) / "out"
            out.mkdir()
            # the report as a run leaves it beside the record, for the store
            report = {"identity": run["identity"], "kind": run.get("kind"), "fields": run["fields"]}
            (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            values = values_of(run["fields"])
            date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
            identity = run["identity"]
            document = Document(1, name, run["pages"], run["body"], values, identity.get("key") or "dok-" + name,
                                date, identity.get("body") or "")
            affair = _write_affairs(out, [document], fields, contract, knowledge, config, lambda line: None)[0]
            file = out / "affairs" / (re.sub(r"[^\w.-]+", "_", affair["key"]) + ".json")
            now = file.read_text(encoding="utf-8")
        places += len(sources_of(json.loads(now)))
        stored = d / "affair.json"
        if write:
            stored.write_text(now, encoding="utf-8")
            print(f"     {name}: affair {affair['key']} written, {len(now)} characters")
            continue
        if not stored.is_file():
            check(False, f"{name}: no stored affair (run with --write once)")
            continue
        before = stored.read_text(encoding="utf-8")
        check(affair["valid"] and before == now, f"{name}: affair {affair['key']} is valid and the stored one"
              + ("" if before == now else ", " + first_difference(before, now)))
    check(count > 0, f"{count} documents with a stored run, {places} values with their places in their affairs")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
