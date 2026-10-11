"""One affair per key: the documents with the same key folded into one record, the oldest first, every value
with its place; then the harmonised type from the label, then the check against the contract."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from docket.affair.types import harmonize
from docket.affair.validator import Contract
from docket.document.language import language_of
from docket.document.response import lift
from docket.fields.fields import Fields
from docket.fields.placer import fill
from docket.store.vocabulary import Vocabulary

SCHEMA = "0.8"
FORMAT = "application/pdf"


@dataclass
class Document:
    """What one document knows, for the merging: its blocks, its placed values per field, its key and date."""

    id: int
    name: str
    pages: int
    body: list[dict]
    values: dict[str, list[dict]] = field(default_factory=dict)
    key: str = ""
    date: str = ""
    # the parliament's key at OpenParlData ("ZH"), empty when the document does not tell
    parliament: str = ""
    # what the document itself is, as the run found it: {kind, block}, with the number of its row when it has one
    kind: dict | None = None


@dataclass
class Affair:
    key: str
    record: dict
    documents: list[int]
    errors: list[str]


def merge(documents: list[Document], fields: Fields, contract: Contract, types: dict[str, dict],
          vocabulary: Vocabulary | None = None, placed: list[dict] | None = None,
          answers: Iterable[str] = ()) -> list[Affair]:
    """Groups the documents by key and builds one affair per group, in the order the keys first appear. The
    type is harmonised through the names of the parliament the affair's documents tell, then through the
    table. With `placed`, where every numbered value went is noted there (docket.fields.placer.fill). With
    `answers`, the section names that announce one, the answer within a document stands as its `response`
    beside its body (docket.document.response)."""
    answers = list(answers)
    groups: dict[str, list[Document]] = {}
    for d in documents:
        groups.setdefault(d.key, []).append(d)
    out = []
    for key, members in groups.items():
        members = sorted(members, key=lambda d: (d.date or "9", d.id))
        record: dict = {"schema": SCHEMA}
        for d in members:
            language = language_of(d.body)
            record, _ = fill(record, d.id, d.values, fields, contract, d.body, placed, language)
            for at, entry in enumerate(record["docs"]["data"]):
                if entry.get("id") == d.id:
                    entry.setdefault("name", d.name)
                    entry.setdefault("format", FORMAT)
                    if language:
                        entry.setdefault("language", language)
                    entry.setdefault("page-count", d.pages)
                    if "body" not in entry:
                        entry["body"], response = lift(d.body, answers)
                        if response:
                            entry["response"] = response
                    if d.kind and d.kind.get("kind") and "article-type" not in entry:
                        _place_kind(record, at, d, placed)
        parliament = next((d.parliament for d in members if d.parliament), "")
        record = harmonize(record, types, vocabulary, parliament, fields)
        out.append(Affair(key, record, [d.id for d in members], contract.check(record)))
    return out


def _place_kind(record: dict, at: int, d: Document, placed: list[dict] | None) -> None:
    """Sets the kind of a document on its entry, with a place in the root sources: found from the words of its
    first page, so a person has to look."""
    record["docs"]["data"][at]["article-type"] = d.kind["kind"]
    path = f"docs.data.{at}.article-type"
    place = {"path": path, "doc": d.id, "block": d.kind.get("block") or "b1", "how": "derived", "approve": True}
    record.setdefault("sources", []).append(place)
    if placed is not None and d.kind.get("n") is not None:
        placed.append({"doc": d.id, "n": d.kind["n"], "of": None, "source": f"sources.{len(record['sources']) - 1}",
                       "path": path})


def values_of(report: dict[str, dict]) -> dict[str, list[dict]]:
    """The placed values of a document from its fields report: per field the items with a block."""
    out: dict[str, list[dict]] = {}
    for name, r in report.items():
        for item in r.get("items", []):
            if item.get("block") is not None:
                hit = {"value": item["value"], "block": item["block"], "how": item.get("how") or "literal"}
                out.setdefault(name, []).append(hit)
    return out
