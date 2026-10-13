"""Asks the fields over the document and takes what stands on the page.

The model gets the first pages as a text image, every block with its id in front, and up to six questions at
once, each with the contract's rule for its place. Fields over the whole document get all pages while the text
image fits the frame. What it answers goes through the placer: literal on the page, derived from the named
block, cited with a word in the named block, or dropped. Fields without a line or with a refused value are asked
once more. Values seen so far are not offered in the prompt (measured 6 October 2026: more values that are not
on the page), but they are kept, so a person can look at them. What code decides without the model, before it
is asked and after it has answered, is in `docket.fields.rules`.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from docket.affair.validator import Contract
from docket.document.bridge import Knowledge
from docket.document.language import language_of
from docket.document.picture import text_image
from docket.fields.fields import Field, Fields, questions
from docket.fields.placer import (
    DAY_MARK, MONTH_WORDS, block_text, blocks_of, covers, day, fill, find_block, locate, overlap, plain, words,
)
from docket.fields.rules import read_by_code, settle, unsound
from docket.model.client import Client, ask

# this many fields in one call
BUNDLE = 6

# room for the answer: this many tokens per field, at least this many
ROOM = (50, 400)

# instead of the dash the model sometimes writes out that nothing is there, or returns the pattern of the task
NONE = re.compile(
    r"^[\-–—\s]*$|nicht angegeben|keine angabe|nicht vorhanden|nicht genannt|nicht ersichtlich|unbekannt"
    r"|TT\.MM\.JJJJ"
    # a bare no in the languages of the documents, and a value that is nothing but a bracket ("(porte-parole)")
    r"|^\W*(?:nein|non|no|none|keine?r?|aucune?|nessun[oa]?)\W*$|^\s*\([^()]*\)\s*$",
    re.I,
)

# for fields over the whole document at most this many characters of text image; above it the first pages and
# the last
WHOLE = 120000
BREAK = "===== Seite {n} ====="

# when an answer stays away, wait this many seconds and ask once more
RETRY = 10

# a field with block-text (the title) takes the text of the named block instead of the answer when every word
# of the answer stands in it and the block is at most this many times longer. Measured 6 October 2026 on 72
# documents: blocks of 1.3 and 1.7 times were title lines, of 3, 3 and 8.4 times paragraphs. Set by the
# assistant, open.
TITLE_STRETCH = 2

# a block the model names counts only when more than this share of the value's words stand in it; 0 means at
# least one word. Measured 6 October 2026: in 142 of 204 named blocks not one word stood. Set by the
# assistant, open.
OVERLAP = 0.0

# these states get one more question, at most one bundle per scope
AGAIN = ("missing", "too short", "too long", "no date")

# the day an entry of a paired field names: as asked for, as the record holds it, or written out
PAIR_DAY = re.compile(
    r"\d{4}-\d{2}-\d{2}|\d{1,2}\.\s*\d{1,2}\.\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}"
    r"|\d{1,2}" + DAY_MARK + r"\s*(?:" + MONTH_WORDS + r")\s*\d{4}",
    re.I,
)


def fill_document(record: dict, pages: list[dict], first: list[int], fields: Fields, contract: Contract,
                  client: Client | None, knowledge: Knowledge, log: Path | None = None) -> tuple[dict, dict]:
    """The whole way for one document: fields over the first pages with their text image, fields over the
    whole document with the text image of all pages, one call per bundle, answers checked and looked for on
    the pages, built in, learnt. Returns the record and the report: per field what became of it, and the
    calls."""
    body = record["docs"]["data"][0]["body"]
    values: dict[str, list[dict]] = {}
    report: dict[str, dict] = {}
    asked: list[dict] = []
    if client is None:
        return record, {"fields": report, "asked": asked}
    read_by_code(values, report, fields, body)
    # a field another one is paired with is answered in that one's line and has no line of its own
    mates = {f.paired for f in fields.fields.values() if f.paired}
    for scope, which in (("first", first), ("all", whole_pages(pages, body))):
        names = [n for n, f in fields.fields.items() if f.pages == scope and n not in mates and not f.reader]
        if not names:
            continue
        text = picture(pages, body, which)
        # fields with a condition only when one of its words is there; else they count as empty, without a call
        flat = plain(text)
        remaining = []
        for name in names:
            when = fields.fields[name].when
            if when and not any(plain(w) in flat for w in when):
                note = "not asked: none of the words " + ", ".join(when) + " on the page"
                report[name] = {"value": None, "state": "empty", "items": [], "note": note}
            else:
                remaining.append(name)
        run = _Run(text, which, len(pages), body, fields, contract, client, values, report, asked, log)
        for bundle in bundles(remaining, fields):
            # when the answer stays away (timeout, error of the service), once more; then on without the bundle
            if not run.round(bundle):
                if client.halted:
                    return _finish(record, values, report, asked, fields, contract, body, knowledge)
                time.sleep(RETRY)
                if not run.round(bundle):
                    if client.halted:
                        return _finish(record, values, report, asked, fields, contract, body, knowledge)
                    for name in bundle:
                        note = "no answer from the service"
                        report[name] = {"value": None, "state": "missing", "items": [], "note": note}
        # the questions about the document itself, in a call of their own over the first pages
        about = [q["name"] for q in questions(fields)] if scope == "first" else []
        if about and not client.halted and not run.round(about):
            for name in about:
                report[name] = {"value": None, "state": "missing", "items": [], "note": "no answer from the service"}
        # the follow-up: what had no line or was refused, once more, at most one bundle
        again = [n for n in remaining if report.get(n, {}).get("state") in AGAIN][:BUNDLE]
        if again and not client.halted:
            before = {n: report[n]["state"] for n in again}
            if run.round(again):
                for name in again:
                    report[name]["asked again"] = before[name]
    return _finish(record, values, report, asked, fields, contract, body, knowledge)


def bundles(names: list[str], fields: Fields) -> list[list[str]]:
    """The calls of one scope. Fields that name the same word under "together" get a call of their own, in the
    place of the first of them: asked in separate calls the model answers each alone and gives the same names to
    the authors and to the co-signers. The rest goes in the order of the file, BUNDLE per call."""
    out: list[list[str]] = []
    groups: dict[str, list[str]] = {}
    rest: list[str] = []
    for name in names:
        word = fields.fields[name].together
        if not word:
            rest.append(name)
        elif word in groups:
            groups[word].append(name)
        else:
            # what was gathered so far goes out first, so that the calls keep the order of the file
            out += [rest[k:k + BUNDLE] for k in range(0, len(rest), BUNDLE)]
            rest = []
            groups[word] = [name]
            out.append(groups[word])
    out += [rest[k:k + BUNDLE] for k in range(0, len(rest), BUNDLE)]
    return [b[k:k + BUNDLE] for b in out for k in range(0, len(b), BUNDLE)]


def _finish(record: dict, values: dict, report: dict, asked: list, fields: Fields, contract: Contract,
            body: list[dict], knowledge: Knowledge) -> tuple[dict, dict]:
    settle(values, report, fields, body)
    out, notes = fill(record, 1, values, fields, contract, body)
    for name, note in notes.items():
        report.setdefault(name, {})["note"] = note
    knowledge.learn(values)
    return out, {"fields": report, "asked": asked}


def whole_pages(pages: list[dict], body: list[dict]) -> list[int]:
    """The pages for fields over the whole document: all while the text image fits the frame, else the first
    ones and the last."""
    take: list[int] = []
    length = 0
    for n in range(1, len(pages) + 1):
        length += len(_one(pages, body, n))
        if length > WHOLE and take:
            break
        take.append(n)
    if len(take) < len(pages) and len(pages) not in take:
        take.append(len(pages))
    return take


def picture(pages: list[dict], body: list[dict], which: list[int]) -> str:
    """The text image of the pages, every block with its id in front ("[b12] ..."), so the model can name the
    block of every value. Several pages stand beneath each other, each with a break line."""
    out = []
    for n in which:
        head = BREAK.format(n=n) + "\n" if len(which) > 1 else ""
        out.append(head + _one(pages, body, n))
    return "\n\n".join(out)


def _one(pages: list[dict], body: list[dict], n: int) -> str:
    """One page's text image with the block ids; for a table the id stands at the first cell."""
    page = pages[n - 1]
    marks: dict[int, str] = {}
    for c in blocks_of(body):
        if c["page"] != n or c["type"] == "graphic":
            continue
        box = (c["x"], c["y"], c["width"], c["height"])
        for i, e in enumerate(page["elements"]):
            if i in marks or not e.get("content"):
                continue
            cx, cy = e["x"] + e["width"] / 2, e["y"] + e["height"] / 2
            inside = c["x"] <= cx <= c["x"] + c["width"] and c["y"] <= cy <= c["y"] + c["height"]
            if (e["x"], e["y"], e["width"], e["height"]) == box or (c["type"] == "table-wrap" and inside):
                marks[i] = f"[{c['id']}]"
                break
    return text_image(page, marks)


