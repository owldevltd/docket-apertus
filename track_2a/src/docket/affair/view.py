"""An affair as a record of another shape, from the same rows.

The store works on one contract; what it knows of an affair does not hang on that contract. The rows say what
was read, what a lookup found and what a person decided, and a fields file says where each of it goes. So a
second fields file with its own contract gives the same affair in another JSON, without reading a document
again: the values are placed as that file says, the standard name of a category and the id of a person go
where it names a place for them, a changed value comes in changed.

What Docket adds to a record of its own (the documents with their blocks, the places of the values, the
reviews) is left out where the other contract has no room for it; it stays in the store. A value a person
rejected is marked in a record that keeps the reviews, and left out of one that cannot show the mark.

A fields file for a view names the fields by the names they were read under; it can leave fields out, and it
cannot ask for what was never read.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable

from docket.affair.merge import Document, merge
from docket.affair.validator import Contract
from docket.fields.fields import Fields, has_room
from docket.fields.placer import day, get_at, set_at
from docket.store.base import Store
from docket.store.rows import blocks_of_document, follow, kind_of, set_places, values_from
from docket.store.vocabulary import Vocabulary

# what Docket adds to a record beyond the values
OWN = ("schema", "docs", "sources", "source")


def view(store: Store, key: str, fields: Fields, contract: Contract, types: dict[str, dict],
         answers: Iterable[str] = ()) -> dict | None:
    """The stored affair laid into the shape of this fields file and contract; None when the affair is not
    there or its documents have no rows."""
    data = store.get_affair(key)
    if data is None:
        return None
    entries = {e.get("id"): e for e in (data["record"].get("docs") or {}).get("data", [])}
    date_field = fields.by_role().get("date", "")
    documents, rows = [], {}
    for document in data["documents"]:
        # a copy: the rows are told where they sit in this record, the store keeps where they sit in its own
        mine = [copy.deepcopy(r) for r in store.get_rows(document["name"]) if r.get("affair") == key]
        if not mine:
            continue
        values = {n: hits for n, hits in values_from(mine, numbered=True).items() if n in fields.fields}
        date = next((day(i["value"]) for i in values.get(date_field, [])), "")
        report = store.get_fields(document["name"]) or {}
        body = blocks_of_document(store, document["name"], entries.get(document["id"]))
        documents.append(Document(document["id"], document["name"], document.get("pages") or 1, body, values, key,
                                  date, str((report.get("identity") or {}).get("body") or ""), kind_of(mine)))
        rows[document["id"]] = mine
    if not documents:
        return None
    placed: list[dict] = []
    vocabulary = Vocabulary(store.get_vocabulary())
    record = merge(documents, fields, contract, types, vocabulary, placed, answers)[0].record
    together = []
    for d in documents:
        set_places(rows[d.id], key, [p for p in placed if p["doc"] == d.id])
        together.extend(rows[d.id])
    _ids(record, together, fields)
    record, _ = follow(record, together)
    _leave_out(record, together, contract)
    return without_own(record, contract)


def _ids(record: dict, rows: list[dict], fields: Fields) -> None:
    """Puts the id a name was told as beside the name, where the fields file names a key for it; a person's
    decision about the id counts: a rejected one is left out, a changed one comes in changed."""
    for row in rows:
        f = fields.fields.get(row["field"])
        found = (row.get("match") or {}).get("id")
        if f is None or f.lookup != "register" or not f.id_key:
            continue
        decided = next((d for d in row.get("decisions") or [] if d.get("part") == "id"), None)
        if decided is not None and decided["review"].get("decision") == "rejected":
            continue
        if decided is not None and decided.get("value") is not None:
            found = decided["value"]
        for place in row.get("places") or []:
            if found is not None and place["of"] is None and place["part"] == "":
                set_at(record, [*place["source"].split(".")[:-1], f.id_key], found)


def _leave_out(record: dict, rows: list[dict], contract: Contract) -> None:
    """Takes out the values a person rejected where the record cannot show the mark: an entry of a list goes
    with its first value, another value of an entry goes alone."""
    gone: list[list[str]] = []
    for row in rows:
        for d in row.get("decisions") or []:
            place = next((p for p in row.get("places") or [] if (p["of"], p["part"]) == (d.get("of"), "")), None)
            if place is None or d["review"].get("decision") != "rejected" or d.get("part"):
                continue
            source = place["source"].split(".")
            if has_room(contract, ["[]" if p.isdigit() else p for p in source]):
                continue
            path = place["path"].split(".")
            entry = source[:-1]
            # the first value of a list entry takes the entry with it
            whole = d.get("of") is None and source[-1] == "source" and entry and entry[-1].isdigit()
            gone.append(entry if whole else path)
    # from the back, so that an index stays what it was while the others go
    for path in sorted(gone, key=lambda p: [int(x) if x.isdigit() else -1 for x in p], reverse=True):
        parent = get_at(record, path[:-1])
        if isinstance(parent, list) and path[-1].isdigit() and int(path[-1]) < len(parent):
            del parent[int(path[-1])]
        elif isinstance(parent, dict):
            parent.pop(path[-1], None)


def without_own(record: dict, contract: Contract) -> dict:
    """A copy of the record without what Docket adds, wherever the contract has no room for it."""

    def walk(node, path: list[str]):
        if isinstance(node, list):
            return [walk(child, [*path, "[]"]) for child in node]
        if not isinstance(node, dict):
            return node
        return {k: walk(v, [*path, k]) for k, v in node.items()
                if k not in OWN or has_room(contract, [*path, k])}

    return walk(copy.deepcopy(record), [])
