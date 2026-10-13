"""What code decides about the values of a document without the model, on made-up pages and played answers, without
a document: an event and its day in one line, each entry with its own day; days written out or with slashes; the
place read from the line a document is dated with; a value left out where it stands under another field, where the
field it belongs to has none, or where the document is of another kind; the day of submission as the first event;
what the model worded held against its document; the kind the model names held against the words of the page;
a value no single block holds: over lines of a heading, one letter off, and a day only where it stands.

    python3 tests/settle.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import load_config  # noqa: E402
from docket.fields import filler  # noqa: E402
from docket.fields.fields import questions  # noqa: E402
from docket.fields.filler import check, items, pair, parse  # noqa: E402
from docket.fields.placer import covers, day, fill, locate, within  # noqa: E402
from docket.fields.rules import add_entries, before_day, keep_apart, keep_kinds, unsound  # noqa: E402
from docket.model.client import Answer  # noqa: E402
from docket.pipeline import add_kind, load_contract, load_field_file, load_knowledge  # noqa: E402


def placed(value: str, block: str, how: str = "literal") -> dict:
    return {"value": value, "block": block, "how": how}


def line(text: str) -> list[dict]:
    return [{"id": "b1", "type": "p", "page": 1, "y": 10, "text": text}]


def main() -> int:
    failed = False

    def ok(passed: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not passed
        print(("ok   " if passed else "FAIL ") + text)

    config = load_config()
    contract = load_contract(config)
    fields = load_field_file(config, contract)
    knowledge = load_knowledge(config)

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

    # a day in the spellings of the documents
    ok(day("1er mars 2020") == "2020-03-01" and day("3 marzo 2020") == "2020-03-03"
       and day("12 fevrier 2019") == "2019-02-12"
       and within("03.03.2020", "Lausanne, le 3 mars 2020") and within("01.08.2021", "Bellinzona, 1° agosto 2021")
       and not within("03.03.2020", "le 13 mars 2020"),
       "a day written out in French or Italian is read, and found on the page for the same day in figures")
    ok(day("14/11/2023") == "2023-11-14" and within("14.11.2023", "Dépôt: 14/11/2023")
       and day("Geschäft 2023/24") == "",
       "a day written with slashes is read and found on the page")
    ok(within("05.03.2021", "Bellinzona, 05 marzo 2021") and day("14 DEC. 2018") == "2018-12-14"
       and within("14.12.2018", "Déposé le 14 DEC. 2018") and day("3 sett. 2020") == "2020-09-03"
       and day("5 jui 2020") == "" and within("09.03.2021", "Sitzung vom 9.3.21 um 14 Uhr")
       and not within("09.03.2021", "Sitzung vom 19.3.21") and within("12.03.2020", "12.03.2020 14 Uhr"),
       "a zero before the day, a month cut short and a year of two digits are the same day; the start of a name "
       "that two months share is no month")

    # a value no single block holds
    page = [{"id": "b1", "type": "p", "page": 1, "y": 10, "text": "INTERPELLANZA"},
            {"id": "b2", "type": "p", "page": 1, "y": 20, "text": "Accesso alla sala del consiglio"},
            {"id": "b3", "type": "p", "page": 1, "y": 30, "text": "Hofer Ruedi Muster Hans"},
            {"id": "b4", "type": "p", "page": 1, "y": 40, "text": "Beispiel Carla"},
            {"id": "b5", "type": "p", "page": 1, "y": 50, "text": "An den Grossen Gemeinderat (November 2019)"},
            {"id": "b6", "type": "p", "page": 2, "y": 10, "text": "Probe Erwin"}]
    ok(locate("Interpellanza Accesso alla sala del consiglio", page, [1, 2]) == "b1"
       and locate("Hans Beispiel", page, [1, 2]) is None and locate("Beispiel Carla An den", page, [1, 2]) == "b4"
       and locate("An den Grossen Gemeinderat (November 2019) Probe", page, [1, 2]) is None,
       "a heading set in two lines stands on the page, at its first line; the end of one row of names and the "
       "start of the next is no name, and nothing runs from one page to the next")
    ok(covers("Grosser Gemeinderat", page[4]["text"]) and not covers("Kleiner Gemeinderat", page[4]["text"])
       and not covers("Hofer Rudi", page[2]["text"]) and not covers("November 2018", page[4]["text"]),
       "held against the block the model names, a word may differ in one letter from five letters on; another "
       "word, a short word or a number may not")
    reply = "language: de\naddressee: Grosser Gemeinderat [b5]\ndate: 14.11.2019 [b5]"
    there: dict = {}
    noted: dict = {}
    filler.ask = lambda client, text, **_: Answer(reply, 200, {"prompt_tokens": 0}, "stop")
    try:
        filler._Run("", [1], 2, page, fields, contract, None, there, noted, [], None).round(["addressee", "date"])
    finally:
        filler.ask = asked_before
    ok(there.get("addressee", [{}])[0].get("how") == "derived" and "date" not in there
       and noted["date"]["items"][0]["block"] is None,
       "a day the page does not hold has no place, though the block named holds its month and year; the body "
       "named one letter off stands as derived")
    one_line = "title: Eine Frage [b2] number: 12 [b1] date: 03.03.2020 [b3]"
    ok(parse(one_line, ["number", "title", "date"])
       == ({"title": "Eine Frage", "number": "12", "date": "03.03.2020"},
           {"title": ["b2"], "number": ["b1"], "date": ["b3"]})
       and parse("title: Antwort auf [b2] number: 5", ["title"])[0]["title"] == "Antwort auf number: 5",
       "an answer that sets several fields in one line is cut where a field asked follows a named block")

    # the place: read by code from the line a document is dated with, no list of places behind it
    dated = ("Herisau, 22. August 2017 / aje", "Lausanne, le 3 mars 2020", "Bellinzona, 05 marzo 2024",
             "Zürich und Winterthur, 26. November 2018", "Neuhausen am Rheinfall, den 2. Mai 2019")
    found = [before_day(line(t)) for t in dated]
    ok([hit and hit[0] for hit in found]
       == ["Herisau", "Lausanne", "Bellinzona", "Zürich und Winterthur", "Neuhausen am Rheinfall"],
       "the place is what stands before the day in a line of a place and a day, in German, French and Italian")
    ok(before_day(line("Der Stadtrat hat am 3. März 2020 beschlossen")) is None
       and before_day(line("Frage vom 3.3.2020, eingereicht")) is None,
       "a day in running text is no line of a place and a day: the place stays empty")
    other = ("un référendum contre la LAT, le 18 septembre 2012, ainsi que", "en burn-out (RTS, le 11 août 2017)",
             "selon le Conseil, le 3 mars 2020, la motion", "Sitzung vom Montag, 3. März 2020",
             "Mardi, le 3 mars 2020", "ED/P255460 Basel, 27. Mai 2026",
             "sur l'axe Chavornay-Vallorbe. Yverdon-les-Bains, le 26 février 2008.",
             "adopté, en séance du Conseil d'Etat, à Lausanne, le 4 juillet 2018.", "St. Gallen, 12.05.2020")
    odd = [before_day(line(t)) for t in other]
    ok([hit and hit[0] for hit in odd]
       == [None, None, None, None, None, "Basel", "Yverdon-les-Bains", "Lausanne", "St. Gallen"],
       "an abbreviation, a day of the week, a name in brackets or in running text before a day is no place; "
       "a file reference in front is left off")

    # a value that stands under another field is left out; a field has no value without the one it belongs to
    hits = {"authors": [placed("FDP Fraktion", "b4")], "parliament": [placed("Kantonsrat", "b1")],
            "party": [placed("FDP-Fraktion", "b4"), placed("SP", "b5")], "on-behalf-of": [placed("Kantonsrat", "b1")]}
    notes = {n: {"value": "", "state": "on the page", "items": [dict(h) for h in hits[n]]}
             for n in ("party", "on-behalf-of")}
    keep_apart(hits, notes, fields)
    ok([h["value"] for h in hits["party"]] == ["SP"] and "on-behalf-of" not in hits
       and notes["on-behalf-of"]["state"] == "empty" and notes["party"]["items"][0]["block"] is None,
       "a party or on-behalf-of that already stands under the submitters or as a body of the document is left out")
    session = {"session": [placed("Einwohnerrat", "b1")], "parliament": [placed("Einwohnerrat", "b1")],
               "session-date": [placed("03.03.2020", "b1")],
               "party": [placed("CVP Glarus", "b2")], "polity": [placed("Glarus", "b3")]}
    notes = {n: {"value": "", "state": "on the page", "items": [dict(h) for h in session[n]]}
             for n in ("session", "session-date", "party")}
    keep_apart(session, notes, fields)
    ok("session" not in session and "session-date" not in session
       and [h["value"] for h in session.get("party", [])] == ["CVP Glarus"],
       "a session named like the parliament is none, and its day goes with it; a party named after its town stays")

    signed = {"authors": [placed("Hans Muster", "b1")],
              "cosigners": [placed("Hans Muster", "b1"), placed("Carla Beispiel", "b2")]}
    notes = {"cosigners": {"value": "", "state": "on the page", "items": [dict(h) for h in signed["cosigners"]]}}
    keep_apart(signed, notes, fields)
    ok([h["value"] for h in signed["cosigners"]] == ["Carla Beispiel"],
       "who submitted is not a co-signer once more")

    # what is no value, and what is no person
    party = fields.fields["party"]
    ok(all(check(party, v) == "empty" for v in ("—", "Non", "Nein", "No", "(porte-parole)"))
       and check(party, "Noé Dupont") == "" and parse("party: — [block_1]", ["party"])[0]["party"] == "—",
       "a bare no, a lone bracket and a dash with a block written out are no value")
    names = fields.fields["cosigners"]
    ok(items(names, "Muster - Beispiel - Probe") == ["Muster", "Beispiel", "Probe"]
       and items(names, "Muster-Probe; Beispiel") == ["Muster-Probe", "Beispiel"],
       "names set apart by a dash with spaces are taken one by one; the dash inside a name sets nothing apart")
    people = fields.fields["authors"]
    ok(items(people, "Hans Muster; fünf Mitunterzeichnende") == ["Hans Muster"]
       and items(people, "Carla Beispiel e cofirmatari") == ["Carla Beispiel"]
       and items(people, "Hofer Ruedi und Mit.") == ["Hofer Ruedi"]
       and items(people, "Anna Muster; Beat Meier") == ["Anna Muster", "Beat Meier"],
       "a word that stands for further co-signers is no entry of a list of persons and is left off behind a name")

    related = fields.fields["related"]
    ok(items(related, "1; 2; 3") == [] and items(related, "21.337; P 7") == ["21.337", "P 7"]
       and items(fields.fields["number"], "N/ref") == [] and items(fields.fields["number"], "M 185") == ["M 185"],
       "the number of an affair holds a digit and is more than one digit by itself: the numbers of the points "
       "of a text are none")

    # the day an affair was submitted is its first event, unless the events read from the document hold that day
    read = {"date": [placed("03.03.2020", "b1")], "event": [placed("Beantwortung im Stadtrat", "b2")],
            "event-date": [placed("12.05.2020", "b2")]}
    add_entries(read, {}, fields, "fr")
    held = {"date": [placed("03.03.2020", "b1")], "event": [placed("Motion eingereicht", "b1")],
            "event-date": [placed("3. März 2020", "b1")]}
    add_entries(held, {}, fields, "de")
    label = fields.fields["date"].entry.get("label", {}).get("fr")
    ok([h["value"] for h in read["event"]] == [label, "Beantwortung im Stadtrat"]
       and [h["value"] for h in read["event-date"]] == ["03.03.2020", "12.05.2020"]
       and read["event"][0]["block"] == "b1" and len(held["event"]) == 1,
       "the day an affair was submitted is its first event, named in the language of the document; "
       "not twice where the document names it")

    # the day an affair was submitted is read from the submission itself, not from an answer or a report
    asked_name = next(q["name"] for q in questions(fields) if q.get("role") == "kind")
    for named, stays in (("submission", True), ("answer", False), (None, True)):
        read = {"date": [placed("03.03.2020", "b1")]}
        told = {"date": {"value": "03.03.2020", "state": "on the page", "items": [dict(read["date"][0])]},
                asked_name: {"value": named, "state": "named" if named else "empty", "items": []}}
        keep_kinds(read, told, fields)
        ok(("date" in read) is stays,
           f"the date of submission {'stays' if stays else 'is left out'} "
           f"where the model names the document {named or 'nothing'}")

    for name in ("cosigners", "on-behalf-of"):
        read = {name: [placed("Carla Beispiel", "b2")]}
        told = {name: {"value": "Carla Beispiel", "state": "on the page", "items": [dict(read[name][0])]},
                asked_name: {"value": "answer", "state": "named", "items": []}}
        keep_kinds(read, told, fields)
        ok(name not in read,
           f"{name} is read from the submission only: who signs an answer did not co-sign the affair")

    # what the model worded is not looked over each time, only where it leaves its document
    paper = ("Der Stadtrat wird gebeten zu prüfen, ob im Jahr 2024 die Öffnungszeiten der Bibliothek verlängert "
             "werden können. Die Motion verlangt zusätzliche Stunden und Kosten von 12000 Franken.")
    said = [unsound(t, paper, "de") for t in (
        "Die Motion verlangt, die Öffnungszeiten der Bibliothek 2024 zu verlängern, mit Kosten von 12000 Franken.",
        "Die Interpellation fragt nach dem Stand der Sanierung der Kantonsstrasse und den Folgen für den Verkehr.",
        "Die Motion verlangt, die Öffnungszeiten der Bibliothek zu verlängern, mit Kosten von 45000 Franken.")]
    ok(said[0] == "" and "words" in said[1] and "number" in said[2],
       "a summary of its document is sound; one of another matter, or one with a number the document does not hold, "
       "is not")
    sheet = [{"id": "b1", "type": "p", "page": 1, "y": 10, "text": paper}]
    summary = fields.fields["summary"]
    for text, marked in (("Die Motion verlangt, die Öffnungszeiten der Bibliothek zu verlängern.", False),
                         ("Zzz qqq xxx yyyy.", True)):
        values, report = {}, {"summary": {"value": text, "state": "not on the page", "items": []}}
        run = filler._Run("", [1], 1, sheet, fields, contract, None, values, report, [], None)
        run._place("summary", summary, text, [])
        record, _ = fill({"docs": {"data": [{"body": sheet}]}}, 1, values, fields, contract, sheet)
        mark = json.dumps(record).count('"approve": true')
        ok(values["summary"][0]["approve"] is marked and (mark == 1) is marked,
           "a summary that leaves its document is marked for a person" if marked
           else "a sound summary stands without a mark, in the record too")

    # the kind the model names, held against the words of the first page
    page = [{"elements": [{"type": "text", "content": "Interpellation", "fontSize": 16}]}]
    blocks = [{"id": "b1", "type": "sec", "page": 1, "y": 10, "title": "Begründung"},
              {"id": "b2", "type": "sig-block", "page": 1, "y": 90}]

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
    ok(other["kind"] == "answer" and other["approve"] is False and "approve" not in with_other["sources"][0]
       and with_other["docs"]["data"][0]["article-type"] == "answer" and "submission" in other["why"],
       "where they differ, the model's kind stands without a mark, and what the words say is noted with it")
    bare = [{"elements": [{"type": "text", "content": "Text", "fontSize": 10}]}]
    silent = add_kind({"docs": {"data": [{"id": 1, "body": line("Text")}]}}, bare, knowledge, None, "answer")
    ok(silent is not None and silent["kind"] == "answer" and silent["approve"] is False,
       "where the words of the page say nothing, the model's kind stands without a mark: nothing speaks against it")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