def prompt(names: list[str], text: str, which: list[int], total: int, fields: Fields,
           contract: Contract, language: str = "") -> str:
    """The task for a few fields and the text image of the pages: per field its question and the contract's
    rule for its place. Before the first field stands the line the task holds as "lead", a question every
    document can answer and whose answer is not used: the model tends to give the first line of a call a
    value whether the document has one or not (measured 12 October 2026 on 60 documents: the field put first
    in a call was filled where nothing belongs far more often than the same field further down). A question
    that names the language of the answer ("{sprache}") gets the language of the document, in the words the task
    holds for it; the model answers in the language of the task otherwise."""
    task = fields.task
    spoken = task.get("languages") or {}
    lines = []
    about = {q["name"]: q for q in questions(fields)}
    for name in names:
        if name in about:
            lines.append(f"- {name}: {about[name]['question']} — Vorgabe: " + json.dumps({"type": "string"}))
            continue
        f = fields.fields[name]
        excerpt = contract.part(f.path) or {"type": "string"}
        question = f.question.replace("{sprache}", spoken.get(language) or spoken.get("") or "")
        lines.append(f"- {name}: {question} — Vorgabe: " + json.dumps(excerpt, ensure_ascii=False))
    lead = task.get("lead")
    if lead:
        lines.insert(0, f"- {lead['name']}: {lead['question']} — Vorgabe: " + json.dumps({"type": "string"}))
    if len(which) == 1:
        intro = task["intro"].replace("{seite}", str(which[0])).replace("{seiten}", str(total))
    else:
        intro = task.get("whole", task["intro"]).replace("{von}", str(len(which))).replace("{seiten}", str(total))
    if task.get("blocks"):
        intro += " " + task["blocks"]
    return (
        intro + "\n\n-----\n" + text + "\n-----\n\n" + task["task"] + "\n" + "\n".join(lines) + "\n\n"
        + task["missing"] + " " + task["form"]
    )


