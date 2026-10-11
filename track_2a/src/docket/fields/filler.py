"""Asks the fields over the document and takes what stands on the page.

The model gets the first pages as a text image, every block with its id in front, and six questions at once,
each with the contract's rule for its place. Fields over the whole document get all pages while the text image
fits the frame. What it answers goes through the placer: literal on the page, derived from the named block,
cited with a word in the named block, or dropped. Fields without a line or with a refused value are asked once
more. Values seen so far are not offered in the prompt (measured 6 October 2026: more values that are not on
the page), but they are kept, so a person can look at them.
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
from docket.fields.fields import Field, Fields
from docket.fields.placer import (
    block_text, blocks_of, covers, day, fill, find_block, locate, overlap, plain, words,
)
from docket.model.client import Client, ask

# this many fields in one call
BUNDLE = 6

# room for the answer: this many tokens per field, at least this many
ROOM = (50, 400)

# instead of the dash the model sometimes writes out that nothing is there, or returns the pattern of the task
NONE = re.compile(
    r"^[\-–—\s]*$|nicht angegeben|keine angabe|nicht vorhanden|nicht genannt|nicht ersichtlich|unbekannt"
    r"|TT\.MM\.JJJJ",
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
    for scope, which in (("first", first), ("all", whole_pages(pages, body))):
        names = [n for n, f in fields.fields.items() if f.pages == scope]
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
        for k in range(0, len(remaining), BUNDLE):
            bundle = remaining[k:k + BUNDLE]
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
        # the follow-up: what had no line or was refused, once more, at most one bundle
        again = [n for n in remaining if report.get(n, {}).get("state") in AGAIN][:BUNDLE]
        if again and not client.halted:
            before = {n: report[n]["state"] for n in again}
            if run.round(again):
                for name in again:
                    report[name]["asked again"] = before[name]
    return _finish(record, values, report, asked, fields, contract, body, knowledge)


def _finish(record: dict, values: dict, report: dict, asked: list, fields: Fields, contract: Contract,
            body: list[dict], knowledge: Knowledge) -> tuple[dict, dict]:
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
    rule for its place. A question that names the language of the answer ("{sprache}") gets the language of
    the document, in the words the task holds for it; the model answers in the language of the task
    otherwise."""
    task = fields.task
    spoken = task.get("languages") or {}
    lines = []
    for name in names:
        f = fields.fields[name]
        excerpt = contract.part(f.path) or {"type": "string"}
        question = f.question.replace("{sprache}", spoken.get(language) or spoken.get("") or "")
        lines.append(f"- {name}: {question} — Vorgabe: " + json.dumps(excerpt, ensure_ascii=False))
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


# block ids named with a value: one per bracket as asked, or several in one ("[b8, b12]", "[b1-b10]"); a list
# the room for the answer cut off stays open at the end of the line ("[b1, b2, b")
CITED = re.compile(r"\s*\[\s*b\d+(?:\s*[,;/\-–]\s*b\d+)*\s*\]|\s*\[\s*b\d*(?:\s*[,;/\-–]\s*b\d*)*\s*$")


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
        ids = [m for group in CITED.findall(lines[i][1]) for m in re.findall(r"b\d+", group)]
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


def items(f: Field, value: str) -> list[str]:
    """The values of a field: per entry one for a list, else the value itself. Asked for is the semicolon;
    without one the model mostly separates with a comma. A separator inside round brackets separates nothing:
    "Muster (Bern, PS)" is one name with what the document prints behind it."""
    if f.form != "list":
        return [value.strip()]
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
        answer = ask(self.client, text, room=room(len(names)), log=self.log, tag="fields " + ",".join(names))
        tokens = (answer.usage or {}).get("prompt_tokens") if answer else None
        self.asked.append({"names": names, "tokens": tokens, "answer": answer.text if answer else None})
        if answer is None:
            return False
        got, cited_all = parse(answer.text, names)
        for name in names:
            f = self.fields.fields[name]
            value = got.get(name)
            state = "missing" if value is None else check(f, value)
            self.report[name] = {"value": value, "state": state or "not on the page", "items": []}
            if state:
                continue
            self.values.pop(name, None)
            cited = [i for i in cited_all.get(name, []) if find_block(i, self.body, self.which) is not None]
            self.report[name]["cited"] = cited_all.get(name, [])
            for item in items(f, value):
                self._place(name, f, item, cited)
        return True

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
        self.report[name]["items"].append(entry)
        if block is not None:
            self.values.setdefault(name, []).append({"value": item, "block": block, "how": how})
            on_page = self.report[name]["state"] == "on the page" or how in ("literal", "derived")
            away = "at the head of the document" if how == "composed" else "block from the model"
            self.report[name]["state"] = "on the page" if on_page else away
