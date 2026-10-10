"""Tells who the persons of an affair are. Every contributor a document names is looked up in the register of
that document's parliament (docket.store.register). Found as exactly one person, the entry gets the id
OpenParlData gives that person, with a place of its own in the root sources: derived from the name, and for a
person to look at when the name was found by its last name alone or with one character off. A name no known
person carries, standing literally in the document, is given to the register to learn.

The name itself is never changed here: what stands in the document stays, the id says who is meant.
"""

from __future__ import annotations

from docket.store.base import Store
from docket.store.register import Register


def link_persons(record: dict, parliaments: dict[int, str], names: dict[int, str], store: Store,
                 stop: set[str]) -> dict[str, list[dict]]:
    """Looks up the contributors of an affair that came from its documents; `parliaments` and `names` give
    the parliament's key and the name per document id. Returns per document name what became of every name:
    {value, name, how, person?, origin?, id?, seen?}."""
    data = (record.get("contributors") or {}).get("data") or []
    registers: dict[str, Register] = {}
    report: dict[str, list[dict]] = {}
    for i, entry in enumerate(data):
        source = entry.get("source")
        if not isinstance(source, dict) or not entry.get("fullname") or entry.get("person_id"):
            continue
        doc = source.get("doc")
        body = parliaments.get(doc, "")
        line = {"value": entry["fullname"], "how": "no parliament"}
        report.setdefault(names.get(doc, str(doc)), []).append(line)
        if not body:
            continue
        register = registers.get(body) or registers.setdefault(body, Register(store, body))
        match = register.find(entry["fullname"])
        line.update({"name": match.name, "how": match.how})
        person = match.person
        if person is not None:
            line.update({"person": person["label"], "origin": person.get("origin")})
            ids = person.get("ids") or []
            if len(ids) == 1:
                entry["person_id"] = line["id"] = ids[0]
                place = {"path": f"contributors.data.{i}.person_id", "doc": doc, "block": source.get("block"),
                         "how": "derived"}
                if match.how != "exact":
                    place["approve"] = True
                record.setdefault("sources", []).append(place)
        elif match.how == "none" and source.get("how") == "literal":
            row = register.learn(entry["fullname"], names.get(doc, str(doc)), stop)
            if row is not None:
                line.update({"origin": row["origin"], "seen": len(row.get("documents") or [])})
    return report
