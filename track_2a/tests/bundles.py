"""Which fields share a call, without a model and without a document: every field of a scope is asked in exactly
one call, no call asks more than BUNDLE fields, fields that name the same word under "together" share a call of
their own, and the fields of the contributors (who submitted, their party, in whose name, who co-signed) are such
a group over the whole document.

    python3 tests/bundles.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from docket.config import load_config  # noqa: E402
from docket.fields.fields import Field, Fields  # noqa: E402
from docket.fields.filler import BUNDLE, bundles, parse, prompt  # noqa: E402
from docket.pipeline import load_contract, load_field_file  # noqa: E402


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
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
