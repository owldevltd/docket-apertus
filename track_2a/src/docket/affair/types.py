"""Translates what the document names into what OpenParlData holds: the type label ("Schriftliche Anfrage",
"Standesinitiative") into the harmonised type in four languages. The table comes from the export
(tools/knowledge.py); OpenParlData calls its harmonised types provisional, so the table is data, not code.
"""

from __future__ import annotations

import re

# an entry of the table counts only when this many affairs carry it and this share of them falls on one type
COUNT = 3
SHARE = 0.6


def harmonized(label: str, table: dict[str, dict]) -> dict | None:
    """The harmonised type for a label, in four languages; None when the table does not know it. First the
    whole label, then the label without additions in brackets, then its first word ("Motion Muster Hans")."""
    flat = re.sub(r"\s+", " ", label).strip().lower()
    for attempt in (flat, re.sub(r"\s*\(.*\)\s*", " ", flat).strip(), flat.split(" ")[0]):
        hit = table.get(attempt)
        if hit is not None and hit["count"] >= COUNT and hit["share"] >= SHARE:
            return hit["type"]
    return None


def harmonize(affair: dict, table: dict[str, dict]) -> dict:
    """Adds the harmonised type to an affair when the label is known and none stands there yet."""
    label = (affair.get("type_name") or {}).get("de")
    if affair.get("type_harmonized") or not label:
        return affair
    found = harmonized(label, table)
    if found is not None:
        affair["type_harmonized"] = {k: v for k, v in found.items() if v is not None}
    return affair
