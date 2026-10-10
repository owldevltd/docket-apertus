"""The stem of the vocabularies from OpenParlData's admin panel, once and without the model: per parliament
the names it gives its affair types with the harmonised type each stands for, the harmonised names of the
events, and the kinds of groups. Writes data/knowledge/vocabulary.json. The store is filled from that file
and can be changed from there on (docket.store.vocabulary).

    python3 tools/vocabulary.py
    python3 tools/vocabulary.py --roles <contributors.ndjson.gz>

The panel shows these lists to a visitor without a login. They are read one page at a time with a pause, 18
requests on 10 October 2026; who last edited a row is not taken along. OpenParlData calls its harmonised
types provisional, so the file carries the day it was fetched and a newer file replaces in the store what
nobody changed by hand.

The roles of those who take part in an affair (author, co-signer, speaker) are not among the panel's lists.
With --roles they are taken from OpenParlData's export of the contributors
(files.openparldata.ch/exports/contributors.ndjson.gz, fetched once by hand): per parliament the names it
gives the roles, with the standard role each stands for. Only the parliament's key and the names of the role
are read from a row, nobody's name; the other lists of the file stay as they are.
"""

from __future__ import annotations

import gzip
import json
import re
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "knowledge" / "vocabulary.json"
PANEL = "https://admin.openparldata.ch/apiadmin/dwh"
AGENT = "docket-knowledge (one request every few seconds)"

# rows per page, and the pause between two requests
PAGE = 100
PAUSE = 4.0

LANGUAGES = ("de", "fr", "it", "en")


def fetch(table: str) -> list[dict]:
    """Every row of a list of the panel, page by page. Any answer but a list of rows ends the run."""
    rows: list[dict] = []
    while True:
        time.sleep(PAUSE)
        url = f"{PANEL}/{table}/?offset={len(rows)}&limit={PAGE}"
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": AGENT})
        with urllib.request.urlopen(request, timeout=60) as r:
            page = json.loads(r.read().decode("utf-8")).get("data")
        if not isinstance(page, list):
            raise ValueError(f"{table}: no rows in the answer")
        rows.extend(page)
        if len(page) < PAGE:
            return rows


def standards(rows: list[dict], prefix: str) -> list[dict]:
    """The standard names of a list in the four languages of the record, in the panel's order."""
    out = []
    for r in sorted(rows, key=lambda r: (r.get(prefix + "position") is None, r.get(prefix + "position") or 0)):
        entry = {"id": r[prefix + "id"], **{lang: clean(r.get(prefix + lang)) or None for lang in LANGUAGES}}
        if r.get(prefix + "wikidata_id"):
            entry["wikidata"] = r[prefix + "wikidata_id"]
        if "n_events" in r:
            entry["count"] = r["n_events"]
        if entry["de"]:
            out.append(entry)
    return out


def clean(text: object) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def type_names(rows: list[dict]) -> tuple[list[dict], int]:
    """What every parliament calls its affair types, with the id of the harmonised type or none. The same
    name twice for one parliament (a stray space, another case) is kept once; returns the names and how many
    were left out."""
    seen: set[tuple[str, str]] = set()
    out = []
    for r in rows:
        body = str(r.get("affair_type_mapping_body_key") or "")
        name = clean(r.get("affair_type_mapping_original_type_name"))
        if not body or not name or (body, name.lower()) in seen:
            continue
        seen.add((body, name.lower()))
        out.append({"body": body, "name": name, "lang": r.get("affair_type_mapping_original_type_lang"),
                    "standard": r.get("affair_type_mapping_harmonized_id")})
    return sorted(out, key=lambda e: (e["body"], e["name"].lower())), len(rows) - len(out)


