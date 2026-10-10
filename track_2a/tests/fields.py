"""The fields file against the contract and the known values against the page, without a model.

For every shipped document whose affair at OpenParlData is known (number, title, type, begin date), whether
that value stands literally on the first pages of the built blocks, found by the same rule the filler uses on
the model's answers. This is the ceiling of the literal rule: a value that does not stand on the page cannot be
taken from it. The located values are built into the record, which must validate against the contract.

    python3 tests/fields.py --pages=<analyzed dir> --documents=<records dir> [--out=<file.md>] <document dir> ...
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.config import load_config  # noqa: E402
from docket.fields.filler import parse  # noqa: E402
from docket.fields.placer import fill, locate  # noqa: E402
from docket.pipeline import first_pages, load_contract, load_field_file  # noqa: E402

# the affair's values in document.json and the field that asks for them, by its path in the fields file
KEYS = {
    "number": ["number"],
    "title": ["title", "de"],
    "type": ["type_name", "de"],
    "begin_date": ["begin_date"],
}


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith("--")]
    pages_dir = next((Path(a[8:]) for a in argv if a.startswith("--pages=")), None)
    records_dir = next((Path(a[12:]) for a in argv if a.startswith("--documents=")), None)
    out_file = next((Path(a[6:]) for a in argv if a.startswith("--out=")), None)
    if not dirs or pages_dir is None or records_dir is None:
        print("usage: python3 tests/fields.py --pages=<dir> --documents=<dir> [--out=<file.md>] <document dir> ...")
        return 1
    config = load_config()
    contract = load_contract(config)
    fields = load_field_file(config, contract)
    by_path = {tuple(f.path): name for name, f in fields.fields.items()}
    names = {key: by_path.get(tuple(path)) for key, path in KEYS.items()}
    missing = [key for key, name in names.items() if name is None]
    if missing:
        print("FAIL the fields file has no field for " + ", ".join(missing))
        return 1
    # the lines of an answer are told by the field's name; where the model puts its own word for a name, in the
    # language of the question, the place of the line tells the field, as long as the answer has one line per
    # field asked and nothing is out of place
    asked = ["number", "title", "type"]
    plain = parse("number: 1 [b2]\ntitle: A title [b3]\ntype: Motion [b4]", asked)
    own_words = parse("Geschäftsnummer: 1 [b2]\ntitle: A title [b3]\nArt: Motion [b4]", asked)
    moved = parse("Geschäftsnummer: 1 [b2]\ntype: Motion [b4]\ntitle: A title [b3]", asked)
    short = parse("Geschäftsnummer: 1 [b2]\ntitle: A title [b3]", asked)
    told = {"number": "1", "title": "A title", "type": "Motion"}
    ok = (plain[0] == told and plain[1]["number"] == ["b2"] and own_words[0] == told
          and own_words[1]["type"] == ["b4"] and "number" not in moved[0] and "number" not in short[0])
    print(("ok   " if ok else "FAIL ") + "answer lines: by the field's name, by their place where the model used "
          "its own word, and not by place when a line is missing or moved")
    if not ok:
        return 1
    print(f"ok   fields file: {len(fields.fields)} fields, every path open in the contract")

    rows = []
    known = found = 0
    failed = False
    for d in dirs:
        info = d / "document.json"
        pdf = next(d.glob("*.pdf"), None) if d.is_dir() else None
        if pdf is None or not info.is_file():
            continue
        affair = json.loads(info.read_text(encoding="utf-8")).get("affair") or {}
        record_file = records_dir / f"{pdf.stem}.json"
        if not record_file.is_file():
            print(f"FAIL {pdf.stem}: no record in {records_dir}")
            failed = True
            continue
        record = json.loads(record_file.read_text(encoding="utf-8"))
        pages = []
        n = 1
        while (pages_dir / f"{pdf.stem}-s{n}.json").is_file():
            pages.append(json.loads((pages_dir / f"{pdf.stem}-s{n}.json").read_text(encoding="utf-8")))
            n += 1
        first = first_pages(pages) if pages else [1]
        body = record["docs"]["data"][0]["body"]
        values: dict[str, list[dict]] = {}
        cells = []
        for key in KEYS:
            value = affair.get(key)
            if value in (None, ""):
                cells.append("—")
                continue
            known += 1
            block = locate(str(value), body, first)
            if block is None:
                cells.append("not on the page")
                continue
            found += 1
            cells.append(block)
            values[names[key]] = [{"value": str(value), "block": block, "how": "literal"}]
        filled, _ = fill(record, 1, values, fields, contract, body)
        errors = contract.check(filled)
        state = "valid" if not errors else f"{len(errors)} violations, first: {errors[0]}"
        if errors:
            failed = True
        rows.append(f"| {pdf.stem} | " + " | ".join(cells) + f" | {state} |")
        hits = sum(1 for c in cells if c.startswith("b"))
        asked = sum(1 for c in cells if c != "—")
        mark = "ok  " if not errors else "FAIL"
        print(f"{mark} {pdf.stem}: {hits} of {asked} known values on the first pages, record {state}")
    print(f"{found} of {known} known values stand literally on the first pages")

    if out_file is not None:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        head = (
            "# Known values against the page\n\n"
            f"Generated by `tests/fields.py` on {time.strftime('%Y-%m-%d')}, no model call. Per document the affair's "
            "values as OpenParlData holds them (number, title, type, begin date) looked for literally on the first "
            "pages of the built blocks, with the rule the filler uses; a date in any spelling of the same day. The "
            "cell names the block that holds the value. The located values are built into the record, which is "
            "validated against the contract.\n\n"
            "| Document | number | title | type | begin_date | Record |\n|---|---|---|---|---|---|\n"
        )
        foot = f"\n{found} of {known} known values stand literally on the first pages.\n"
        out_file.write_text(head + "\n".join(rows) + "\n" + foot, encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
