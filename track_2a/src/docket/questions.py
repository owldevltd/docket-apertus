"""Three questions across the parliaments, answered from the rows a store holds; without the model.

OpenParlData cannot answer them from its own data: who backs an affair besides its first author is not held
for every parliament, a document has no kind there, and what a parliament prints on its affairs is known only
from the documents themselves.

    backing   the persons a document names as authors and co-signers of an affair, each once; with the exports
              of OpenParlData beside it, the number of persons held there for the same affair
    kinds     what the documents of a parliament were found to be
    printed   per field, in how many documents of a parliament a value was found on the page

The parliament of a document is the one the run found for it. Where the documents were drawn from OpenParlData,
the list they were drawn with tells parliament and affair for certain, and is taken first.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from statistics import mean, median

from docket.affair.identity import number
from docket.fields.fields import Fields
from docket.store.base import Store
from docket.store.register import key_of
from docket.store.rows import PLACED

ROLES = ("author", "cosign")
# the roles under which OpenParlData holds the persons who back an affair
HELD_AS = ("author", "cosign", "co-signer")
# a parliament gets a column of its own in the last table from this many documents on
OWN_COLUMN = 5


def collect(store: Store, fields: Fields, drawn: dict[str, dict] | None = None) -> list[dict]:
    """One entry per stored document: its affair, its parliament, the persons named, its kind, the fields
    found on its pages. `drawn` tells by the name of a document its parliament and its affair at OpenParlData
    ({body, affair}), where the documents came from there."""
    documents = []
    for affair in store.list_affairs():
        for d in affair["documents"]:
            rows = [r for r in store.get_rows(d["name"]) if r["state"] == PLACED]
            identity = (store.get_fields(d["name"]) or {}).get("identity") or {}
            source = (drawn or {}).get(d["name"]) or {}
            documents.append({
                "affair": affair["key"], "name": d["name"], "theirs": source.get("affair"),
                "body": str(source.get("body") or identity.get("body") or ""), "told": bool(identity.get("body")),
                "persons": {key_of(r["value"]) for r in rows if r.get("role") in ROLES} - {""},
                "kind": next((r["value"] for r in rows if r.get("about") == "document"), None),
                "number": number(next((str(r["value"]) for r in rows if r.get("role") == "number"), "")),
                "fields": {r["field"] for r in rows if r["field"] in fields.fields},
            })
    return documents


def held(affairs_export: Path, contributors_export: Path, documents: list[dict]) -> dict[str, int]:
    """How many persons OpenParlData holds for the affairs of these documents, by the key of the affair here.
    An affair is found there by the id the documents were drawn with, else by parliament and number. From a
    row of the affairs only parliament, number and id are read, from a row of the contributors the affair, the
    role and the id of the person; nothing of it is kept but the count."""
    ids = {d["theirs"]: d["affair"] for d in documents if d["theirs"]}
    by_number = {(d["body"], d["number"]): d["affair"] for d in documents if not d["theirs"] and d["number"]}
    if by_number:
        with gzip.open(affairs_export, "rt", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                at = (str(row.get("body_key") or ""), number(str(row.get("number") or "")))
                if at[1] and at in by_number:
                    ids.setdefault(row["id"], by_number[at])
    persons: dict[str, set] = {key: set() for key in ids.values()}
    with gzip.open(contributors_export, "rt", encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            key = ids.get(row.get("affair_id"))
            if key is not None and row.get("type") == "person" and row.get("role_harmonized") in HELD_AS:
                persons[key].add(row.get("person_id") or row.get("fullname"))
    return {key: len(found) for key, found in persons.items()}


def label(body: str, bodies: dict[str, dict]) -> str:
    """A parliament as the tables name it: the place with its council, since a canton and its capital share
    the name ("Luzern, Kantonsrat" and "Luzern, Grosser Stadtrat")."""
    known = bodies.get(body) or {}
    return ", ".join(x for x in (known.get("name"), known.get("parliament")) if x) or body or "not told"


def answers(documents: list[dict], fields: Fields, bodies: dict[str, dict],
            at_openparldata: dict[str, int] | None = None) -> dict:
    """The three answers per parliament, the parliaments with the most documents first."""
    order: dict[str, list[dict]] = {}
    for d in documents:
        order.setdefault(d["body"], []).append(d)
    parliaments = sorted(order, key=lambda body: (-len(order[body]), body))

    backing, kinds, printed = [], [], []
    for body in parliaments:
        docs = order[body]
        affairs: dict[str, set] = {}
        for d in docs:
            affairs.setdefault(d["affair"], set()).update(d["persons"])
        counts = [len(persons) for persons in affairs.values()]
        row = {"parliament": label(body, bodies), "affairs": len(affairs), "named": sum(1 for c in counts if c),
               "mean": mean(counts), "median": median(counts), "most": max(counts)}
        if at_openparldata is not None:
            pairs = [(len(persons), at_openparldata[key]) for key, persons in affairs.items()
                     if key in at_openparldata]
            row.update({"found": len(pairs), "theirs": mean(t for _, t in pairs) if pairs else None,
                        "more": sum(1 for o, t in pairs if o > t), "same": sum(1 for o, t in pairs if o == t),
                        "fewer": sum(1 for o, t in pairs if o < t)})
        backing.append(row)
        told: dict[str, int] = {}
        for d in docs:
            told[d["kind"] or ""] = told.get(d["kind"] or "", 0) + 1
        kinds.append({"parliament": label(body, bodies), "documents": len(docs), "kinds": told})
        printed.append({"parliament": label(body, bodies), "documents": len(docs),
                        "fields": {name: sum(1 for d in docs if name in d["fields"]) for name in fields.fields}})
    return {"documents": len(documents), "parliaments": len(parliaments), "backing": backing, "kinds": kinds,
            "printed": printed, "told": sum(1 for d in documents if d["told"])}


def markdown(found: dict) -> str:
    """The answers as three tables."""
    out = ["# Three questions across the parliaments", "",
           f"From the rows of {found['documents']} documents of {found['parliaments']} parliaments, without the "
           f"model. The run itself found the parliament of {found['told']} of the documents.",
           "", "## How many members back an affair?", "",
           "The persons a document names as authors and co-signers, each once, per affair."]
    theirs = any("found" in r for r in found["backing"])
    if theirs:
        out += ["Beside it what OpenParlData holds for the same affair, where parliament and number lead to one: "
                "the mean of the persons held there, and in how many affairs the documents name more, as many "
                "or fewer."]
    head = "| parliament | affairs | with names | mean | median | most |"
    out += ["", head + (" at OpenParlData | their mean | more | same | fewer |" if theirs else ""),
            "|---|" + "---:|" * (10 if theirs else 5)]
    for r in found["backing"]:
        line = (f"| {r['parliament']} | {r['affairs']} | {r['named']} | {r['mean']:.1f} | {r['median']:g} | "
                f"{r['most']} |")
        if theirs:
            mean_there = "–" if r.get("theirs") is None else f"{r['theirs']:.1f}"
            line += (f" {r.get('found', 0)} | {mean_there} | {r.get('more', 0)} | {r.get('same', 0)} | "
                     f"{r.get('fewer', 0)} |")
        out.append(line)

    names = sorted({k for r in found["kinds"] for k in r["kinds"] if k})
    out += ["", "## What kinds of documents hang on the affairs?", "",
            "What a run found every document to be.", "",
            "| parliament | documents | " + " | ".join(names) + " | not told |",
            "|---|---:|" + "---:|" * (len(names) + 1)]
    for r in found["kinds"]:
        out.append(f"| {r['parliament']} | {r['documents']} | " + " | ".join(str(r["kinds"].get(k, 0)) for k in names)
                   + f" | {r['kinds'].get('', 0)} |")

    own = [r for r in found["printed"] if r["documents"] >= OWN_COLUMN]
    out += ["", "## Which details does a parliament print at all?", "",
            "Per field: in how many documents a value was found on the page, in how many parliaments at least "
            "once, in how many in every document; then the documents of every parliament with at least "
            f"{OWN_COLUMN} of them.", "",
            "| field | documents | parliaments | in every document | " + " | ".join(
                f"{r['parliament']} ({r['documents']})" for r in own) + " |",
            "|---|---:|---:|---:|" + "---:|" * len(own)]
    fields = list(found["printed"][0]["fields"]) if found["printed"] else []
    for name in sorted(fields, key=lambda n: -sum(r["fields"][n] for r in found["printed"])):
        total = sum(r["fields"][name] for r in found["printed"])
        some = sum(1 for r in found["printed"] if r["fields"][name])
        every = sum(1 for r in found["printed"] if r["fields"][name] == r["documents"])
        out.append(f"| {name} | {total} | {some} | {every} | " + " | ".join(str(r["fields"][name]) for r in own) + " |")
    return "\n".join(out) + "\n"
