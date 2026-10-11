"""The rows: what was found in a document, one row per value, said in terms that hold for any target JSON.

A record places a value under the key its JSON happens to use; a row says what the value is. Every answer of
the model that became a value gets a row with its entity (a person, a date, an identifier), the role under it,
the field that asked for it, the value as read, and where it stands: the page and the box of its block. The
block's id is kept as a reference into the document's blocks and counts only inside that document; over
documents a value is found by entity and value. What the model answered and what did not hold gets a row as
well, without a place, so that a dropped answer can be looked at later.

A row: {doc, n, entity, role, field, entry, value, state, how, block, page, box}. `n` numbers the rows of the
document in the order of the fields and their values; `entry` is the value's position among the values of its
field, by which the fields of one list entry belong together (a name and its party); `state` is placed or
dropped; `how` is how the value was found, or why it was dropped; `box` is [x, y, width, height] in the
pixels of the page.

The blocks themselves stay with the document in its record; the rows point into them.

What a person decides about a value is kept at its row, not in the record: `decisions`, each with the review as
the record shows it and, after a change, the value that counts now; `value` stays what was read. The record
follows the rows. Where a row's value sits in the record of its affair is noted beside it when the affair is
built (`affair`, `places`: the path of the source and of the value) and written anew with every build, so a
decision finds its value again after a new run and in a record of another shape. One read value can sit in
several entries (a party given once for three names); a decision then names the entry it was made on by the
row that made the entry (`of`).

A second opinion on where a field stands (docket.fields.second) leaves its word at the row as well: `second`
says which block it named and whether the value stands there, `approve` whether a person should look after
that, and a value it found where the model found none is a row of its own with `by`.

What a lookup found for the value stands at the row too (`match`): the standard name of a category, the person
a name was told as, the parliament a body was told as. Where a lookup puts something of its own into the
record, the id of a person, that place belongs to the row of the name as its part "id", and a decision on it
is kept there like any other.
"""

from __future__ import annotations

import copy
import time

from docket.affair.merge import Document, merge
from docket.affair.persons import person_places
from docket.affair.validator import Contract
from docket.document.response import whole
from docket.fields.fields import Fields
from docket.fields.placer import day, find_block, get_at, set_at
from docket.store.base import Store
from docket.store.vocabulary import Vocabulary

PLACED = "placed"
DROPPED = "dropped"
# the name the kind of a document goes by among the rows: it is no field of the fields file
KIND = "kind"


def rows_of(doc: str, report: dict[str, dict], fields: Fields, body: list[dict],
            kind: dict | None = None) -> list[dict]:
    """The rows of a document from its fields report (what the model answered, per field) and its blocks.
    With `kind`, what the run found the document itself to be ({kind, block}) becomes a row as well: a
    category about the document, not the value of a field, for a person to look at."""
    rows: list[dict] = []
    for name, answer in report.items():
        f = fields.fields.get(name)
        if f is None:
            continue
        items = answer.get("items") or []
        if not items and answer.get("value") not in (None, "") and answer.get("state") != "empty":
            # an answer that became no value at all (too short, not of the form): kept with what it failed on
            items = [{"value": answer["value"], "block": None, "how": answer.get("state")}]
        for entry, item in enumerate(items):
            placed = item.get("block") is not None
            block = find_block(item["block"], body) if placed else None
            rows.append({
                "doc": doc,
                "n": len(rows),
                "entity": f.entity,
                "role": f.role,
                "field": name,
                "entry": entry,
                "value": item["value"],
                "state": PLACED if placed else DROPPED,
                "how": item.get("how") or ("literal" if placed else ""),
                "block": item.get("block"),
                "page": block.get("page") if block else None,
                "box": [block.get(k) for k in ("x", "y", "width", "height")] if block else None,
            })
    if kind and kind.get("kind"):
        block = find_block(kind.get("block") or "b1", body)
        rows.append({
            "doc": doc, "n": len(rows), "entity": "category", "role": "kind", "field": KIND, "entry": 0,
            "value": kind["kind"], "state": PLACED, "how": "derived", "block": kind.get("block") or "b1",
            "page": block.get("page") if block else None,
            "box": [block.get(k) for k in ("x", "y", "width", "height")] if block else None,
            "about": "document", "approve": True,
        })
    return rows


def blocks_of_document(store: Store, name: str, entry: dict | None = None) -> list[dict]:
    """The blocks of a stored document in reading order: as the store keeps them, else from the document's
    entry in the record of its affair (a store filled before the blocks were kept on their own)."""
    blocks = store.get_blocks(name)
    return blocks if blocks is not None else whole(entry)


def kind_of(rows: list[dict]) -> dict | None:
    """What the rows of a document say it is, as the merging takes it: {kind, block, n}; None when they do
    not say."""
    row = next((r for r in rows if r.get("about") == "document" and r["state"] == PLACED), None)
    return {"kind": row["value"], "block": row["block"], "n": row["n"]} if row else None


