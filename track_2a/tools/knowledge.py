"""Prior knowledge from the export of OpenParlData, once and without the model: per type label the harmonised
type in four languages, per parliament the forms of its affair numbers, and the names of the parliaments from
the API. Writes data/knowledge/types.json, number-forms.json and bodies.json; what else lies there stays.

    python3 tools/knowledge.py <affairs.ndjson.gz> [--no-bodies | --only-bodies]

The export is the daily affairs export (NDJSON, gzip). The names come from the API, one page of bodies at a
time with a pause, only for the parliaments that hold affairs or documents; --no-bodies skips the network,
--only-bodies leaves the two tables of the export as they are.
"""

from __future__ import annotations

import gzip
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "knowledge"
API = "https://api.openparldata.ch/v1"

# a number form counts for a parliament when at least this share of its affairs carries it
SHARE = 0.05

# bodies per API page, and the pause between pages
PAGE = 100
PAUSE = 2.0


def shape(number: str) -> str:
    """The form of a number: digits 9, letters a, separators stay, spaces vanish (as in the identity)."""
    import re

    t = re.sub(r"\s+", "", number.strip())
    return re.sub(r"[^\W\d_]", "a", re.sub(r"\d", "9", t))


def read_export(path: Path) -> tuple[dict, dict, set, int]:
    types: dict[str, dict] = {}
    shapes: dict[str, dict[str, int]] = {}
    keys: set[str] = set()
    n = 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for line in f:
            try:
                a = json.loads(line)
            except json.JSONDecodeError:
                continue
            n += 1
            for lang in ("de", "fr", "it"):
                label = str(a.get(f"type_name_{lang}") or "").strip().lower()
                kind = str(a.get("type_harmonized_de") or "")
                if not label or not kind:
                    continue
                t = types.setdefault(label, {"count": 0, "kinds": {}, "names": {}})
                t["count"] += 1
                t["kinds"][kind] = t["kinds"].get(kind, 0) + 1
                t["names"][kind] = {
                    "de": kind,
                    "fr": a.get("type_harmonized_fr"),
                    "it": a.get("type_harmonized_it"),
                    "en": a.get("type_harmonized_en"),
                }
            key = str(a.get("body_key") or "")
            form = shape(str(a.get("number") or ""))
            if key:
                keys.add(key)
            if key and form:
                shapes.setdefault(key, {})
                shapes[key][form] = shapes[key].get(form, 0) + 1
    return types, shapes, keys, n


def fetch(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers={"Accept": "application/json"}), timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))


def every(names: object) -> list[str]:
    """A name in every language it is held in, each once; a name with an addition in brackets ("Gossau (SG)")
    also without it, as a document prints it."""
    import re

    out: list[str] = []
    for value in (names.values() if isinstance(names, dict) else [names]):
        for form in (str(value or "").strip(), re.sub(r"\s*\([^)]*\)\s*$", "", str(value or "")).strip()):
            if form and form not in out:
                out.append(form)
    return out


def read_bodies(keys: set[str]) -> dict[str, dict]:
    """The names of the parliaments with affairs or documents, from the API, page by page."""
    with_docs = fetch(API + "/docs/group_by/body_key")
    for row in with_docs.get("data", []) if isinstance(with_docs, dict) else []:
        if isinstance(row, dict) and row.get("body_key"):
            keys.add(str(row["body_key"]))
    bodies: dict[str, dict] = {}
    url: str | None = f"{API}/bodies/?limit={PAGE}&offset=0"
    pages = 0
    while url:
        time.sleep(PAUSE)
        page = fetch(url)
        pages += 1
        for b in page.get("data", []):
            key = str(b.get("body_key") or "")
            if key not in keys:
                continue
            name = (b.get("name") or {}).get("de") or (b.get("name") or {}).get("fr") or ""
            hall = (b.get("legislative_name") or {}).get("de") or (b.get("legislative_name") or {}).get("fr") or ""
            # the name for the screen is the German one; a document is found by the name in its own language
            bodies[key] = {"name": name, "parliament": hall, "canton": b.get("canton_key"), "level": b.get("type"),
                           "names": every(b.get("name")), "parliaments": every(b.get("legislative_name"))}
        url = (page.get("meta") or {}).get("next_page")
    print(f"{pages} pages of bodies read, {len(bodies)} parliaments with affairs or documents named")
    return dict(sorted(bodies.items()))


def main(argv: list[str]) -> int:
    files = [a for a in argv if not a.startswith("--")]
    if not files:
        print("usage: python3 tools/knowledge.py <affairs.ndjson.gz> [--no-bodies | --only-bodies]")
        return 1
    export = Path(files[0])
    types, shapes, keys, n = read_export(export)
    stamp = time.strftime("%Y-%m-%d")

    table = {}
    for label, t in sorted(types.items()):
        top = max(t["kinds"].items(), key=lambda item: item[1])
        table[label] = {"type": t["names"][top[0]], "share": round(top[1] / t["count"], 3), "count": t["count"]}
    forms = {}
    for key, s in sorted(shapes.items()):
        total = sum(s.values())
        kept = {form: count for form, count in sorted(s.items(), key=lambda i: -i[1]) if count / total >= SHARE}
        if kept:
            forms[key] = kept

    OUT.mkdir(parents=True, exist_ok=True)
    if "--only-bodies" not in argv:
        source = f"affairs export of OpenParlData ({export.name}), {n} affairs, built {stamp}"
        _write("types.json", {"source": source, "types": table})
        _write("number-forms.json", {"source": source, "share": SHARE, "forms": forms})
        print(f"{n} affairs read: {len(table)} type labels, number forms for {len(forms)} parliaments")
    if "--no-bodies" not in argv:
        bodies = read_bodies(set(keys))
        source = f"API of OpenParlData, bodies with affairs or documents, built {stamp}"
        _write("bodies.json", {"source": source, "bodies": bodies})
    return 0


def _write(name: str, data: dict) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
