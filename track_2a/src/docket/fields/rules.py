"""What code decides about the values of a document without the model: before it is asked, and after it has
answered.

Before: a field that names a way under "reader" is read by code and not asked. After: a value that already
stands under another field is left out ("apart"), a field has no value without the one it belongs to
("needs"), a field is read from documents of its kinds only ("kinds"), and the value of one field becomes an
entry of a list as well ("entry"). Which field does what is said in the fields file; nothing here names a
field, a parliament or a kind of document. Beside these, the check of a text the model worded against the
document it worded it from: the model is not looked over each time, only where it leaves its document.
"""

from __future__ import annotations

import re

from docket.document.language import language_of, language_of_text
from docket.fields.fields import Fields, questions
from docket.fields.placer import (
    DAY_MARK, MONTH_WORDS, WEEKDAYS, bare, block_text, blocks_of, day, overlap, plain, whole,
)

# a text the model worded itself (the summary) stands without a mark while at least this share of its words
# stands in the document. Measured 13 October 2026 on 120 documents, 60 of them never used before: the summary
# of a document shares 0.39 to 0.93 of its words with it, 0.71 in the middle; the summary of another document of
# the same language 0.18 in the middle and 0.31 at nine in ten. Set by the assistant, open.
COMPOSED_SHARE = 0.4

# a place and a day in one line, the way a document is dated ("Liestal, 3. März 2020", "Lausanne, le 3 mars
# 2020"). No list of places stands behind it; what tells a place is its form and where it stands. A word of a
# place name starts with a capital and has small letters, no digits: an abbreviation or a file reference before
# a day is none ("LAT, le 18 septembre 2012", "ED/P255460 Basel, 27. Mai 2026" gives Basel). Up to four such
# words, a short one with a point in front ("St. Gallen"), small words between them ("Neuhausen am Rheinfall").
_NAME = r"[A-ZÄÖÜÉÈÀ][A-Za-zÀ-ÿ'’\-]*[a-zà-ÿ][A-Za-zÀ-ÿ'’\-]*"
PLACE_DAY = re.compile(
    r"((?:[A-Z][a-z]{0,2}\.\s?)?" + _NAME + r"(?:[ \-/](?:[a-zäöüéèà]{1,3} )?" + _NAME + r"){0,3})"
    r"\s*,\s*(?:den |le |il |li |lì |am )?"
    r"(?i:\d{1,2}\.\s*\d{1,2}\.\s*\d{2,4}|\d{1,2}/\d{1,2}/\d{4}"
    r"|\d{1,2}" + DAY_MARK + r"\s*(?:" + MONTH_WORDS + r")\s*\d{4})"
)
# the line stands by itself: at the start of a block or a line, after the end of a sentence, after a number, or
# after a word that leads to a place ("adopté à Lausanne, le …"); in running text a name before a day is
# something else ("selon le Conseil, le 3 mars 2020, …"), and so is one in brackets
_LEADS = re.compile(r"(?:^|[\s,;])(?:à|a|in|zu)$", re.I)


def _stands_alone(text: str, m: re.Match) -> bool:
    # the day of the week before a date is no place ("Sitzung vom Montag, 3. März 2020")
    if bare(re.split(r"[ \-/]", m.group(1))[-1]) in WEEKDAYS:
        return False
    before = text[:m.start(1)].rstrip(" \t")
    led = not before or before[-1] in "\n.:;" or before[-1].isdigit() or _LEADS.search(before) is not None
    goes_on = re.match(r"\s*,\s*[a-zà-ÿ]", text[m.end():]) is not None
    return led and not goes_on


def before_day(body: list[dict]) -> tuple[str, str] | None:
    """The place a document is dated at: the words before the day in the first line of a place and a day, with
    the id of their block; None when the pages hold no such line."""
    for block in blocks_of(body):
        if block["type"] == "graphic":
            continue
        text = block_text(block)
        for m in PLACE_DAY.finditer(text):
            if _stands_alone(text, m):
                return m.group(1).strip(), block["id"]
    return None


# the ways code reads a field itself, by the name a field gives under "reader". Asked for the place, the model
# named one in 22 of 60 documents that print none, mostly the polity (measured 13 October 2026); read from
# the line of place and day, the place came out as in the reference in 56 of the 60 instead of 34. On 151
# documents the rule was not made on, 5 of 26 lines found were none (an abbreviation, a file reference, the end
# of the sentence before): hence the form of a name and the place of the line above.
READERS = {"before-day": before_day}


def read_by_code(values: dict, report: dict, fields: Fields, body: list[dict]) -> None:
    """The fields the code reads itself: found, the value stands literally in its block; not found, the field
    is empty and counts as not asked."""
    for name, f in fields.fields.items():
        if f.reader:
            hit = READERS[f.reader](body)
            if hit:
                entry = {"value": hit[0], "block": hit[1], "how": "literal"}
                values[name] = [dict(entry)]
                report[name] = {"value": hit[0], "state": "on the page", "items": [entry]}
            else:
                note = f"not asked: read by code ({f.reader}), nothing of the kind on the pages"
                report[name] = {"value": None, "state": "empty", "items": [], "note": note}


