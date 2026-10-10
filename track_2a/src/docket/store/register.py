"""The register: the persons of the parliaments, to tell who a printed name is.

It starts from the persons OpenParlData keeps (tools/register.py loads them into the store: id, name,
parliament, party, nothing private). A name from a document is looked up among the persons of its own
parliament only: exactly, in either order of first and last name; by the last name alone, as some parliaments
print it; or with one character off, since a reading sometimes takes a letter for another. It counts as found
only when exactly one person fits. Tried on 10 October 2026 with every name of the register changed by one
character: in the own parliament 95.5 % come back as the right person alone and 4.5 % with others beside, three
of 26 934 as someone else; searched over all parliaments 85.7 % alone.

The register also learns. A name that is no known person, stands literally in the document and looks like a
name is kept as a candidate with the documents it was seen in; from the third document on it is taken into
the register as learnt (set by the project lead, 10 October 2026). A learnt person has no id at OpenParlData;
it serves to recognise the name the next time, also with one character off. A newer list from OpenParlData
replaces what came from there and leaves what was learnt; a learnt person the new list knows becomes theirs.

A row: {body, key, label, first, last, ids, party, origin, ...}. `body` is the parliament's key, `key` the name
in small letters as "first last"; `origin` is stem, learned or candidate.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from docket.store.base import Store, stamp

# a name is taken into the register when it was seen in this many documents
LEARN_AT = 3

# one character off counts only for names of at least this many characters: in a short name one character is
# another name ("Graf", "Gras"). Set by the assistant, open.
NEAR_FROM = 8

# titles and forms of address in front of a name are not part of it
TITLES = {"dr", "prof", "lic", "iur", "med", "phil", "dipl", "ing", "me", "avv", "dott", "herr", "frau", "m", "mme",
          "sig", "on"}

# what follows a name on the page and is not the name: the party or the place in brackets, a place or a party
# after a comma, further signatories after "and"
TAIL = re.compile(r"\([^)]*\)?|[,;].*$|\s(?:und|et|e)\s.*$")


def clean_name(text: str) -> str:
    """A printed name without what follows it ("Armin Feldhaus, Uster", "Linus Strehl (SVP)", "Luca
    Tamborini PLR") and without a title in front."""
    words = re.sub(r"\s+", " ", TAIL.sub(" ", str(text or ""))).strip(" .-–)(").split()
    while len(words) > 1 and words[0].lower().strip(".") in TITLES:
        words = words[1:]
    # a short word in capitals behind two names is the party
    if len(words) > 2 and words[-1].isupper() and 2 <= len(words[-1]) <= 4 and not words[-2].isupper():
        words = words[:-1]
    return " ".join(words)


def key_of(name: str) -> str:
    """A name as it is compared: small letters, letters and hyphens only, single spaces."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s'-]", " ", str(name or "").lower())).strip()


def near(a: str, b: str) -> bool:
    """At most one character apart: replaced, missing or one too many."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i + 1:] == b[i + 1:] if len(a) == len(b) else a[i:] == b[i + 1:]


def _cuts(key: str) -> set[str]:
    """The key and every form of it with one character less: two keys at most one character apart share one."""
    return {key} | {key[:i] + key[i + 1:] for i in range(len(key))}


@dataclass
class Match:
    """What a name was found as: exact, surname, near, several (more than one person fits) or none; `rows`
    are the persons that fit, `name` the name as it was looked up."""

    how: str
    name: str = ""
    rows: list[dict] = field(default_factory=list)

    @property
    def person(self) -> dict | None:
        return self.rows[0] if self.how in ("exact", "surname", "near") else None


class Persons:
    """The persons of one parliament, for looking up printed names. `rows` are its rows of the register;
    candidates are not looked up."""

    def __init__(self, rows: list[dict]):
        self.rows = [r for r in rows if r.get("origin") != "candidate"]
        self.exact: dict[str, list[dict]] = {}
        self.last: dict[str, list[dict]] = {}
        self.cuts: dict[str, list[tuple[str, dict]]] = {}
        for r in self.rows:
            first, last = key_of(r.get("first", "")), key_of(r.get("last", ""))
            keys = {f"{first} {last}", f"{last} {first}"} if first and last else {key_of(r.get("label", ""))}
            for key in keys - {""}:
                self.exact.setdefault(key, []).append(r)
                for c in _cuts(key):
                    self.cuts.setdefault(c, []).append((key, r))
            if last:
                self.last.setdefault(last, []).append(r)

    def find(self, printed: str) -> Match:
        name = clean_name(printed)
        key = key_of(name)
        if not key:
            return Match("none", name)
        hits = self.exact.get(key)
        how = "exact"
        if not hits and " " not in key:
            hits, how = self.last.get(key), "surname"
        if not hits and len(key) >= NEAR_FROM and " " in key:
            found = {id(r): r for c in _cuts(key) for other, r in self.cuts.get(c, ()) if near(key, other)}
            hits, how = list(found.values()), "near"
        if not hits:
            return Match("none", name)
        # one row can stand for two persons of the same name; then nobody is found
        if len(hits) > 1 or len(hits[0].get("ids") or []) > 1:
            return Match("several", name, list(hits))
        return Match(how, name, list(hits))


def looks_like_name(name: str, stop: set[str]) -> bool:
    """Whether a cleaned value can be a person: at least two words, every one beginning with a letter and
    longer than one letter or an initial, none of them the word of an organ ("Kommission", "Regierungsrat")."""
    words = name.split()
    if len(words) < 2 or len(words) > 5:
        return False
    for w in words:
        low = w.lower().strip(".")
        # the word of an organ, alone or at the end of a compound ("Gemeinderat", "Finanzkommission")
        organ = low in stop or any(low.endswith(s) and len(low) >= len(s) + 4 for s in stop)
        if not w[0].isalpha() or any(ch.isdigit() for ch in w) or organ:
            return False
    return any(len(w.strip(".")) > 2 for w in words)


def stop_words(vocabulary_rows: list[dict]) -> set[str]:
    """The words that name an organ, from the standard names of the groups in the vocabulary ("Kommission",
    "Fraktion", "Regierung"), in every language held there."""
    out: set[str] = set()
    for r in vocabulary_rows:
        if r.get("list") == "groups" and r.get("body") == "":
            for text in (r.get("standard") or {}).values():
                out |= {w for w in re.findall(r"[^\W\d_]{3,}", str(text or "").lower())}
    return out


class Register:
    """The register of one parliament as the store holds it: its persons for looking up, and the learning."""

    def __init__(self, store: Store, body: str):
        self.store, self.body = store, body
        self.held = {r["key"]: r for r in store.get_register(body)} if body else {}
        self.persons = Persons(list(self.held.values()))

    def find(self, printed: str) -> Match:
        return self.persons.find(printed) if self.body else Match("none", clean_name(printed))

    def learn(self, printed: str, document: str, stop: set[str]) -> dict | None:
        """Notes a name no known person of the parliament carries. It becomes a candidate with the document
        it was seen in, and a learnt person from the LEARN_AT-th document on. Returns the row written, or
        None when the value does not look like a name."""
        name = clean_name(printed)
        if not self.body or not looks_like_name(name, stop):
            return None
        key = key_of(name)
        row = self.held.get(key)
        if row is None:
            row = {"body": self.body, "key": key, "label": name, "origin": "candidate", "documents": [],
                   "since": stamp()}
        if row.get("origin") != "candidate":
            return row
        if document in row["documents"]:
            return row
        row["documents"].append(document)
        if len(row["documents"]) >= LEARN_AT:
            words = name.split()
            row.update({"origin": "learned", "learned": stamp(), "first": " ".join(words[:-1]), "last": words[-1],
                        "ids": []})
            self.persons = Persons([*(r for r in self.held.values() if r is not row), row])
        self.held[key] = row
        self.store.put_register([row])
        return row


def sync(store: Store, persons: list[dict], fetched: str) -> dict[str, int]:
    """Brings the register up to a list of persons from OpenParlData ({id, body, first, last, party}, the id
    being the person's primary one). Rows from an earlier list are replaced or, when the list dropped them,
    removed; what was learnt stays, and a learnt person or a candidate the list now knows becomes a row of
    the list with what was seen kept beside it. Returns the counts."""
    fresh: dict[str, dict[str, dict]] = {}
    for p in persons:
        first, last = str(p.get("first") or "").strip(), str(p.get("last") or "").strip()
        key = key_of(f"{first} {last}")
        if not p.get("body") or not last or not key:
            continue
        row = fresh.setdefault(str(p["body"]), {}).setdefault(key, {
            "body": str(p["body"]), "key": key, "label": f"{first} {last}".strip(), "first": first, "last": last,
            "ids": [], "origin": "stem", "fetched": fetched,
        })
        if p.get("id") is not None and p["id"] not in row["ids"]:
            row["ids"].append(p["id"])
        if p.get("party") and not row.get("party"):
            row["party"] = p["party"]
    counts = {"added": 0, "replaced": 0, "removed": 0, "kept": 0}
    for body in sorted(set(fresh) | set(store.register_bodies())):
        held = {r["key"]: r for r in store.get_register(body)}
        put, gone = [], []
        for key, row in fresh.get(body, {}).items():
            old = held.get(key)
            if old is None:
                put.append(row)
                counts["added"] += 1
            elif old.get("origin") != "stem":
                put.append({**row, "seen": {k: old[k] for k in ("documents", "since", "learned") if k in old}})
                counts["replaced"] += 1
            else:
                new = {**row, **({"seen": old["seen"]} if "seen" in old else {})}
                if old != new:
                    put.append(new)
                    counts["replaced"] += 1 if old.get("ids") != row["ids"] else 0
        for key, old in held.items():
            if key in fresh.get(body, {}):
                continue
            if old.get("origin") == "stem":
                gone.append(old)
            else:
                counts["kept"] += 1
        counts["removed"] += len(gone)
        if put:
            store.put_register(put)
        if gone:
            store.drop_register(gone)
    return counts
