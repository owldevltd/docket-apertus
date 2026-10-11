"""What a visitor reads: the affairs in the affair schema, and nothing but them.

Every answer here is made of the records the store holds, in the schema of data/schema/docket.json: a list of
affairs, one affair, and the tables that follow from the affairs the way OpenParlData keeps them beside its
affairs (those who take part, the groups they belong to, the meetings documents name, the events of the
course), every row with the `affair_id` it comes from. No row of the store, no report of a run and no
decision is read: what the record does not say is not shown. In a list the blocks of the documents are left
out; the record of one affair holds them.
"""

from __future__ import annotations

import copy

# the tables that follow from the affairs, by the name OpenParlData has for each
TABLES = ("contributors", "groups", "meetings", "events")

# what a search over the affairs is asked by; any other name asks for the rows of a table that hold exactly
# that value under it
SEARCH = ("q", "body_key", "type", "kind", "language")

# the parts of a document entry that hold its blocks
BLOCKS = ("body", "back")


def text_of(value) -> str:
    """The text of a value the schema holds per language: the first there is."""
    if isinstance(value, dict):
        return next((str(v) for v in value.values() if v not in (None, "")), "")
    return "" if value is None else str(value)


def wordings(value) -> list[str]:
    """Every wording of a value the schema holds per language."""
    if isinstance(value, dict):
        return [str(v) for v in value.values() if v not in (None, "")]
    return [] if value in (None, "") else [str(value)]


def light(record: dict) -> dict:
    """A copy of the record without the blocks of its documents, for a list."""
    out = copy.deepcopy(record)
    for entry in (out.get("docs") or {}).get("data") or []:
        for key in BLOCKS:
            entry.pop(key, None)
        for answer in entry.get("response") or []:
            answer.pop("body", None)
    return out


def fits(record: dict, asked: dict[str, str], bodies: dict[str, dict]) -> bool:
    """Whether an affair is what a visitor searches for: every word of `q` in its title, number, type, id,
    parliament or a document's name; `body_key`, `type`, `kind` and `language` as given. The type is asked
    for by any of its wordings, the standard name in whatever language or the name the document prints: a
    page in French asks by the French one."""
    docs = (record.get("docs") or {}).get("data") or []
    body = bodies.get(str(record.get("body_key") or "")) or {}
    types = wordings(record.get("type_harmonized")) + wordings(record.get("type_name"))
    text = " ".join([*wordings(record.get("title")), str(record.get("number") or ""), *types,
                     str(record.get("id") or ""), str(body.get("name") or ""), str(body.get("parliament") or ""),
                     *(str(d.get("name") or "") for d in docs)]).lower()
    return (
        all(word in text for word in asked.get("q", "").lower().split())
        and asked.get("body_key", record.get("body_key")) == record.get("body_key")
        and ("type" not in asked or asked["type"] in types)
        and ("kind" not in asked or asked["kind"] in [d.get("article-type") for d in docs])
        and ("language" not in asked or asked["language"] in [d.get("language") for d in docs])
    )


def listed(records: list[dict], asked: dict[str, str] | None, bodies: dict[str, dict]) -> dict:
    """The affairs that fit, the newest first, as {meta, data}."""
    asked = {k: v.strip() for k, v in (asked or {}).items() if v and v.strip()}
    found = [light(r) for r in records if fits(r, asked, bodies)]
    found.sort(key=lambda r: (str(r.get("begin_date") or ""), str(r.get("id") or "")), reverse=True)
    return {"meta": {"total": len(records), "count": len(found), "blocks": "left out, see /api/records/<id>"},
            "data": found}


def table(name: str, records: list[dict], asked: dict[str, str] | None, bodies: dict[str, dict]) -> dict:
    """One of the tables that follow from the affairs, over the affairs that fit, as {meta, data}. `q` looks
    for its words in a row; a name of the table itself (`fullname`, `name`, `conf-name`, ...) asks for the rows
    that hold exactly that value: the rows of one person, one group, one meeting."""
    asked = {k: v.strip() for k, v in (asked or {}).items() if v and v.strip()}
    rows: list[dict] = []
    for record in records:
        if fits(record, {k: v for k, v in asked.items() if k != "q"}, bodies):
            rows.extend(_rows(name, record))
    words = asked.get("q", "").lower().split()
    exact = {k: v for k, v in asked.items() if k not in SEARCH}
    found = [r for r in rows if all(w in " ".join(text_of(v) for v in r.values()).lower() for w in words)
             and all(text_of(r.get(k)) == v for k, v in exact.items())]
    return {"meta": {"total": len(rows), "count": len(found)}, "data": found}


def _rows(name: str, record: dict) -> list[dict]:
    """The rows one affair gives a table, each with the affair and the parliament it comes from."""
    home = {"affair_id": record.get("id"), **({"body_key": record["body_key"]} if record.get("body_key") else {})}
    people = (record.get("contributors") or {}).get("data") or []
    docs = (record.get("docs") or {}).get("data") or []
    if name == "contributors":
        return [{**home, **{k: v for k, v in c.items() if k != "source"}} for c in people]
    if name == "events":
        return [{**home, **{k: v for k, v in e.items() if k != "source"}}
                for e in (record.get("events") or {}).get("data") or []]
    if name == "meetings":
        return [{**home, "doc": d.get("name"), **d["conference"]} for d in docs if d.get("conference")]
    if name == "groups":
        rows = [{**home, "name": text_of(c["party"]), "type": "party"} for c in people if c.get("party")]
        rows += [{**home, "name": str(c["on-behalf-of"]), "type": "on-behalf-of"} for c in people
                 if c.get("on-behalf-of")]
        rows += [{**home, "name": str(m.get("meta-value")), "type": m["meta-name"]}
                 for m in record.get("custom-meta") or [] if m.get("meta-name") in ("addressee", "department")]
        seen: set[tuple] = set()
        once = []
        for r in rows:
            if r["name"] and (r["name"], r["type"]) not in seen:
                seen.add((r["name"], r["type"]))
                once.append(r)
        return once
    return []
