"""Translates what the document names into what OpenParlData holds: the type label ("Schriftliche Anfrage",
"Standesinitiative") into the harmonised type in four languages. First through the vocabulary of the
parliament (docket.store.vocabulary): the same label stands for another type in another parliament ("Antrag"
is an amendment in Basel-Stadt and government business elsewhere). Where the parliament is not known or does
not list the label, through the table of the export (tools/knowledge.py), which knows the label alone.
OpenParlData calls its harmonised types provisional, so both are data, not code.
"""

from __future__ import annotations

import re

from docket.fields.fields import Fields
from docket.fields.placer import get_at, set_at
from docket.store.vocabulary import Vocabulary

# an entry of the table counts only when this many affairs carry it and this share of them falls on one type
COUNT = 3
SHARE = 0.6


def harmonized(label: str, table: dict[str, dict], vocabulary: Vocabulary | None = None,
               parliament: str = "", name_of_list: str = "types") -> dict | None:
    """The harmonised type for a label, in four languages; None when nothing knows it. First the whole label,
    then the label without additions in brackets, then its first word ("Motion Muster Hans"). A label the
    parliament lists without a harmonised type has none: the table of all parliaments is not asked then."""
    flat = re.sub(r"\s+", " ", label).strip().lower()
    attempts = (flat, re.sub(r"\s*\(.*\)\s*", " ", flat).strip(), flat.split(" ")[0])
    if vocabulary is not None and parliament:
        for attempt in attempts:
            row = vocabulary.row(name_of_list, parliament, attempt)
            if row is not None:
                return row["standard"]
    for attempt in attempts:
        hit = table.get(attempt)
        if hit is not None and hit["count"] >= COUNT and hit["share"] >= SHARE:
            return hit["type"]
    return None


def harmonize(affair: dict, table: dict[str, dict], vocabulary: Vocabulary | None = None,
              parliament: str = "", fields: Fields | None = None) -> dict:
    """Adds the harmonised type to an affair when the label is known and none stands there yet. Which value
    is the label and where its standard name goes is said by the fields file: a field whose entity has a list
    of the vocabulary behind it and that names a place for the standard name. Without a fields file, the keys
    of OpenParlData."""
    places = [(["type_name", "de"], ["type_harmonized"], "types")]
    if fields is not None:
        places = [(f.path, f.standard.split("."), f.list_name) for f in fields.fields.values()
                  if f.lookup == "vocabulary" and f.standard and "[]" not in f.path]
    for path, target, name_of_list in places:
        label = get_at(affair, path)
        if get_at(affair, target) or not label:
            continue
        # the table of the export knows the types alone
        found = harmonized(str(label), table if name_of_list == "types" else {}, vocabulary, parliament, name_of_list)
        if found is not None:
            set_at(affair, target, {k: v for k, v in found.items() if v is not None})
    return affair