def unsound(worded: str, source: str, language: str) -> str:
    """Why a text the model worded itself needs a person, or '' when nothing speaks against it. The model is not
    looked over each time, only where it leaves its document: too few of the words stand in the document, the
    text is in another language than the document, or it holds a number the document does not."""
    if overlap(worded, source) < COMPOSED_SHARE:
        return "few of its words stand in the document"
    spoken = language_of_text(worded)
    if spoken and language and spoken != language:
        return "in another language than the document"
    held = {int(n) for n in re.findall(r"\d+", source)}
    if any(int(n) not in held for n in re.findall(r"\d{2,}", worded)):
        return "a number the document does not hold"
    return ""


def keep_apart(values: dict, report: dict, fields: Fields) -> None:
    """A value that already stands under a field named in "apart" is left out of this field: asked for the
    party, the model repeats the group that submitted, or names the parliament (measured 13 October 2026: 14 of
    the 24 parties set in documents that print none were such values). A part of the other value counts as
    well ("Luzern" as the place of a session where the polity is "Stadt Luzern"), not a value that holds the
    other one and more: "CVP Glarus" is a party though the polity is Glarus, "Sitzung des Einwohnerrats" a
    session though the parliament is the Einwohnerrat (seen on documents the rule was not made on). Then a
    field that "needs" another has no value where that one has none: no day and no place of a session without
    the session."""

    def leave(name: str, kept: list[dict], why: dict[str, str]) -> None:
        for entry in report.get(name, {}).get("items", []):
            if entry.get("block") is not None and plain(entry["value"]) in why:
                entry["block"], entry["how"] = None, why[plain(entry["value"])]
        if kept:
            values[name] = kept
        else:
            del values[name]
            report[name]["state"] = "empty"

    for name, f in fields.fields.items():
        if not f.apart or name not in values:
            continue
        taken = [(hit["value"], other) for other in f.apart for hit in values.get(other, [])]
        why = {}
        for hit in values[name]:
            other = next((o for v, o in taken if whole(hit["value"], v)), None)
            if other:
                why[plain(hit["value"])] = f"left out: stands under {other}"
        if why:
            leave(name, [hit for hit in values[name] if plain(hit["value"]) not in why], why)
    for name, f in fields.fields.items():
        if f.needs and name in values and f.needs not in values:
            leave(name, [], {plain(hit["value"]): f"left out: no {f.needs}" for hit in values[name]})


def keep_kinds(values: dict, report: dict, fields: Fields) -> None:
    """A field that names kinds of documents under "kinds" is read from documents of these kinds only: the day
    an affair was submitted from the submission itself. Asked for it, the model gives the day the document at
    hand carries; in an answer or a report that is another day about as often as not (measured 13 October 2026:
    right in 31 of 33 submissions and in 10 of 19 other documents of the reference set; on 60 documents the rule
    was not made on, as OpenParlData in 26 of 32 and in 7 of 18). The kind is the one the model named; where it
    named none, the value stays."""
    asked = next((q["name"] for q in questions(fields) if q.get("role") == "kind"), "")
    named = (report.get(asked) or {}).get("value")
    if not named:
        return
    for name, f in fields.fields.items():
        if f.kinds and named not in f.kinds and name in values:
            for entry in report[name].get("items", []):
                if entry.get("block") is not None:
                    entry["block"], entry["how"] = None, f"left out: the document is a {named}"
            del values[name]
            report[name]["state"] = "empty"


def add_entries(values: dict, report: dict, fields: Fields, language: str) -> None:
    """The value of a field with "entry" becomes an entry of the list named there as well, under the label of
    the field in the language of the document, and stands first: the day an affair was submitted is its first
    event. OpenParlData lists the submission among the events of an affair, on the day the affair began; read
    from the document alone, that event was missing in 19 of 60 documents and its day stood under the date
    only (measured 13 October 2026). Not added where the list holds that day already."""
    for name, f in fields.fields.items():
        # not where a single field is asked later on and the list is not among the fields at hand
        if not f.entry or name not in values or f.entry.get("of") not in fields.fields:
            continue
        lead = fields.fields[f.entry["of"]]
        mate = lead.paired
        hit = values[name][0]
        if not day(hit["value"]) or any(day(h["value"]) == day(hit["value"]) for h in values.get(mate, [])):
            continue
        labels = f.entry.get("label", {})
        label = labels.get(language) or labels.get("de") or name
        pair = {lead.name: {"value": label, "block": hit["block"], "how": "derived"},
                mate: {"value": hit["value"], "block": hit["block"], "how": hit["how"]}}
        for key, entry in pair.items():
            values[key] = [dict(entry), *values.get(key, [])]
            held = report.setdefault(key, {"value": None, "state": "empty", "items": []})
            held["items"] = [dict(entry), *held.get("items", [])]
            held["state"] = "on the page"


def settle(values: dict, report: dict, fields: Fields, body: list[dict]) -> None:
    """What holds between the values of a document once the model has answered, in this order: values that
    belong elsewhere are left out, then values a document of this kind does not give, then the entries that
    follow from what is left."""
    keep_apart(values, report, fields)
    keep_kinds(values, report, fields)
    add_entries(values, report, fields, language_of(body))