def values_from(rows: list[dict], numbered: bool = False) -> dict[str, list[dict]]:
    """The placed values per field as the placing takes them, from the rows of a document: the way back from
    the rows to the record. With `numbered` every value carries the number of its row, so that the placing can
    tell where the row went."""
    out: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda r: r["n"]):
        # what a row says about the document itself is no value of a field
        if row["state"] == PLACED and not row.get("about"):
            hit = {"value": row["value"], "block": row["block"], "how": row["how"]}
            # what a second opinion said about the look a value needs goes with it
            if "approve" in row:
                hit["approve"] = row["approve"]
            out.setdefault(row["field"], []).append({**hit, "n": row["n"]} if numbered else hit)
    return out


def set_places(rows: list[dict], affair: str, placed: list[dict]) -> None:
    """Notes at the rows of a document the affair they went into and where each sits in its record, from what
    the placing noted for this document."""
    at: dict[int, list[dict]] = {}
    for p in placed:
        at.setdefault(p["n"], []).append({"of": p["of"], "part": "", "source": p["source"], "path": p["path"]})
    for row in rows:
        row["affair"] = affair
        row["places"] = at.get(row["n"], [])


def value_id(row: dict, place: dict) -> str:
    """The id a value is known by in the review: its document and the number of its row, and where the row
    sits in the entry of another or stands for an id, that as well ("doc#4", "doc#4:2", "doc#4/id"). It holds
    whatever shape the record has; a new run numbers the rows anew."""
    of = "" if place.get("of") is None else f":{place['of']}"
    part = f"/{place['part']}" if place.get("part") else ""
    return f"{row['doc']}#{row['n']}{of}{part}"


def find_value(rows: list[dict], ident: str) -> tuple[dict, dict] | None:
    """The row and its place for the id of a value; None when no row carries it."""
    for row in rows:
        for place in row.get("places") or []:
            if value_id(row, place) == ident:
                return row, place
    return None


def place_of(rows: list[dict], source: str, path: str) -> tuple[dict, dict] | None:
    """The row and its place for a source and a value path of the record; None when no row sits there."""
    for row in rows:
        for place in row.get("places") or []:
            if place["source"] == source and place["path"] == path:
                return row, place
    return None


def set_matches(record: dict, rows: list[dict], fields: Fields, became: dict[str, list[dict]] | None = None,
                parliaments: dict[str, str] | None = None) -> None:
    """Notes at the rows what the lookups found, from the record of their affair: the standard name of a
    category, the person of a name with the place of the id the record got for it, the parliament of a body.
    `became` is what the person lookup tells per document name, `parliaments` the parliament's key per
    document name."""
    ids = {tuple(into): (name_at, id_key) for into, name_at, id_key in person_places(fields)}
    sources = {s.get("path"): i for i, s in enumerate(record.get("sources") or [])}
    for row in rows:
        f = fields.fields.get(row["field"])
        own = [p for p in row.get("places") or [] if p["of"] is None and p["part"] == ""]
        if f is None or not own:
            continue
        if f.lookup == "bodies" and (parliaments or {}).get(row["doc"]):
            row["match"] = {"key": parliaments[row["doc"]]}
        elif f.lookup == "vocabulary" and f.standard and get_at(record, f.standard.split(".")):
            row["match"] = {"standard": get_at(record, f.standard.split("."))}
        elif f.lookup == "register" and "[]" in f.path and tuple(f.path[:f.path.index("[]")]) in ids:
            entry = own[0]["source"].rsplit(".", 1)[0]
            id_path = entry + "." + ids[tuple(f.path[:f.path.index("[]")])][1]
            line = next((x for x in (became or {}).get(row["doc"], []) if x.get("value") == row["value"]), None)
            if line is not None:
                row["match"] = {k: v for k, v in line.items() if k != "value"}
            elif get_at(record, id_path.split(".")) is not None:
                row["match"] = {"id": get_at(record, id_path.split("."))}
            if id_path in sources:
                place = {"of": None, "part": "id", "source": f"sources.{sources[id_path]}", "path": id_path}
                row["places"] = [*[p for p in row["places"] if p["part"] != "id"], place]


def note_decision(row: dict, place: dict, review: dict, value) -> None:
    """Writes a person's decision at the row, for the place it was made on; an earlier one for the same place
    is replaced. `value` is the value that counts after a change, else None."""
    at = (place["of"], place["part"])
    kept = [d for d in row.get("decisions") or [] if (d.get("of"), d.get("part", "")) != at]
    row["decisions"] = [*kept, {"of": at[0], "part": at[1], "review": copy.deepcopy(review), "value": value,
                                "seq": time.time_ns()}]


