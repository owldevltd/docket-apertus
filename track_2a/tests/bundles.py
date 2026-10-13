"""Which fields share a call, without a model and without a document: every field of a scope is asked in exactly
one call, no call asks more than BUNDLE fields, fields that name the same word under "together" share a call of
their own, and the fields of the contributors (who submitted, their party, in whose name, who co-signed) are such
a group over the whole document. An event and its day are asked in one line: every entry keeps its own day, on a
made-up page with a played answer. The place is read by code from a line of a place and a day and is not asked; a
party does not repeat what stands under the submitters or the bodies; a bare no is no value. What a document is
in its affair is asked from the model out of a closed list and held against the words of the first page: the same
from both stands without a mark, anything else is for a person. A date the model does not give is read from the
line the document is dated with; a day written with slashes is read; names set apart by a dash with spaces are
taken one by one.

    python3 tests/bundles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import load_config  # noqa: E402
from docket.fields import filler  # noqa: E402
from docket.fields.fields import Field, Fields  # noqa: E402
from docket.fields.filler import (  # noqa: E402
    BUNDLE, before_day, bundles, check, day_in_line, items, keep_apart, pair, parse, prompt, read_otherwise,
)
from docket.fields.placer import day, fill, within  # noqa: E402
from docket.model.client import Answer  # noqa: E402
from docket.pipeline import add_kind, load_contract, load_field_file, load_knowledge  # noqa: E402


def main() -> int:
    failed = False

    def ok(passed: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not passed
        print(("ok   " if passed else "FAIL ") + text)

    config = load_config()
    fields = load_field_file(config, load_contract(config))
    for scope in ("first", "all"):
        names = [n for n, f in fields.fields.items() if f.pages == scope]
        calls = bundles(names, fields)
        flat = [n for call in calls for n in call]
        ok(sorted(flat) == sorted(names) and len(flat) == len(set(flat)) and all(0 < len(c) <= BUNDLE for c in calls),
           f"scope {scope}: every one of the {len(names)} fields in exactly one of {len(calls)} calls, none over {BUNDLE}")
        words = {fields.fields[n].together for n in names} - {""}
        alone = all(
            len({fields.fields[n].together for n in call}) == 1
            for call in calls if any(fields.fields[n].together for n in call)
        )
        whole = all(sum(1 for call in calls if any(fields.fields[n].together == w for n in call)) == 1 for w in words)
        ok(alone and whole, f"scope {scope}: fields that belong together share one call and nothing else is asked in it")
    people = ["authors", "party", "on-behalf-of", "cosigners"]
    ok(all(fields.fields[n].pages == "all" for n in people) and len({fields.fields[n].together for n in people}) == 1
       and fields.fields["authors"].together != "",
       "who submitted, their party, in whose name and who co-signed are asked together over the whole document")

    # made-up fields: the order of the file holds, a group stands where its first field stands, a large group is cut
    def made(name: str, word: str = "") -> Field:
        return Field(name=name, path=[name], question=name, together=word)

    plain = Fields({}, {f.name: f for f in [made("a"), made("b", "x"), made("c"), made("d", "x"), made("e")]}, {})
    ok(bundles(list(plain.fields), plain) == [["a"], ["b", "d"], ["c", "e"]],
       "a group is asked where its first field stands; what stood before it goes first, the rest after it")
    many = Fields({}, {f.name: f for f in [made(f"g{i}", "x") for i in range(BUNDLE + 2)]}, {})
    ok([len(c) for c in bundles(list(many.fields), many)] == [BUNDLE, 2], "a group larger than a call is cut")
    # the line before the first field: asked in every call, its answer read past
    contract = load_contract(config)
    lead = fields.task.get("lead") or {}
    asked = [row for row in prompt(["number", "title"], "", [1], 1, fields, contract).split("\n") if row.startswith("- ")]
    ok(bool(lead) and asked[0].startswith("- " + lead["name"] + ": ") and asked[1].startswith("- number: ")
       and lead["name"] not in fields.fields,
       "every call starts with a line that is no field, before the first field asked")
    got, _ = parse("language: de [b1]\nGeschäftsnummer: 1 [b2]\ntitle: A title [b3]", [lead.get("name", ""), "number", "title"])
    ok(got.get("number") == "1" and got.get("title") == "A title",
       "the answer to that line is read past: the fields behind it keep their lines, also by their place")
    ok(bool(fields.fields["keywords"].when), "printed keywords are asked only where a word for them stands on the page")
    # an event and its day in one line, entry by entry
    ok(fields.fields["event"].paired == "event-date" and pair("03.03.2020 Eingereicht") == ("03.03.2020", "Eingereicht")
       and pair("Beantwortung im Stadtrat, 12. Mai 2020") == ("12. Mai 2020", "Beantwortung im Stadtrat")
       and pair("Vertagt") == ("", "Vertagt"),
       "an entry of a paired field is cut into its day and what happened, wherever the day stands in it")
    body = [{"id": "b1", "type": "p", "page": 1, "y": 10, "text": "Eingereicht am 3. März 2020"},
            {"id": "b2", "type": "p", "page": 1, "y": 20, "text": "Beantwortung im Stadtrat: 12.05.2020"},
            {"id": "b3", "type": "p", "page": 1, "y": 30, "text": "Le Conseil en prend acte le 1er juin 2020."}]
    said = ("language: de\nevent: 03.03.2020 Eingereicht; 01.01.2021 Kenntnis genommen im Plenum; "
            "12.05.2020 Beantwortung im Stadtrat; TT.MM.JJJJ Bezeichnung; Vertagt; 01.06.2020 Prise d'acte du Conseil")
    sent: list[str] = []

    def played(client, text, **_):
        sent.append(text)
        return Answer(said, 200, {"prompt_tokens": 0}, "stop")

    values: dict = {}
    report: dict = {}
    asked_before = filler.ask
    filler.ask = played
    try:
        filler._Run("", [1], 1, body, fields, contract, None, values, report, [], None).round(["event"])
    finally:
        filler.ask = asked_before
    ok("- event: " in sent[0] and "- event-date: " not in sent[0], "the day has no line of its own in the call")
    ok([h["value"] for h in values.get("event", [])][:2] == ["Eingereicht", "Beantwortung im Stadtrat"]
       and [h["value"] for h in values.get("event-date", [])][:2] == ["03.03.2020", "12.05.2020"]
       and len(values.get("event", [])) == len(values.get("event-date", [])) == 3,
       "an entry without a place, without a day or with the pattern of the task is left out and moves no other")
    last = values.get("event", [{}])[-1]
    ok(last.get("value") == "Prise d'acte du Conseil" and last.get("block") == "b3" and last.get("how") == "cited",
       "what happened, worded by the model, takes the block of its day when a word of it stands there, as cited")
    record, _ = fill({"docs": {"data": [{"body": body}]}}, 1, values, fields, contract, body)
    days = [(next(iter(e["title"].values())), e["date"]) for e in record["events"]["data"]]
    ok(days == [("Eingereicht", "2020-03-03"), ("Beantwortung im Stadtrat", "2020-05-12"),
                ("Prise d'acte du Conseil", "2020-06-01")],
       "in the record every event stands with the day of its own entry")
    ok(day("1er mars 2020") == "2020-03-01" and day("3 marzo 2020") == "2020-03-03" and day("12 fevrier 2019") == "2019-02-12"
       and within("03.03.2020", "Lausanne, le 3 mars 2020") and within("01.08.2021", "Bellinzona, 1° agosto 2021")
       and not within("03.03.2020", "le 13 mars 2020"),
       "a day written out in French or Italian is read, and found on the page for the same day in figures")
    # the place: read by code from the line a document is dated with, never asked, no list of places behind it
    def line(text: str) -> list[dict]:
        return [{"id": "b1", "type": "p", "page": 1, "y": 10, "text": text}]

    found = [before_day(line(t)) for t in ("Herisau, 22. August 2017 / aje", "Lausanne, le 3 mars 2020", "Bellinzona, 05 marzo 2024",
                                           "Zürich und Winterthur, 26. November 2018", "Neuhausen am Rheinfall, den 2. Mai 2019")]
    ok([hit and hit[0] for hit in found] == ["Herisau", "Lausanne", "Bellinzona", "Zürich und Winterthur", "Neuhausen am Rheinfall"],
       "the place is what stands before the day in a line of a place and a day, in German, French and Italian")
    ok(before_day(line("Der Stadtrat hat am 3. März 2020 beschlossen")) is None and before_day(line("Frage vom 3.3.2020, eingereicht")) is None,
       "a day in running text is no line of a place and a day: the place stays empty")
    calls = [n for scope in ("first", "all") for call in bundles([n for n, f in fields.fields.items() if f.pages == scope and not f.reader], fields) for n in call]
    ok(fields.fields["place"].reader == "before-day" and "place" not in calls, "the place is read by code and stands in no call")
    # a party is not the submitter once more and not a body of the document
    hits = {"authors": [{"value": "FDP Fraktion", "block": "b4", "how": "literal"}],
            "parliament": [{"value": "Kantonsrat", "block": "b1", "how": "literal"}],
            "party": [{"value": "FDP-Fraktion", "block": "b4", "how": "literal"}, {"value": "SP", "block": "b5", "how": "literal"}],
            "on-behalf-of": [{"value": "Kantonsrat", "block": "b1", "how": "literal"}]}
    notes = {n: {"value": "", "state": "on the page", "items": [dict(h) for h in hits[n]]} for n in ("party", "on-behalf-of")}
    keep_apart(hits, notes, fields)
    ok([h["value"] for h in hits["party"]] == ["SP"] and "on-behalf-of" not in hits and notes["on-behalf-of"]["state"] == "empty"
       and notes["party"]["items"][0]["block"] is None,
       "a party or on-behalf-of that already stands under the submitters or as a body of the document is left out")
    party = fields.fields["party"]
    ok(all(check(party, v) == "empty" for v in ("—", "Non", "Nein", "No", "(porte-parole)")) and check(party, "Noé Dupont") == ""
       and parse("party: — [block_1]", ["party"])[0]["party"] == "—",
       "a bare no, a lone bracket and a dash with a block written out are no value")
    # what the document is: one word of a closed list from the model, held against the words of the first page
    knowledge = load_knowledge(config)
    asked_kind = next((q for q in filler.questions(fields) if q.get("role") == "kind"), None)
    listed = [k["id"] for k in knowledge.kinds if k.get("rule") is not False]
    ok(asked_kind is not None and sorted(asked_kind["one-of"]) == sorted(listed) and asked_kind["name"] not in fields.fields,
       "the kinds the model may name are the kinds of the knowledge file that a rule can set; the question is no field")
    values, report = {}, {}
    filler.ask = lambda client, text, **_: Answer("language: de\ndocument-kind: answer (die Antwort der Regierung) [b1]", 200, {}, "stop")
    try:
        filler._Run("", [1], 1, body, fields, contract, None, values, report, [], None).round([asked_kind["name"]])
    finally:
        filler.ask = asked_before
    ok(report[asked_kind["name"]]["value"] == "answer" and asked_kind["name"] not in values,
       "of the answer the word of the list is kept; it is looked for on no page")
    page = [{"elements": [{"type": "text", "content": "Interpellation", "fontSize": 16}]}]
    blocks = [{"id": "b1", "type": "sec", "page": 1, "y": 10, "title": "Begründung"}, {"id": "b2", "type": "sig-block", "page": 1, "y": 90}]

    def kind(named):
        record = {"docs": {"data": [{"id": 1, "body": blocks}]}}
        return add_kind(record, page, knowledge, "Interpellation", named), record

    alone, _ = kind(None)
    same, with_same = kind("submission")
    other, with_other = kind("answer")
    ok(alone is not None and alone["kind"] == "submission" and alone["approve"] is True,
       "the words of the first page alone give a kind for a person to look at")
    ok(same["kind"] == "submission" and same["approve"] is False and "approve" not in with_same["sources"][0],
       "the same kind from the words and from the model stands without a mark")
    ok(other["kind"] == "answer" and other["approve"] is True and with_other["sources"][0].get("approve") is True
       and with_other["docs"]["data"][0]["article-type"] == "answer",
       "where they differ, the model's kind stands, for a person to look at")
    # the date: where the model gave none with a place, the day of the line the document is dated with
    dated = [{"id": "b7", "type": "p", "page": 2, "y": 10, "text": "Delémont, le 27 février 2020"}]
    hits, notes = {}, {"date": {"value": "-", "state": "empty", "items": []}}
    read_otherwise(hits, notes, fields, dated)
    kept = {"date": [{"value": "03.03.2020", "block": "b1", "how": "literal"}]}
    read_otherwise(kept, {"date": {"value": "03.03.2020", "state": "on the page", "items": []}}, fields, dated)
    ok(fields.fields["date"].otherwise == "day-in-line" and day_in_line(dated) == ("27 février 2020", "b7")
       and hits.get("date", [{}])[0].get("block") == "b7" and notes["date"]["state"] == "on the page"
       and kept["date"][0]["value"] == "03.03.2020",
       "a date the model does not give is read from the line of a place and a day; the model's own date stays")
    ok(day("14/11/2023") == "2023-11-14" and within("14.11.2023", "Dépôt: 14/11/2023") and day("Geschäft 2023/24") == "",
       "a day written with slashes is read and found on the page")
    names = fields.fields["cosigners"]
    ok(items(names, "Muster - Beispiel - Probe") == ["Muster", "Beispiel", "Probe"] and items(names, "Muster-Probe; Beispiel") == ["Muster-Probe", "Beispiel"],
       "names set apart by a dash with spaces are taken one by one; the dash inside a name sets nothing apart")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