def roles(export: Path) -> tuple[list[dict], list[dict], int]:
    """The standard roles and what every parliament calls its roles, from the export of the contributors. A
    name that stands for two standard roles in one parliament goes to the one it stands for more often;
    returns the standards, the names and how many names that were."""
    standard: dict[str, dict] = {}
    seen: Counter = Counter()
    with gzip.open(export, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            key = r.get("role_harmonized")
            name, lang = next(((clean(r.get(f"role_{lang}")), lang) for lang in ("de", "fr", "it")
                               if clean(r.get(f"role_{lang}"))), ("", ""))
            if not key:
                continue
            entry = standard.setdefault(key, {"id": key, "count": 0})
            entry["count"] += 1
            for language in LANGUAGES:
                entry.setdefault(language, clean(r.get(f"role_harmonized_{language}")) or None)
            # a standard role is listed also when no parliament has a name of its own for it
            if name and r.get("body_key"):
                seen[(str(r["body_key"]), name, lang, key)] += 1
    best: dict[tuple[str, str], tuple[int, str, str]] = {}
    for (body, name, lang, key), count in seen.items():
        if count > best.get((body, name.lower()), (0, "", ""))[0]:
            best[(body, name.lower())] = (count, name, lang, key)
    names = [{"body": body, "name": name, "lang": lang, "standard": key}
             for (body, _), (_, name, lang, key) in best.items()]
    standards_out = [{"id": e["id"], **{language: e.get(language) for language in LANGUAGES}, "count": e["count"]}
                     for e in sorted(standard.values(), key=lambda e: -e["count"])]
    return standards_out, sorted(names, key=lambda e: (e["body"], e["name"].lower())), len(seen) - len(names)


def write(data: dict) -> None:
    """One row per line, so a newer stem shows as changed lines."""
    lines = ["{", f'  "source": {json.dumps(data["source"], ensure_ascii=False)},',
             f'  "fetched": {json.dumps(data["fetched"])},']
    if "roles" in data:
        lines.append(f'  "roles": {json.dumps(data["roles"], ensure_ascii=False)},')
    lines.append('  "lists": {')
    names = list(data["lists"])
    for name in names:
        lines.append(f'    "{name}": {{')
        for part in ("standards", "names"):
            rows = data["lists"][name][part]
            lines.append(f'      "{part}": [')
            lines.extend("        " + json.dumps(r, ensure_ascii=False) + ("," if i + 1 < len(rows) else "")
                         for i, r in enumerate(rows))
            lines.append("      ]" + ("," if part == "standards" else ""))
        lines.append("    }" + ("," if name != names[-1] else ""))
    lines.extend(["  }", "}"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    held = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else {"lists": {}}
    if argv[:1] == ["--roles"] and len(argv) == 2:
        if not held["lists"]:
            print("no vocabulary file yet: run without --roles first", file=sys.stderr)
            return 1
        standard, names, twice = roles(Path(argv[1]))
        held["lists"]["roles"] = {"standards": standard, "names": names}
        held["roles"] = {"source": "the export of the contributors of OpenParlData (files.openparldata.ch/exports)",
                         "read": time.strftime("%Y-%m-%d")}
        write(held)
        print(f"{len(standard)} standard roles, {sum(1 for s in standard if s['de'])} with names in the four "
              f"languages; {len(names)} role names of {len({n['body'] for n in names})} parliaments, {twice} that "
              f"stood for two roles given to the more frequent one")
        return 0
    types = standards(fetch("affair_types_harmonized"), "affair_type_harmonized_")
    names, twice = type_names(fetch("affair_type_mapping"))
    events = standards(fetch("event_texts_harmonized"), "event_text_harmonized_")
    groups = standards(fetch("group_types_harmonized"), "group_type_harmonized_")
    write({
        "source": "admin panel of OpenParlData (admin.openparldata.ch), the lists as a visitor reads them",
        "fetched": time.strftime("%Y-%m-%d"),
        "lists": {
            "types": {"standards": types, "names": names},
            "events": {"standards": events, "names": []},
            "groups": {"standards": groups, "names": []},
            # the roles come from the export, not from the panel: a new stem keeps the ones the file has
            **({"roles": held["lists"]["roles"]} if "roles" in held["lists"] else {}),
        },
        **({"roles": held["roles"]} if "roles" in held else {}),
    })
    with_type = sum(1 for n in names if n["standard"] is not None)
    ways: dict[str, set] = {}
    for n in names:
        ways.setdefault(n["name"].lower(), set()).add(n["standard"])
    apart = sum(1 for s in ways.values() if len(s) > 1)
    print(f"{len(types)} harmonised types; {len(names)} type names of {len({n['body'] for n in names})} parliaments, "
          f"{with_type} with a harmonised type, {twice} left out as doubles; {apart} of {len(ways)} names stand for "
          f"another type in another parliament; {len(events)} event names; {len(groups)} kinds of groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