def room(count: int) -> int:
    return max(ROOM[1], ROOM[0] * count)


# block ids named with a value: one per bracket as asked, or several in one ("[b8, b12]", "[b1-b10]"), now and
# then written out ("[block_1]"); a list the room for the answer cut off stays open at the end of the line
# ("[b1, b2, b")
CITED = re.compile(
    r"\s*\[\s*b(?:lock[_ ]?)?\d+(?:\s*[,;/\-–]\s*b(?:lock[_ ]?)?\d+)*\s*\]|\s*\[\s*b\d*(?:\s*[,;/\-–]\s*b\d*)*\s*$"
)


def parse(answer: str, names: list[str]) -> tuple[dict[str, str], dict[str, list[str]]]:
    """The answer lines "name: value" for the fields asked, and per field the block ids named with the value
    ("[b12]"), taken off the value. A field without a line is missing."""
    lines: list[tuple[str, str]] = []
    for line in answer.splitlines():
        m = re.match(r"^[\s\-\*]*([\w _-]{2,40}?)\s*:\s*(.*)$", line)
        if m:
            lines.append((m.group(1).strip().lower(), m.group(2).strip(" \t\"'`")))
    out: dict[str, str] = {}
    cited: dict[str, list[str]] = {}
    taken: dict[int, str] = {}

    def take(i: int, name: str) -> None:
        ids = ["b" + m for group in CITED.findall(lines[i][1]) for m in re.findall(r"b(?:lock[_ ]?)?(\d+)", group)]
        cited[name] = list(dict.fromkeys(ids))
        out[name] = CITED.sub("", lines[i][1]).strip(" \t\"'`")
        taken[i] = name

    # first the exact name, then one that ends with it ("affair number" for number)
    for fits in (lambda key, name: key == name, lambda key, name: key.endswith(name)):
        for i, (key, _) in enumerate(lines):
            for name in names:
                if name not in out and i not in taken and fits(key, name.lower()):
                    take(i, name)
    # the model now and then puts its own word for a name, in the language of the question ("Geschäftsnummer"
    # for number). Then the place of the line tells the field: when the answer has one line per field asked and
    # every line known by its name stands where its field was asked
    if len(lines) == len(names) and all(names[i] == name for i, name in taken.items()):
        for i, name in enumerate(names):
            if name not in out and i not in taken:
                take(i, name)
    return out, cited


def check(f: Field, value: str) -> str:
    """Empty, too short, too long, no date, or '' when the value may stand."""
    if NONE.search(value):
        return "empty"
    count = len(value.split())
    if f.form == "date" and not day(value):
        return "no date"
    if f.min_words is not None and count < f.min_words:
        return "too short"
    if f.max_words is not None and count > f.max_words:
        return "too long"
    return ""


