"""The mapping of the schema onto OpenParlData and the standards, without a network: every key the contract
adds stands in a row, and no row names a key the contract does not have; every row says something for every
standard, a list of names or an empty one; the page is what the tool writes from the file; the note of the
check counts the names the file holds now, so a name added later shows as unchecked; and the check itself
tells a name a schema does not define, an attribute, a property and a schema that is not there.

    python3 tests/mapping.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

from mapping import PAGE, SOURCE, check, render  # noqa: E402


def keys_of(node, out: set[str]) -> set[str]:
    """Every property name a JSON Schema defines, at any depth."""
    if isinstance(node, dict):
        out |= set(node.get("properties") or {})
        for value in node.values():
            keys_of(value, out)
    elif isinstance(node, list):
        for value in node:
            keys_of(value, out)
    return out


def main() -> int:
    failed = False

    def ok(passed: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not passed
        print(("ok   " if passed else "FAIL ") + text)

    mapping = json.loads(SOURCE.read_text(encoding="utf-8"))
    standards = [s["id"] for s in mapping["standards"]]
    rows = [r for g in mapping["groups"] for r in g["rows"]]
    contract = keys_of(json.loads((ROOT / "data" / "schema" / "docket.json").read_text(encoding="utf-8")), set())
    # "type" is the name of a block, told by the rows of the blocks themselves
    covered = {k for r in rows for k in r["keys"]} | {"type"}
    ok(contract <= covered, f"every one of the {len(contract)} keys the contract adds stands in a row"
       + (f"; missing: {sorted(contract - covered)}" if contract - covered else ""))
    ok(covered <= contract, "no row names a key the contract does not have"
       + (f"; unknown: {sorted(covered - contract)}" if covered - contract else ""))
    whole = all(isinstance(r.get(s), list) and all(isinstance(n, str) and n for n in r[s])
                for r in rows for s in standards)
    ok(whole and all(r["term"] and r["means"] for r in rows),
       f"each of the {len(rows)} rows says what it is and holds a list for each of the {len(standards)} standards")
    ok(all(set(r.get("notes") or {}) <= set(standards) for r in rows), "a note belongs to one of the standards")
    ok(PAGE.read_text(encoding="utf-8") == render(mapping), "the page is what the tool writes from the file")
    names = {s: len({n for r in rows for n in r[s]}) for s in standards}
    checked = mapping.get("checked") or {}
    ok(checked.get("found") == names and checked.get("names") == sum(names.values()),
       f"the note of the check counts the names the file holds now ({sum(names.values())})")

    # the check itself, on schemas of a few lines
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        for name in ("jats", "popolo", "docling", "openparldata"):
            (folder / name).mkdir()
        (folder / "jats" / "small.xsd").write_text(
            '<xs:schema><xs:element name="sec"/><xs:attribute name="sec-type"/><xs:attribute ref="xml:lang"/>'
            "</xs:schema>", encoding="utf-8")
        (folder / "popolo" / "motion.json").write_text('{"properties": {"date": {}}}', encoding="utf-8")
        (folder / "docling" / "DoclingDocument.json").write_text(
            '{"properties": {"body": {}}, "$defs": {"TextItem": {"properties": {"label": {"const": "footnote"}}}}}',
            encoding="utf-8")
        (folder / "openparldata" / "fields.json").write_text('{"affairs": ["number"]}', encoding="utf-8")
        small = {"standards": [{"id": s} for s in ("jats", "akoma-ntoso", "popolo", "docling", "openparldata")],
                 "groups": [{"rows": [{
                     "jats": ["sec", "sec/@sec-type", "@lang", "p", "sec/@style"], "akoma-ntoso": ["doc"],
                     "popolo": ["motion", "motion.date", "motion.result", "vote"],
                     "docling": ["body", "TextItem", "TextItem.label=footnote", "TextItem.label=title",
                                 "TextItem.prov"],
                     "openparldata": ["affairs", "affairs.number", "affairs.title_de", "docs.name"]}]}]}
        found, missing, absent = check(small, folder)
        ok(absent == ["akoma-ntoso"], "a standard whose schema is not there is told as not checked")
        ok(missing == {"jats": ["p", "sec/@style"], "popolo": ["motion.result", "vote"],
                       "docling": ["TextItem.label=title", "TextItem.prov"],
                       "openparldata": ["affairs.title_de", "docs.name"]}
           and found == {"jats": 3, "popolo": 2, "docling": 3, "openparldata": 2},
           "an element, an attribute, a property, a value and a field the schema does not define are told; the "
           "others are found")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
