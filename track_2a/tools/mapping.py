"""Writes the mapping of the affair schema onto OpenParlData and the standards as a page, and checks its names.

    python3 tools/mapping.py                       writes docs/mapping.md from data/schema/mapping.json
    python3 tools/mapping.py --standards <folder>  checks every name against the schemas in the folder first

data/schema/mapping.json says, per term of the schema, what holds the same thing in OpenParlData, JATS, Akoma
Ntoso, Parla-CLARIN, Popolo and Docling, by the names of their own schemas. The check takes those schemas as
files, they are not part of this repository:

    <folder>/openparldata/fields.json     {table: [field, ...]}, the fields of the tables of the exports
    <folder>/jats/                        the XSD of JATS 1.3 Archiving (ftp.ncbi.nih.gov/pub/jats)
    <folder>/akoma-ntoso/                 akomantoso30.xsd (docs.oasis-open.org/legaldocml)
    <folder>/parla-clarin/                parla-clarin.xsd (github.com/clarin-eric/parla-clarin)
    <folder>/popolo/                      the JSON schemas, one per class (github.com/popolo-project/popolo-spec)
    <folder>/docling/DoclingDocument.json the JSON Schema (github.com/docling-project/docling-core, docs/)

A name counts as found when the schema defines it: an element or an attribute of an XSD, a property of a class,
a field of a table. An attribute is looked for in the schema, not on the element it is named with. Whether the
element means the same as the term is not checked by anything; that is the reading the file states. When every
name is found, the day and the counts are noted in mapping.json and stand at the head of the page.
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "schema" / "mapping.json"
PAGE = ROOT / "docs" / "mapping.md"

XML = ("jats", "akoma-ntoso", "parla-clarin")


def render(mapping: dict) -> str:
    """The page: per group a table with one row per term and one column per standard, the notes below it."""
    standards = mapping["standards"]
    rows = [r for g in mapping["groups"] for r in g["rows"]]
    out = ["# The affair schema and the standards", "", mapping["about"], ""]
    checked = mapping.get("checked")
    if checked:
        out += [f"Checked on {checked['on']}: {checked['names']} names, all found in the schemas named below.", ""]
    out += ["| Standard | Edition | How a name is written | Terms with a name there |", "| --- | --- | --- | ---: |"]
    for s in standards:
        held = sum(1 for r in rows if r[s["id"]])
        out.append(f"| {s['name']} | {s['edition']} | {s['names']} | {held} of {len(rows)} |")
    out += ["", "A dash means that nothing was found for the term in that schema."]
    for group in mapping["groups"]:
        out += ["", f"## {group['title']}", "",
                "| Here | What it is | " + " | ".join(s["name"] for s in standards) + " |",
                "| --- | --- |" + " --- |" * len(standards)]
        notes = []
        for r in group["rows"]:
            cells = [", ".join(f"`{n}`" for n in r[s["id"]]) or "–" for s in standards]
            out.append(f"| {r['term']} | {r['means']} | " + " | ".join(cells) + " |")
            names = {s["id"]: s["name"] for s in standards}
            notes += [f"- {r['term']} in {names[i]}: {text}." for i, text in (r.get("notes") or {}).items()]
        if notes:
            out += [""] + notes
    return "\n".join(out) + "\n"


def _xsd(folder: Path) -> tuple[set[str], set[str]]:
    """The elements and the attributes the XSD files of a folder define."""
    elements: set[str] = set()
    attributes: set[str] = set()
    for file in folder.rglob("*.xsd"):
        text = file.read_text(encoding="utf-8", errors="replace")
        elements |= set(re.findall(r'<xsd?:element\s+[^>]*?name="([^"]+)"', text))
        attributes |= set(re.findall(r'<xsd?:attribute\s+[^>]*?name="([^"]+)"', text))
        attributes |= set(re.findall(r'<xsd?:attribute\s+[^>]*?ref="(?:\w+:)?([^"]+)"', text))
    return elements, attributes


def _holds(standard: str, folder: Path):
    """A function that says whether the schema of a standard defines a name; None when its files are missing."""
    if standard in XML:
        elements, attributes = _xsd(folder)
        if not elements:
            return None

        def in_xsd(name: str) -> bool:
            # "sec", "@lang" or "sec/@sec-type"
            element, _, attribute = name.partition("@")
            element = element.rstrip("/")
            return (not element or element in elements) and (not attribute or attribute in attributes)
        return in_xsd
    if standard == "openparldata":
        file = folder / "fields.json"
        if not file.is_file():
            return None
        tables = json.loads(file.read_text(encoding="utf-8"))
        return lambda name: name.partition(".")[0] in tables and (
            "." not in name or name.partition(".")[2] in tables[name.partition(".")[0]])
    if standard == "popolo":
        classes = {f.stem: json.loads(f.read_text(encoding="utf-8")).get("properties") or {}
                   for f in folder.glob("*.json")}
        if not classes:
            return None
        return lambda name: name.partition(".")[0] in classes and (
            "." not in name or name.partition(".")[2] in classes[name.partition(".")[0]])
    file = folder / "DoclingDocument.json"
    if not file.is_file():
        return None
    text = file.read_text(encoding="utf-8")
    schema = json.loads(text)

    def in_docling(name: str) -> bool:
        name, _, value = name.partition("=")
        owner, _, prop = name.partition(".")
        if not prop:
            return owner in schema["$defs"] or owner in schema["properties"]
        found = prop in (schema["$defs"].get(owner) or {}).get("properties", {})
        return found and (not value or f'"{value}"' in text)
    return in_docling


def check(mapping: dict, folder: Path) -> tuple[dict[str, int], dict[str, list[str]], list[str]]:
    """Holds every name of the mapping against the schemas under `folder`. Returns the names found per
    standard, the names not found per standard, and the standards whose schema is not there."""
    found: dict[str, int] = {}
    missing: dict[str, list[str]] = {}
    absent = []
    for s in mapping["standards"]:
        holds = _holds(s["id"], folder / s["id"])
        if holds is None:
            absent.append(s["id"])
            continue
        names = sorted({n for g in mapping["groups"] for r in g["rows"] for n in r[s["id"]]})
        missing[s["id"]] = [n for n in names if not holds(n)]
        found[s["id"]] = len(names) - len(missing[s["id"]])
    return found, missing, absent


def main(argv: list[str]) -> int:
    mapping = json.loads(SOURCE.read_text(encoding="utf-8"))
    if "--standards" in argv:
        folder = Path(argv[argv.index("--standards") + 1])
        found, missing, absent = check(mapping, folder)
        for s in mapping["standards"]:
            if s["id"] in absent:
                print(f"{s['name']}: no schema under {folder / s['id']}, not checked")
            else:
                gone = missing[s["id"]]
                print(f"{s['name']}: {found[s['id']]} names found"
                      + (f", not found: {', '.join(gone)}" if gone else ""))
        if absent or any(missing.values()):
            return 1
        mapping["checked"] = {"on": time.strftime("%Y-%m-%d"), "names": sum(found.values()), "found": found}
        SOURCE.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PAGE.write_text(render(mapping), encoding="utf-8")
    rows = sum(len(g["rows"]) for g in mapping["groups"])
    print(f"{PAGE.relative_to(ROOT)}: {rows} terms, {len(mapping['standards'])} standards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