def pair(item: str) -> tuple[str, str]:
    """An entry of a paired field in its two parts: the day it names and the rest, what happened. A part that
    is not there comes back empty."""
    m = PAIR_DAY.search(item)
    if not m:
        return "", item.strip()
    rest = (item[:m.start()] + " " + item[m.end():]).strip(" \t:,;–—-")
    return m.group(0), re.sub(r"\s+", " ", rest)


# words that stand for the co-signers of a submission instead of naming them, in the languages of the documents:
# alone they are no entry of a list of persons ("cofirmatari", "fünf Mitunterzeichnende"), behind a name they
# are left off ("Hofer Ruedi und Mit.", "… et consorts")
_OTHERS = r"(?:mitunterzeichnende[rn]?|mitunterzeichner(?:innen)?|mit\.|cofirmatar[io]|cosignataires?|consorts)"
OTHERS_ALONE = re.compile(r"^\W*(?:\w+\s+)?" + _OTHERS + r"\W*$", re.I)
OTHERS_BEHIND = re.compile(r"\s+(?:und|et|e|ed)\s+" + _OTHERS + r"\W*$", re.I)


def items(f: Field, value: str) -> list[str]:
    """The entries of a field, see `_entries`; of a list of persons without what only stands for further
    persons."""
    out = _entries(f, value)
    if f.form == "list" and f.entity == "person":
        out = [OTHERS_BEHIND.sub("", v).strip() for v in out]
        out = [v for v in out if v and not OTHERS_ALONE.match(v)]
    return out


def _entries(f: Field, value: str) -> list[str]:
    """The values of a field: per entry one for a list, else the value itself. Asked for is the semicolon;
    without one the model mostly separates with a comma. A separator inside round brackets separates nothing:
    "Muster (Bern, PS)" is one name with what the document prints behind it."""
    if f.form != "list":
        return [value.strip()]
    # without semicolon or comma, a dash with a space on both sides sets names apart ("Muster - Beispiel - Probe");
    # the dash inside a name has none ("Muster-Probe")
    if ";" not in value and "," not in value and re.search(r"\s[\-–]\s", value):
        return [v.strip() for v in re.split(r"\s[\-–]\s", value) if v.strip()]
    separator = ";" if ";" in value else ","
    out, depth, one = [], 0, ""
    for char in value:
        depth += 1 if char == "(" else (-1 if char == ")" and depth else 0)
        if char == separator and not depth:
            out.append(one)
            one = ""
        else:
            one += char
    return [v.strip() for v in [*out, one] if v.strip()]


