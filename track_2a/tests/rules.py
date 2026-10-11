"""Learning from decisions, without a model: two changes by hand with the same pattern on the same field
propose a rule and apply nothing; the proposal says how many values it would change; a person's yes changes
them, each with a review by "rule"; a person's no keeps the rule from being proposed again; a decision by hand
that speaks against a rule takes the proposal away; the same value becoming the same value is a pattern of its
own; a person's confirmation of a value a rule set is counted on the rule, and a switched-off rule applies
nothing new. And the label: two values a person set to what the document prints beside the same label propose
that this field is what stands at that label; accepted, it holds for every document that prints the label with
another value, and for none that does not print it or leaves its box empty.

    python3 tests/rules.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract  # noqa: E402
from docket.store.files import FileStore  # noqa: E402
from docket.store.review import sources_of  # noqa: E402
from docket.store.rules import apply, labels, pattern, patterns  # noqa: E402

PLACES = ["Kanton Zürich", "Kanton Bern", "Kanton Aargau", "Kanton Luzern", "Stadt Bern"]


def record_with(place: str) -> dict:
    block = {"id": "b1", "page": 1, "type": "p", "x": 0, "y": 0, "width": 10, "height": 10, "text": place}
    return {
        "schema": "0.8",
        "docs": {"data": [{"id": 1, "name": "doc-" + place.lower().replace(" ", "-"), "page-count": 1,
                           "body": [block]}]},
        "custom-meta": [{"meta-name": "polity", "meta-value": place,
                         "source": {"doc": 1, "block": "b1", "how": "cited", "approve": True}}],
    }


def record_with_label(read: str, printed: str | None) -> dict:
    """A record whose polity was read from a paragraph, while the document prints it with a label (or not)."""
    record = record_with(read)
    if printed is not None:
        record["docs"]["data"][0]["body"].append(
            {"id": "b2", "page": 1, "type": "def-list", "x": 0, "y": 20, "width": 10, "height": 10,
             "items": [{"term": "Gemeinde:", "def": printed}]})
    return record


def main() -> int:
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    cases = [("Kanton Zürich", "Zürich", "prefix-off"), ("15.5098.01", "15.5098", "suffix-off"),
             ("11 S230", "11 5230", "digits"), ("motion", "Motion", "spelling"), ("Lüthold", "Katrin", None)]
    for before, after, kind in cases:
        got = pattern(before, after)
        check((got or {}).get("kind") == kind, f"pattern {before!r} -> {after!r}: {got}")

    config = load_config()
    contract = load_contract(config)
    source = "custom-meta.0.source"

    def fresh(tmp: str, name: str, places: list[str]) -> tuple[FileStore, App, Jobs]:
        store = FileStore(Path(tmp) / name)
        for i, place in enumerate(places):
            store.put_affair(f"nr-{i}", record_with(place), [{"name": f"doc-{i}", "id": 1, "pages": 1}])
        jobs = Jobs(type(config)(**{**config.__dict__, "storage_dir": Path(tmp) / (name + "-runs")}))
        return store, App(store, contract, config, jobs), jobs

    def change(app: App, i: int, after: str) -> tuple[int, dict]:
        return app.decide(f"nr-{i}", {"source": source, "decision": "changed", "by": "test", "after": after})

    def value(store: FileStore, i: int) -> dict:
        return sources_of(store.get_affair(f"nr-{i}")["record"])[0]

    with tempfile.TemporaryDirectory() as tmp:
        # two changes propose, a yes applies
        store, app, jobs = fresh(tmp, "yes", PLACES)
        status, answer = change(app, 0, "Zürich")
        check(status == 200 and answer["proposals"] == [], "the first change proposes nothing")
        status, answer = change(app, 1, "Bern")
        proposals = answer["proposals"]
        check(status == 200 and len(proposals) == 1, f"the second change with the same pattern proposes one rule: "
              f"{[(r['kind'], r['parameter']) for r in proposals]}")
        rule = proposals[0]
        check(rule["kind"] == "prefix-off" and rule["parameter"] == "Kanton " and rule["state"] == "proposed"
              and rule["count"] == 2, "the rule takes 'Kanton ' off and stands proposed after two changes")
        reach = rule["reach"]
        check(reach["count"] == 2 and reach["affairs"] == 2
              and {e["after"] for e in reach["examples"]} == {"Aargau", "Luzern"},
              f"it says what it would change: {reach['count']} values in {reach['affairs']} affairs")
        check(value(store, 2)["value"] == "Kanton Aargau" and value(store, 3)["review"] is None,
              "nothing is changed before a person answers")
        kinds = sorted((r["kind"], r["state"]) for r in store.get_rules())
        check(kinds == [("prefix-off", "proposed"), ("value", "counting"), ("value", "counting")],
              f"each change also counts as its value becoming that value: {kinds}")
        listed = next(r for r in app.rules() if r["id"] == rule["id"])
        check(listed["reach"]["count"] == 2, "the list of rules shows the proposal with its reach")

        status, rule = app.answer_rule(rule["id"], True, "test")
        check(status == 200 and rule["state"] == "active" and rule["applied"] == 2, "a yes makes the rule active")
        fourth = value(store, 3)
        review = fourth["review"] or {}
        check(fourth["value"] == "Luzern" and review.get("by") == "rule" and review.get("rule") == rule["id"]
              and value(store, 2)["value"] == "Aargau", "the values that fit are changed by the rule")
        fifth = value(store, 4)
        check(fifth["value"] == "Stadt Bern" and fifth["review"] is None, "a value without the prefix stays")
        rows = store.list_decisions("nr-3")
        logged = len(rows) == 1 and rows[0]["by"] == "rule" and rows[0]["rule"] == rule["id"]
        check(logged, "the rule's change is logged")
        status, answer = app.answer_rule(rule["id"], True, "test")
        check(status == 409, f"an answered rule cannot be answered again: {answer.get('error')}")

        status, _ = app.decide("nr-3", {"source": source, "decision": "confirmed", "by": "test"})
        rule = next(r for r in store.get_rules() if r["id"] == rule["id"])
        check(status == 200 and rule["confirmed"] == 1, "a person confirming the rule's value counts on the rule")

        status, switched = app.switch_rule(rule["id"], False, "test")
        check(status == 200 and not switched["active"] and switched["state"] == "off", "the rule can be switched off")
        store.put_affair("nr-5", record_with("Kanton Glarus"), [{"name": "doc-5", "id": 1, "pages": 1}])
        status, _ = app.decide("nr-0", {"source": source, "decision": "confirmed", "by": "test"})
        sixth = value(store, 5)
        check(sixth["value"] == "Kanton Glarus" and sixth["review"] is None, "a switched-off rule applies nothing new")
        status, switched = app.switch_rule(rule["id"], True, "test")
        check(status == 200 and value(store, 5)["value"] == "Glarus",
              "switching the rule on applies it to the new value")
        jobs.stop()

        # a no
        store, app, jobs = fresh(tmp, "no", PLACES)
        change(app, 0, "Zürich")
        _, answer = change(app, 1, "Bern")
        rule = answer["proposals"][0]
        status, rule = app.answer_rule(rule["id"], False, "test")
        check(status == 200 and rule["state"] == "declined" and not rule["active"], "a no declines the rule")
        check(value(store, 2)["value"] == "Kanton Aargau", "a declined rule changes nothing")
        _, answer = change(app, 2, "Aargau")
        check(answer["proposals"] == [], "the same change a third time does not propose it again")
        jobs.stop()

        # a decision by hand that speaks against the rule
        store, app, jobs = fresh(tmp, "against", PLACES)
        change(app, 0, "Zürich")
        _, answer = change(app, 1, "Bern")
        rule = answer["proposals"][0]
        status, answer = app.decide("nr-2", {"source": source, "decision": "confirmed", "by": "test"})
        held = next(r for r in store.get_rules() if r["id"] == rule["id"])
        check(status == 200 and held["state"] == "contradicted" and held["against"] == 1 and answer["proposals"] == [],
              "a person confirming 'Kanton Aargau' as it stands takes the proposal away")
        status, answer = app.answer_rule(rule["id"], True, "test")
        check(status == 409 and value(store, 3)["value"] == "Kanton Luzern",
              f"a contradicted rule cannot be accepted: {answer.get('error')}")
        jobs.stop()

        # the same value becomes the same value
        store, app, jobs = fresh(tmp, "value", ["Standesinitiative", "Standesinitiative", "Standesinitiative", "Anzug"])
        change(app, 0, "Antrag")
        _, answer = change(app, 1, "Antrag")
        proposals = answer["proposals"]
        check(len(proposals) == 1 and proposals[0]["kind"] == "value" and proposals[0]["to"] == "Antrag"
              and proposals[0]["reach"]["count"] == 1, "two equal replacements propose the replacement for the third")
        status, rule = app.answer_rule(proposals[0]["id"], True, "test")
        check(status == 200 and value(store, 2)["value"] == "Antrag" and value(store, 3)["value"] == "Anzug",
              "accepted, it changes the equal value and no other")
        jobs.stop()

        # what a document prints with a label: the text beside it, the label itself where its box is ticked
        head = [{"id": "b1", "type": "def-list", "items": [
            {"term": "Vorstoss-Nr.:", "def": "M 185"}, {"term": "Richtlinienmotion", "def": "☒"},
            {"term": "Dringlich", "def": "☐"}, {"term": "Eingereicht am", "def": "22.11.2018"}]}]
        told = labels(head)
        check(told == {"vorstoss-nr.": "M 185", "richtlinienmotion": "Richtlinienmotion",
                       "eingereicht am": "22.11.2018"},
              f"labels of a head: {told}")
        kinds = [(p["kind"], p["parameter"]) for p in patterns("Motion", "Richtlinienmotion", told)]
        check(("label", "richtlinienmotion") in kinds
              and ("label", "vorstoss-nr.") in [(p["kind"], p["parameter"]) for p in patterns("nid 0.1", "m 185", told)]
              and not [p for p in patterns("Motion", "Postulat", told) if p["kind"] == "label"],
              "a change to what stands at a label, or to the label of a ticked box, carries that label")
        rule = {"kind": "label", "parameter": "eingereicht am"}
        check(apply(rule, "2018-11-21", told) == "2018-11-22" and apply(rule, "22. November 2018", told) is None
              and apply({"kind": "label", "parameter": "dringlich"}, "x", told) is None
              and apply(rule, "2018-11-21", {}) is None,
              "a rule of a label gives the labelled value where it differs, a date as its day; nothing where the "
              "box is empty or the label is not printed")

        # two changes to what stands at the same label propose the label for the field
        reads = [("Stadtrat", "Nidau"), ("Parlament", "Biel"), ("Rat", "Thun"), ("Bern", "Bern"), ("Kanzlei", None),
                 ("Amt", "☐")]
        store = FileStore(Path(tmp) / "label")
        for i, (read, printed) in enumerate(reads):
            store.put_affair(f"nr-{i}", record_with_label(read, printed), [{"name": f"doc-{i}", "id": 1, "pages": 1}])
        jobs = Jobs(type(config)(**{**config.__dict__, "storage_dir": Path(tmp) / "label-runs"}))
        app = App(store, contract, config, jobs)
        _, answer = change(app, 0, "Nidau")
        check(answer["proposals"] == [], "the first change to a labelled value proposes nothing")
        _, answer = change(app, 1, "Biel")
        found = [r for r in answer["proposals"] if r["kind"] == "label"]
        check(len(found) == 1 and found[0]["parameter"] == "gemeinde" and found[0]["field"] == "polity"
              and found[0]["reach"]["count"] == 1 and found[0]["reach"]["examples"][0]["after"] == "Thun",
              "the second proposes the label for the field; it reaches the one document that prints another value "
              "there")
        status, rule = app.answer_rule(found[0]["id"], True, "test")
        third, review = value(store, 2), value(store, 2)["review"] or {}
        check(status == 200 and rule["applied"] == 1 and third["value"] == "Thun" and review.get("by") == "rule"
              and review.get("rule") == rule["id"] and review.get("before") == "Rat",
              "accepted, the value becomes what stands at the label, with a review by the rule")
        check([value(store, i)["value"] for i in (3, 4, 5)] == ["Bern", "Kanzlei", "Amt"]
              and all(value(store, i)["review"] is None for i in (3, 4, 5)),
              "the same value, no label and an empty box are left alone")
        jobs.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
