"""What the review shows of an affair, taken from the rows of its documents.

A row holds a value as it was read: the document, the field, the block, how it got there, what a lookup found
for it and what a person decided. Where the value sits in a record, the row notes as a place, for the shape it
was laid into. From that the entries of the review are built here, without reading the values out of the
record: per entry the value (after a person's change, the changed one), where it stands in the document, how
it got there, whether a person should look, and the decision. The values of one entry stand together, as a
name with its party. Every value carries the id of its row, which names it in a decision.

The record is only asked for two things: the order its entries stand in, and what it holds with a place that
no row stands for (an affair stored before the rows existed, or put there by hand).
"""

from __future__ import annotations

from collections.abc import Callable

from docket.fields.fields import Fields
from docket.fields.placer import day
from docket.store.review import label_of_path, sources_of
from docket.store.rows import value_id


def entries_of(rows: list[dict], numbers: dict[str, int], fields: Fields,
               block_of: Callable[[str, str], dict | None], record: dict | None = None) -> list[dict]:
    """The entries of an affair from the rows of its documents. `numbers` is the number each document has in
    the affair, by its name; `block_of` gives a block of a document by the document's name and the block's id.
    With `record`, the entries stand in its order and what only it holds with a place comes after them."""
    by_number = {(r["doc"], r["n"]): r for r in rows}
    groups: dict[str, list[tuple[dict, dict]]] = {}
    for row in sorted(rows, key=lambda r: (numbers.get(r["doc"], 0), r["n"])):
        for place in row.get("places") or []:
            groups.setdefault(place["source"], []).append((row, place))
    out = []
    for source, members in groups.items():
        # the row the entry belongs to: its own value sits there; of several, the one placed last
        own = [(r, p) for r, p in members if p["of"] is None]
        owner, at = own[-1] if own else (by_number.get((members[0][0]["doc"], members[0][1]["of"])), None)
        if owner is None:
            continue
        ordered = sorted(members, key=lambda m: _rank(m, fields))
        values = {p["path"]: _value(r, p, fields) for r, p in ordered}
        first, first_place = ordered[0]
        f = fields.fields.get(first["field"])
        named = (f.fixed.get("meta-name") if f is not None and first_place["part"] == "" else None)
        how, approve = _flags(owner, at, fields, block_of)
        decisions = [d for r, p in members for d in r.get("decisions") or []
                     if (d.get("of"), d.get("part", "")) == (p["of"], p["part"])]
        review = max(decisions, key=lambda d: d.get("seq", 0))["review"] if decisions else None
        entry = {
            "id": value_id(first, first_place),
            "field": first["field"],
            "source": source,
            "path": first_place["path"],
            "label": str(named) if named else label_of_path(first_place["path"]),
            "value": values[first_place["path"]],
            "doc": numbers.get(owner["doc"]),
            "block": owner["block"],
            "how": how,
            "approve": approve,
            "review": review,
            "open": approve and review is None,
        }
        if not source.startswith("sources."):
            entry["values"] = values
            entry["ids"] = {p["path"]: value_id(r, p) for r, p in ordered}
        out.append(entry)
    if record is None:
        return out
    held = sources_of(record)
    order = {e["source"]: i for i, e in enumerate(held)}
    out.sort(key=lambda e: order.get(e["source"], len(order)))
    # what the record holds with a place and no row stands for keeps the place as its id
    left = [{**e, "id": e["source"]} for e in held if e["source"] not in groups]
    return sorted([*out, *left], key=lambda e: order.get(e["source"], len(order)))


def counts_of(entries: list[dict]) -> dict[str, int]:
    """How many values have a place, how many are open, how many decided."""
    return {
        "places": len(entries),
        "open": sum(1 for e in entries if e["open"]),
        "done": sum(1 for e in entries if e["review"] is not None),
    }


def _rank(member: tuple[dict, dict], fields: Fields) -> tuple[int, int]:
    """The order of the values within an entry: the entry's own value, the values laid beside it in the order
    of the fields file, the id last."""
    row, place = member
    names = list(fields.fields)
    at = names.index(row["field"]) if row["field"] in names else len(names)
    return (2 if place["part"] else (0 if place["of"] is None else 1), at)


def _value(row: dict, place: dict, fields: Fields):
    """The value at a place: what a person changed it to, else what the lookup found for an id, else the
    value as read, a date as its day."""
    at = (place["of"], place["part"])
    changed = [d for d in row.get("decisions") or [] if (d.get("of"), d.get("part", "")) == at
               and d["review"].get("decision") == "changed" and d.get("value") is not None]
    if changed:
        return max(changed, key=lambda d: d.get("seq", 0))["value"]
    if place["part"] == "id":
        return (row.get("match") or {}).get("id")
    f = fields.fields.get(row["field"])
    return day(row["value"]) if f is not None and f.form == "date" else row["value"]


def _flags(owner: dict, place: dict | None, fields: Fields,
           block_of: Callable[[str, str], dict | None]) -> tuple[str, bool]:
    """How the entry's value got its place and whether a person should look, as the placing says it of the
    row: worded by the model, found literally or derived, else cited; to look at when it is neither literal
    nor derived, when its block was read from an image, or when a second opinion or the lookup said so."""
    if place is not None and place["part"] == "id":
        return "derived", (owner.get("match") or {}).get("how", "exact") != "exact"
    f = fields.fields.get(owner["field"])
    how = owner.get("how") or "literal"
    how = "composed" if f is not None and f.free else (how if how in ("literal", "derived") else "cited")
    block = block_of(owner["doc"], owner["block"]) if owner.get("block") else None
    look = how not in ("literal", "derived") or bool(block and block.get("approve"))
    return how, bool(owner.get("approve", look))