def carry_decisions(old: list[dict], new: list[dict]) -> int:
    """The decisions of a document's earlier rows carried to the rows of a new run: a row is found again by
    field, value and block, else by field and value. Returns the number of decisions carried."""
    to: dict[int, dict] = {}
    taken: set[int] = set()
    for keys in (("field", "value", "block"), ("field", "value")):
        index: dict[tuple, list[dict]] = {}
        for row in new:
            index.setdefault(tuple(str(row[k]) for k in keys), []).append(row)
        for row in old:
            if row["n"] in to:
                continue
            match = next((r for r in index.get(tuple(str(row[k]) for k in keys), []) if r["n"] not in taken), None)
            if match is not None:
                to[row["n"]] = match
                taken.add(match["n"])
    count = 0
    for row in old:
        target = to.get(row["n"])
        if target is None:
            continue
        for d in row.get("decisions") or []:
            # a decision on the entry of another row needs that row again as well
            if d.get("of") is not None and d["of"] not in to:
                continue
            of = None if d.get("of") is None else to[d["of"]]["n"]
            target.setdefault("decisions", []).append({**copy.deepcopy(d), "of": of})
            count += 1
    return count


def adopt(record: dict, rows: list[dict]) -> int:
    """Takes into the rows the reviews the record holds at their places and the rows do not know: decisions
    from before the rows held them. Returns the count."""
    # a source some row's decision already stands for is known, also when the values of an entry share it
    known = {p["source"] for row in rows for d in row.get("decisions") or []
             for p in row.get("places") or [] if (p["of"], p["part"]) == (d.get("of"), d.get("part", ""))}
    count = 0
    for row in rows:
        for place in row.get("places") or []:
            if place["of"] is not None or place["source"] in known:
                continue
            source = get_at(record, place["source"].split("."))
            if not isinstance(source, dict) or not isinstance(source.get("review"), dict):
                continue
            changed = source["review"].get("decision") == "changed"
            value = get_at(record, place["path"].split(".")) if changed else None
            # before everything decided since
            row.setdefault("decisions", []).append({"of": None, "part": place["part"], "value": value, "seq": 0,
                                                    "review": copy.deepcopy(source["review"])})
            known.add(place["source"])
            count += 1
    return count


def follow(record: dict, rows: list[dict]) -> tuple[dict, int]:
    """A copy of the record with every decision of the rows at its place: the review at the source and, after
    a change, the value. In the order the decisions were made, since the values of one entry share a source.
    Returns the record and the number of decisions that found their place."""
    out = copy.deepcopy(record)
    todo = [(d.get("seq", 0), row["doc"], row["n"], row, d) for row in rows for d in row.get("decisions") or []]
    count = 0
    for _, _, _, row, d in sorted(todo, key=lambda t: t[:3]):
        at = (d.get("of"), d.get("part", ""))
        place = next((p for p in row.get("places") or [] if (p["of"], p["part"]) == at), None)
        source = get_at(out, place["source"].split(".")) if place else None
        if not isinstance(source, dict):
            # the value has no place in this record
            continue
        source["review"] = copy.deepcopy(d["review"])
        if d["review"].get("decision") == "changed" and d.get("value") is not None:
            set_at(out, place["path"].split("."), d["value"])
        count += 1
    return out, count


def fill_rows(store: Store, fields: Fields, contract: Contract, types: dict[str, dict]) -> int:
    """Writes the rows of every stored document from its fields report and its blocks, without a model: for a
    store that was filled before the rows existed. The affair is built once more beside the stored one to tell
    where every row sits, and the reviews the record holds are taken into the rows. Returns the number of
    documents."""
    vocabulary = Vocabulary(store.get_vocabulary())
    date_field = fields.by_role().get("date", "")
    count = 0
    for affair in store.list_affairs():
        entries = {e.get("id"): e for e in (affair["record"].get("docs") or {}).get("data", [])}
        documents, rows_of_doc, became = [], {}, {}
        for document in affair["documents"]:
            name, entry = document["name"], entries.get(document["id"])
            report = store.get_fields(name)
            if report is None or entry is None:
                continue
            # what became of every name stands in the report since the run that looked it up
            became[name] = report.get("persons") or []
            # the kind only where the stored record holds it: an older run did not carry it into the affair
            kind = report.get("kind") if entry.get("article-type") else None
            blocks = blocks_of_document(store, name, entry)
            if store.get_blocks(name) is None:
                store.put_blocks(name, blocks)
            rows = rows_of(name, report["fields"], fields, blocks, kind)
            values = values_from(rows, numbered=True)
            date = next((day(i["value"]) for i in values.get(date_field, [])), "")
            parliament = str((report.get("identity") or {}).get("body") or "")
            documents.append(Document(document["id"], name, document.get("pages") or 1, blocks,
                                      values, affair["key"], date, parliament, kind_of(rows)))
            rows_of_doc[document["id"]] = rows
        placed: list[dict] = []
        merge(documents, fields, contract, types, vocabulary, placed)
        together = []
        for d in documents:
            rows = rows_of_doc[d.id]
            set_places(rows, affair["key"], [p for p in placed if p["doc"] == d.id])
            together.extend(rows)
        set_matches(affair["record"], together, fields, became, {d.name: d.parliament for d in documents})
        for d in documents:
            carry_decisions(store.get_rows(d.name), rows_of_doc[d.id])
        adopt(affair["record"], together)
        for d in documents:
            store.put_rows(d.name, rows_of_doc[d.id])
            count += 1
    return count
