"""Tells who the persons of an affair are. Every person a document names (which values are persons, the fields
file says) is looked up in the register of that document's parliament (docket.store.register). Found as
exactly one person, the entry gets the id OpenParlData gives that person, with a place of its own in the root
sources: derived from the name, and for a person to look at when the name was found by its last name alone or
with one character off. A name no known person carries, standing literally in the document, is given to the
register to learn.

The name itself is never changed here: what stands in the document stays, the id says who is meant.
"""

from __future__ import annotations

from docket.fields.fields import Fields
from docket.fields.placer import get_at
from docket.store.base import Store
from docket.store.register import Register

# without a fields file: the list of the names, the name in an entry, the key of the id, as OpenParlData has them
CONTRIBUTORS = [(["contributors", "data"], ["fullname"], "person_id")]


def person_places(fields: Fields | None) -> list[tuple[list[str], list[str], str]]:
    """Where the record holds persons to look up, from the fields file: every list a field with the register
    behind it goes into and names a key for the id in; per list its path, the name's path in an entry and that
    key."""
    if fields is None:
        return CONTRIBUTORS
    out: list[tuple[list[str], list[str], str]] = []
    for f in fields.fields.values():
        if f.lookup == "register" and f.id_key and "[]" in f.path:
            at = f.path.index("[]")
            place = (f.path[:at], f.path[at + 1:], f.id_key)
            if place not in out:
                out.append(place)
    return out


def link_persons(record: dict, parliaments: dict[int, str], names: dict[int, str], store: Store,
                 stop: set[str], fields: Fields | None = None) -> dict[str, list[dict]]:
    """Looks up the persons of an affair that came from its documents; `parliaments` and `names` give the
    parliament's key and the name per document id. Which entries are persons and where their id goes is said
    by the fields file. Returns per document name what became of every name: {value, name, how, person?,
    origin?, id?, seen?}."""
    registers: dict[str, Register] = {}
    report: dict[str, list[dict]] = {}
    for into, name_at, id_key in person_places(fields):
        for i, entry in enumerate(get_at(record, into) or []):
            source = entry.get("source")
            printed = get_at(entry, name_at)
            if not isinstance(source, dict) or not printed or entry.get(id_key):
                continue
            doc = source.get("doc")
            body = parliaments.get(doc, "")
            line = {"value": printed, "how": "no parliament"}
            report.setdefault(names.get(doc, str(doc)), []).append(line)
            if not body:
                continue
            register = registers.get(body) or registers.setdefault(body, Register(store, body))
            match = register.find(printed)
            line.update({"name": match.name, "how": match.how})
            person = match.person
            if person is not None:
                line.update({"person": person["label"], "origin": person.get("origin")})
                ids = person.get("ids") or []
                if len(ids) == 1:
                    entry[id_key] = line["id"] = ids[0]
                    place = {"path": ".".join([*into, str(i), id_key]), "doc": doc, "block": source.get("block"),
                             "how": "derived"}
                    if match.how != "exact":
                        place["approve"] = True
                    record.setdefault("sources", []).append(place)
            elif match.how == "none" and source.get("how") == "literal":
                row = register.learn(printed, names.get(doc, str(doc)), stop)
                if row is not None:
                    line.update({"origin": row["origin"], "seen": len(row.get("documents") or [])})
    return report
