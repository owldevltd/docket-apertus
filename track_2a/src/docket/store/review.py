"""The review: every value with a place, what a person decided about it, and how a decision lands in the
record.

A source sits either beside its value (custom-meta, contributors, events, conference, related entries carry
`source`) or in the root list `sources[]` with the path to the value. A decision writes `review` at the source;
"changed" also sets the new value at its place and keeps the old one in `before`; "rejected" leaves the value
and marks it, so an export can leave it out. `approve` stays: it is the machine's signal, "open" means approve
without review. A new run over the same document keeps every review a person wrote.
"""

from __future__ import annotations

import copy

from docket.fields.placer import get_at, set_at
from docket.store.base import stamp

DECISIONS = ("confirmed", "changed", "rejected")

# keys of an entry that are not its value
NOT_VALUES = {"source", "id", "role", "meta-name", "page-count", "format", "name", "body"}


def sources_of(record: dict) -> list[dict]:
    """Every value with a place: the path of its source object, the path of the value, the value, the
    document, the block, how, approve and review."""
    out: list[dict] = []
    for i, s in enumerate(record.get("sources", [])):
        path = s.get("path", "")
        value = get_at(record, path.split(".")) if path else None
        out.append(_entry(f"sources.{i}", path, _label(path), value, s))
    _walk(record, [], out)
    return out


def _walk(node, path: list[str], out: list[dict]) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("source"), dict) and path:
            leaves = _leaves(node, path)
            if leaves:
                value_path, value = leaves[0]
                label = str(node["meta-name"]) if node.get("meta-name") else _label(value_path)
                entry = _entry(".".join([*path, "source"]), value_path, label, value, node["source"])
                entry["values"] = {p: v for p, v in leaves}
                out.append(entry)
        for key, child in node.items():
            if key not in ("source", "body"):
                _walk(child, [*path, str(key)], out)
    elif isinstance(node, list):
        for i, child in enumerate(node):
            _walk(child, [*path, str(i)], out)


def _leaves(node: dict, path: list[str]) -> list[tuple[str, object]]:
    """The scalar values of an entry with their paths, the value keys first."""
    out = []
    for key, v in node.items():
        if key in NOT_VALUES:
            continue
        if isinstance(v, dict):
            for inner, iv in v.items():
                if not isinstance(iv, (dict, list)) and iv is not None:
                    out.append((".".join([*path, key, inner]), iv))
        elif not isinstance(v, list) and v is not None:
            out.append((".".join([*path, key]), v))
    return out


def _label(path: str | list[str]) -> str:
    """The field a value belongs to, the same across affairs: the path of the value without indexes and
    without the language ("contributors.data.2.party.de" to "contributors.party")."""
    parts = path.split(".") if isinstance(path, str) else list(path)
    words = [p for p in parts if not p.isdigit() and p not in ("data", "de", "fr", "it")]
    return ".".join(words)


def _entry(source_path: str, value_path: str, label: str, value, source: dict) -> dict:
    return {
        "source": source_path,
        "path": value_path,
        "label": label,
        "value": value,
        "doc": source.get("doc"),
        "block": source.get("block"),
        "how": source.get("how"),
        "approve": bool(source.get("approve")),
        "review": source.get("review"),
        "open": bool(source.get("approve")) and "review" not in source,
    }


def counts(record: dict) -> dict[str, int]:
    """How many values have a place, how many are open, how many decided."""
    entries = sources_of(record)
    return {
        "places": len(entries),
        "open": sum(1 for e in entries if e["open"]),
        "done": sum(1 for e in entries if e["review"] is not None),
    }


def apply_decision(record: dict, source_path: str, decision: str, by: str, after: str | None = None,
                   value_path: str | None = None, rule: str | None = None, at: str | None = None) -> dict:
    """A copy of the record with the decision written at the source; raises ValueError when the source or
    the decision is not right."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {', '.join(DECISIONS)}")
    out = copy.deepcopy(record)
    source = get_at(out, source_path.split("."))
    if not isinstance(source, dict) or "doc" not in source or "block" not in source:
        raise ValueError(f"no source at {source_path}")
    entry = next((e for e in sources_of(out) if e["source"] == source_path), None)
    if entry is None:
        raise ValueError(f"no value for the source at {source_path}")
    path = value_path or entry["path"]
    if entry.get("values") is not None and path not in entry["values"]:
        raise ValueError(f"{path} is not a value of the entry at {source_path}")
    if entry.get("values") is None and path != entry["path"]:
        raise ValueError(f"the source at {source_path} belongs to {entry['path']}, not {path}")
    before = get_at(out, path.split("."))
    review: dict = {"at": at or stamp(), "decision": decision}
    if by:
        review["by"] = by
    if rule:
        review["rule"] = rule
    if decision == "changed":
        if after is None or after == "":
            raise ValueError("a change needs the new value")
        if before is not None:
            review["before"] = str(before)
        set_at(out, path.split("."), after)
    elif decision == "rejected" and before is not None:
        review["before"] = str(before)
    source["review"] = review
    return out


def carry_reviews(old: dict, new: dict) -> tuple[dict, int]:
    """The reviews of an earlier record carried into a new run over the same documents: matched by document
    name, block and value path; a changed value is carried with its review. Returns the record and the count."""
    old_names = {d.get("id"): d.get("name") for d in (old.get("docs") or {}).get("data", [])}
    new_ids = {d.get("name"): d.get("id") for d in (new.get("docs") or {}).get("data", [])}
    wanted = {}
    for e in sources_of(old):
        if e["review"] is None:
            continue
        name = old_names.get(e["doc"])
        if name in new_ids:
            wanted[(new_ids[name], e["block"], _without_doc_index(e["path"]))] = e
    if not wanted:
        return new, 0
    out = copy.deepcopy(new)
    carried = 0
    for e in sources_of(out):
        match = wanted.get((e["doc"], e["block"], _without_doc_index(e["path"])))
        if match is None:
            continue
        source = get_at(out, e["source"].split("."))
        source["review"] = copy.deepcopy(match["review"])
        if match["review"].get("decision") == "changed" and match["value"] is not None:
            set_at(out, e["path"].split("."), match["value"])
        carried += 1
    return out, carried


def _without_doc_index(path: str) -> str:
    """docs.data.3.abstract.de and docs.data.0.abstract.de are the same place in different runs."""
    parts = path.split(".")
    if parts[:2] == ["docs", "data"] and len(parts) > 2 and parts[2].isdigit():
        parts[2] = "n"
    return ".".join(parts)