class _Run:
    """One scope of one document: the text image, the pages it shows, and the state the rounds fill."""

    def __init__(self, text: str, which: list[int], total: int, body: list[dict], fields: Fields,
                 contract: Contract, client: Client, values: dict, report: dict, asked: list,
                 log: Path | None):
        self.text, self.which, self.total, self.body = text, which, total, body
        self.language = language_of(body)
        self.fields, self.contract, self.client = fields, contract, client
        self.values, self.report, self.asked, self.log = values, report, asked, log

    def round(self, names: list[str]) -> bool:
        """One call for a few fields: ask, read the lines, check the values and look for them on the page.
        False when no answer came."""
        text = prompt(names, self.text, self.which, self.total, self.fields, self.contract, self.language)
        # the line before the first field is answered too and read past
        lead = [self.fields.task["lead"]["name"]] if self.fields.task.get("lead") else []
        answer = ask(self.client, text, room=room(len(lead + names)), log=self.log, tag="fields " + ",".join(names))
        tokens = (answer.usage or {}).get("prompt_tokens") if answer else None
        self.asked.append({"names": names, "tokens": tokens, "answer": answer.text if answer else None})
        if answer is None:
            return False
        got, cited_all = parse(answer.text, lead + names)
        for name in names:
            if name not in self.fields.fields:
                # a question about the document itself: the word of its list the answer holds; no place on a page
                listed = next(q for q in questions(self.fields) if q["name"] == name).get("one-of", [])
                said = (got.get(name) or "").lower()
                word = next((w for w in listed if re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", said)), None)
                state = "missing" if name not in got else ("named" if word else "empty")
                self.report[name] = {"value": word, "state": state, "items": [], "cited": cited_all.get(name, [])}
                continue
            f = self.fields.fields[name]
            value = got.get(name)
            state = "missing" if value is None else check(f, value)
            entries = [] if state else items(f, value)
            if f.paired and value is not None:
                # entry by entry: one that hands the pattern of the task back does not empty the others
                entries = [i for i in items(f, value) if not NONE.search(i)]
                state = "" if entries else "empty"
            self.report[name] = {"value": value, "state": state or "not on the page", "items": []}
            if f.paired:
                self.report[f.paired] = {"value": None, "state": state or "not on the page", "items": []}
                self.values.pop(f.paired, None)
            if state:
                continue
            self.values.pop(name, None)
            cited = [i for i in cited_all.get(name, []) if find_block(i, self.body, self.which) is not None]
            self.report[name]["cited"] = cited_all.get(name, [])
            for item in entries:
                if f.paired:
                    self._pair(name, f, item, cited)
                else:
                    self._place(name, f, item, cited)
        return True

    def _pair(self, name: str, f: Field, item: str, cited: list[str]) -> None:
        """One entry of a paired field: the day goes to the field named as its pair, the rest stays here. The
        entry stands only with both placed, so that the two fields keep as many values in the same order:
        the record gives each entry of the list the day at the same place. Asked as two lists, an event
        without a place moved every later day up by one, and several days in one answer came out as the
        first of them for every event (found 12 October 2026 in 9 of 9 documents with several days)."""
        mate = f.paired
        first, rest = pair(item)
        reports = {name: self.report[name], mate: self.report[mate]}
        had = {key: len(self.values.get(key, [])) for key in reports}
        seen = {key: len(reports[key]["items"]) for key in reports}
        if first:
            self._place(mate, self.fields.fields[mate], first, cited)
            reports[mate]["value"] = "; ".join(filter(None, [reports[mate]["value"], first]))
        if rest:
            # what happened is mostly worded by the model: where it does not stand literally, the block of
            # its day counts as the block named for it, under the same rule as any named block
            at = [h["block"] for h in self.values.get(mate, [])[had[mate]:]]
            self._place(name, f, rest, [*at, *cited])
        if all(len(self.values.get(key, [])) > had[key] for key in reports):
            return
        for key, report in reports.items():
            hits = self.values.get(key, [])[:had[key]]
            for entry in report["items"][seen[key]:]:
                if entry["block"] is not None:
                    entry["block"], entry["how"] = None, "left out: its pair has no place"
            if hits:
                self.values[key] = hits
                on_page = any(h["how"] in ("literal", "derived") for h in hits)
                report["state"] = "on the page" if on_page else "block from the model"
            else:
                self.values.pop(key, None)
                report["state"] = "not on the page"

    def _place(self, name: str, f: Field, item: str, cited: list[str]) -> None:
        """Literal on the page counts; else the block the model names, with the share of its words there. What
        the model words itself (a free field, the summary) stands nowhere on the page: it keeps the block the
        model names, else the head of the pages asked, and a person looks at it in any case."""
        block = locate(item, self.body, self.which)
        how = "literal" if block is not None else ("cited" if cited else None)
        block = block or (cited[0] if cited else None)
        share = None
        if how == "cited":
            share = overlap(item, block_text(find_block(block, self.body, self.which)))
            # a named block in which (nearly) no word of the value stands is no place; a summary need not share
            # a word with it (the model sums up a French document in German)
            if share <= OVERLAP and not f.free:
                how = "named block without coverage"
                block = None
        if block is None and f.free:
            asked = [c for c in blocks_of(self.body) if c["page"] in self.which and c["type"] != "graphic"]
            block = asked[0]["id"] if asked else None
            how = "composed"
        doubt = None
        if f.free or (f.paired and how == "cited"):
            # what the model worded (a summary, the name of an event that stands at its day) is held against
            # the document it worded it from
            pages = " ".join(block_text(c) for c in blocks_of(self.body) if c["page"] in self.which)
            doubt = unsound(item, pages, self.language)
        text = block_text(find_block(block, self.body, self.which)).strip() if how == "cited" else ""
        # for the title the text of the named block counts when every word of the answer stands in it and
        # the block is no paragraph
        if how == "cited" and f.block_text and covers(item, text) and words(text) <= TITLE_STRETCH * words(item):
            item = text
            how = "literal"
            self.report[name]["note"] = "text of the named block taken"
        # every word of the value in the block, only put together differently: derived, no case for a person
        if how == "cited" and covers(item, text):
            how = "derived"
        entry = {"value": item, "block": block, "how": how}
        if share is not None:
            entry["overlap"] = share
        if doubt is not None:
            entry["approve"] = bool(doubt)
            if doubt:
                entry["doubt"] = doubt
        self.report[name]["items"].append(entry)
        if block is not None:
            hit = {"value": item, "block": block, "how": how}
            if doubt is not None:
                hit["approve"] = bool(doubt)
            self.values.setdefault(name, []).append(hit)
            on_page = self.report[name]["state"] == "on the page" or how in ("literal", "derived")
            away = "at the head of the document" if how == "composed" else "block from the model"
            self.report[name]["state"] = "on the page" if on_page else away
