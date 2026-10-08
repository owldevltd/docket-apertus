"""The general repair, without a model: three changes with the same pattern on the same field make a rule,
the rule changes the fitting values of that field in the other affairs with a review by "rule", a person's
confirmation of such a value is counted on the rule, and a switched-off rule applies nothing new.

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
from docket.store.rules import pattern  # noqa: E402

PLACES = ["Kanton Zürich", "Kanton Bern", "Kanton Aargau", "Kanton Luzern", "Stadt Bern"]


def record_with(place: str) -> dict:
    block = {"id": "b1", "page": 1, "type": "p", "x": 0, "y": 0, "width": 10, "height": 10, "text": place}
    return {
        "schema": "0.8",
        "docs": {"data": [{"id": 1, "name": "doc-" + place.lower().replace(" ", "-"), "page-count": 1,
                           "body": [block]}]},
        "custom-meta": [{"meta-name": "gemeinwesen", "meta-value": place,
                         "source": {"doc": 1, "block": "b1", "how": "cited", "approve": True}}],
    }


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

    with tempfile.TemporaryDirectory() as tmp:
        config = load_config()
        store = FileStore(Path(tmp) / "store")
        for i, place in enumerate(PLACES):
            store.put_affair(f"nr-{i}", record_with(place), [{"name": f"doc-{i}", "id": 1, "pages": 1}])
        jobs = Jobs(type(config)(**{**config.__dict__, "storage_dir": Path(tmp)}))
        app = App(store, load_contract(config), config, jobs)
        source = "custom-meta.0.source"
        for i in range(3):
            status, _ = app.decide(f"nr-{i}", {"source": source, "decision": "changed", "by": "test",
                                               "after": PLACES[i].replace("Kanton ", "")})
            check(status == 200, f"change {i + 1}: {PLACES[i]!r} without the prefix")
        rules = store.get_rules()
        check(len(rules) == 1 and rules[0]["active"] and rules[0]["count"] == 3,
              f"one rule, active after three changes: {rules[0] if rules else None}")
        rule = rules[0]
        check(rule["kind"] == "prefix-off" and rule["parameter"] == "Kanton ", "the rule takes 'Kanton ' off")
        fourth = sources_of(store.get_affair("nr-3")["record"])[0]
        review = fourth["review"] or {}
        check(fourth["value"] == "Luzern" and review.get("by") == "rule" and review.get("rule") == rule["id"],
              f"the fourth affair was changed by the rule: {fourth['value']}")
        fifth = sources_of(store.get_affair("nr-4")["record"])[0]
        check(fifth["value"] == "Stadt Bern" and fifth["review"] is None, "a value without the prefix stays")
        check(rule["applied"] == 1, f"the rule counts {rule['applied']} application")
        rows = store.list_decisions("nr-3")
        logged = len(rows) == 1 and rows[0]["by"] == "rule" and rows[0]["rule"] == rule["id"]
        check(logged, "the rule's change is logged")

        status, _ = app.decide("nr-3", {"source": source, "decision": "confirmed", "by": "test"})
        rule = store.get_rules()[0]
        check(status == 200 and rule["confirmed"] == 1, "a person confirming the rule's value counts on the rule")

        status, switched = app.switch_rule(rule["id"], False, "test")
        check(status == 200 and not switched["active"], "the rule can be switched off")
        store.put_affair("nr-5", record_with("Kanton Glarus"), [{"name": "doc-5", "id": 1, "pages": 1}])
        status, _ = app.decide("nr-0", {"source": source, "decision": "confirmed", "by": "test"})
        sixth = sources_of(store.get_affair("nr-5")["record"])[0]
        check(sixth["value"] == "Kanton Glarus" and sixth["review"] is None, "a switched-off rule applies nothing new")
        status, switched = app.switch_rule(rule["id"], True, "test")
        sixth = sources_of(store.get_affair("nr-5")["record"])[0]
        check(status == 200 and sixth["value"] == "Glarus", "switching the rule on applies it to the new value")
        jobs.stop()
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
