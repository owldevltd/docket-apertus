"""One affair per key: the documents with the same key folded into one record, the oldest first, every value
with its place; then the harmonised type from the label, then the check against the contract."""

from __future__ import annotations

from dataclasses import dataclass, field

from docket.affair.types import harmonize
from docket.affair.validator import Contract
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


@dataclass
class Affair:
    key: str
    record: dict
    documents: list[int]
    errors: list[str]


def merge(documents: list[Document], fields: Fields, contract: Contract, types: dict[str, dict],
          vocabulary: Vocabulary | None = None) -> list[Affair]:
    """Groups the documents by key and builds one affair per group, in the order the keys first appear. The
    type is harmonised through the names of the parliament the affair's documents tell, then through the
    table."""
    groups: dict[str, list[Document]] = {}
    for d in documents:
        groups.setdefault(d.key, []).append(d)
    out = []
    for key, members in groups.items():
        members = sorted(members, key=lambda d: (d.date or "9", d.id))
        record: dict = {"schema": SCHEMA}
        for d in members:
            record, _ = fill(record, d.id, d.values, fields, contract, d.body)
            for entry in record["docs"]["data"]:
                if entry.get("id") == d.id:
                    entry.setdefault("name", d.name)
                    entry.setdefault("format", FORMAT)
                    entry.setdefault("page-count", d.pages)
                    entry.setdefault("body", d.body)
        parliament = next((d.parliament for d in members if d.parliament), "")
        record = harmonize(record, types, vocabulary, parliament)
        out.append(Affair(key, record, [d.id for d in members], contract.check(record)))
    return out


def values_of(report: dict[str, dict]) -> dict[str, list[dict]]:
    """The placed values of a document from its fields report: per field the items with a block."""
    out: dict[str, list[dict]] = {}
    for name, r in report.items():
        for item in r.get("items", []):
            if item.get("block") is not None:
                hit = {"value": item["value"], "block": item["block"], "how": item.get("how") or "literal"}
                out.setdefault(name, []).append(hit)
    return out
