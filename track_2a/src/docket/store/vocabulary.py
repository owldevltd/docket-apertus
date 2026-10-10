"""The vocabularies: what a parliament calls a thing, and the standard name it stands for.

They start from the lists OpenParlData keeps (the stem, data/knowledge/vocabulary.json, fetched by
tools/vocabulary.py): per parliament the names of its affair types with the harmonised type, the harmonised
names of the events, the kinds of groups, and per parliament the names of the roles of those who take part
in an affair with the standard role. OpenParlData calls its harmonised types provisional, so the stem
is not code and not a fixed file: it lies in the store and can be changed there. A person sets another
standard for a name or adds a name the stem does not have; such a row says who and when, and keeps what the
stem said, so the difference can be seen and taken back. A newer stem replaces every row nobody changed, and
leaves the changed ones as they are.

A row: {list, body, name, label, standard, origin, fetched}. `list` is types, events, groups or roles; `body`
is the parliament's key at OpenParlData, empty for the standard names themselves; `name` is the label in small
letters with single spaces, the key of the row; `standard` is the standard name in four languages, or None
where the stem lists a name without one; `origin` is stem or person. The roles carry the word OpenParlData
knows a standard role by as well (`key`: author, cosign), since it names some of them by that word alone; a
field of the fields file names its role by it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from docket.store.base import Store, stamp

LISTS = ("types", "events", "groups", "roles")
LANGUAGES = ("de", "fr", "it", "en")


def key_of(label: str) -> str:
    """A label as the key of its row: small letters, single spaces."""
    return re.sub(r"\s+", " ", str(label or "")).strip().lower()


def load_stem(path: Path) -> dict | None:
    """The stem file, or None when the checkout has none."""
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def stem_rows(stem: dict) -> list[dict]:
    """The rows of a stem file as the store holds them: the standard names of every list (body empty), and
    the names of the parliaments with the standard each stands for."""
    rows = []
    for name in LISTS:
        part = (stem.get("lists") or {}).get(name) or {}
        by_id = {}
        for s in part.get("standards") or []:
            standard = {lang: s.get(lang) for lang in LANGUAGES}
            by_id[s.get("id")] = standard
            # a standard OpenParlData names by a word only (some of the roles) is known by that word
            label = s.get("de") or str(s["id"])
            row = {"list": name, "body": "", "name": key_of(label), "label": label, "standard": standard,
                   "origin": "stem", "fetched": stem.get("fetched")}
            for extra in ("wikidata", "count"):
                if s.get(extra) is not None:
                    row[extra] = s[extra]
            if isinstance(s.get("id"), str):
                row["key"] = s["id"]
            rows.append(row)
        for n in part.get("names") or []:
            row = {"list": name, "body": str(n["body"]), "name": key_of(n["name"]), "label": n["name"],
                   "lang": n.get("lang"), "standard": by_id.get(n.get("standard")), "origin": "stem",
                   "fetched": stem.get("fetched")}
            if isinstance(n.get("standard"), str):
                row["key"] = n["standard"]
            rows.append(row)
    return rows


def _key(row: dict) -> tuple[str, str, str]:
    return row["list"], row["body"], row["name"]


def sync(store: Store, stem: dict) -> dict[str, int]:
    """Brings the store's vocabulary up to a stem. Rows the store lacks are added; rows from an earlier stem
    are renewed, and removed when the stem dropped them. A row a person changed keeps its standard, only
    what the stem says about it is renewed beside it. Returns how many rows were added, got another standard
    (replaced), were removed, and were kept as a person set them; a second call with the same stem writes
    nothing."""
    held = {_key(r): r for r in store.get_vocabulary()}
    fresh = {_key(r): r for r in stem_rows(stem)}
    put, gone = [], []
    counts = {"added": 0, "replaced": 0, "removed": 0, "kept": 0}
    for key, row in fresh.items():
        old = held.get(key)
        if old is None:
            put.append(row)
            counts["added"] += 1
        elif old.get("origin") == "person":
            said = {"standard": row["standard"], "fetched": row["fetched"]}
            if old.get("stem") != said:
                put.append({**old, "stem": said})
            counts["kept"] += 1
        elif old != row:
            put.append(row)
            counts["replaced"] += 1 if old.get("standard") != row["standard"] else 0
    for key, old in held.items():
        if key in fresh:
            continue
        if old.get("origin") != "person":
            gone.append(old)
            continue
        # a name a person set stays when the stem does not have it; it then no longer says what the stem said
        counts["kept"] += 1
        if "stem" in old:
            put.append({k: v for k, v in old.items() if k != "stem"})
    counts["removed"] = len(gone)
    if put:
        store.put_vocabulary(put)
    if gone:
        store.drop_vocabulary(gone)
    return counts


class Vocabulary:
    """The rows of a store, for looking up and for changing. `rows` is the stored list."""

    def __init__(self, rows: list[dict]):
        self.rows = {_key(r): r for r in rows}

    def row(self, name_of_list: str, body: str, label: str) -> dict | None:
        """The row of a name in a parliament's list, or None when the parliament does not list it."""
        return self.rows.get((name_of_list, str(body), key_of(label)))

    def standards(self, name_of_list: str) -> list[dict]:
        """The standard names of a list."""
        return [r for (kind, body, _), r in self.rows.items() if kind == name_of_list and body == ""]

    def names(self, name_of_list: str | None = None, body: str | None = None) -> list[dict]:
        """The rows of a list, of a parliament, or all, in the order of list, parliament and name."""
        rows = [r for (kind, b, _), r in self.rows.items()
                if (name_of_list is None or kind == name_of_list) and (body is None or b == str(body))]
        return sorted(rows, key=_key)

    def set(self, name_of_list: str, body: str, label: str, standard: str | None, by: str) -> dict:
        """A person says what a name of a parliament stands for: one of the list's standard names (in any of
        its languages), or None for a name that has no standard. Returns the row to store; ValueError when
        the list, the parliament or the standard is not known."""
        if name_of_list not in LISTS or not str(body).strip() or not key_of(label):
            raise ValueError(f"a row needs a list ({', '.join(LISTS)}), a parliament and a name")
        found = chosen = None
        if standard is not None:
            wanted = key_of(standard)
            chosen = next((s for s in self.standards(name_of_list)
                           if wanted in (key_of(v) for v in [*s["standard"].values(), s.get("key")] if v)), None)
            if chosen is None:
                raise ValueError(f"{standard!r} is no standard name of the list {name_of_list}")
            found = chosen["standard"]
        key = (name_of_list, str(body).strip(), key_of(label))
        old = self.rows.get(key)
        row = {"list": key[0], "body": key[1], "name": key[2], "label": (old or {}).get("label") or str(label).strip(),
               "standard": found, "origin": "person", "by": by, "at": stamp()}
        if old is not None and old.get("lang"):
            row["lang"] = old["lang"]
        if chosen is not None and chosen.get("key"):
            row["key"] = chosen["key"]
        # what the stem said stays beside the person's word
        if old is not None and old.get("origin") == "stem":
            row["stem"] = {"standard": old.get("standard"), "fetched": old.get("fetched")}
        elif old is not None and "stem" in old:
            row["stem"] = old["stem"]
        self.rows[key] = row
        return row

    def reset(self, name_of_list: str, body: str, label: str) -> tuple[dict | None, dict | None]:
        """Takes a person's word back: the row says again what the stem said, or goes when the stem never had
        it. Returns (the row to store, the row to drop), each None when there is nothing to do."""
        key = (name_of_list, str(body), key_of(label))
        old = self.rows.get(key)
        if old is None or old.get("origin") != "person":
            return None, None
        if "stem" not in old:
            del self.rows[key]
            return None, old
        row = {k: v for k, v in old.items() if k not in ("by", "at", "stem", "standard", "origin")}
        row.update({"standard": old["stem"]["standard"], "origin": "stem", "fetched": old["stem"]["fetched"]})
        self.rows[key] = row
        return row, None
