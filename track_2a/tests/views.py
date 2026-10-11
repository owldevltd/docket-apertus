"""The same affair in two JSONs, from the same rows; without a model.

Affairs are formed from the stored runs of shipped documents into a store that works on the main contract.
Then each is laid into a second JSON that is built unlike the first on purpose (data/schema/plain: other keys,
other nesting, closed everywhere, no room for the documents' blocks or for the places of the values). Checked:
the second record fits its contract and carries nothing Docket adds; field by field it holds the values the
first one holds; the standard name of the type and the id of a person stand in both, each where its fields
file names a place; what a person decided shows in both (a changed value changed, a rejected value marked in
the first and left out of the second); and the first record itself is what the rows give in the first shape.

    python3 tests/views.py <document dir> ...
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.merge import Document, values_of  # noqa: E402
from docket.affair.validator import Contract  # noqa: E402
from docket.affair.view import OWN, view  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.fields.fields import Fields, load_fields  # noqa: E402
from docket.fields.placer import day, get_at  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.runner import _write_affairs  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.review import sources_of  # noqa: E402

PLAIN = Path(__file__).resolve().parents[1] / "data" / "schema" / "plain"


def known_person(config) -> dict:
    """A row of the register for the first name the Zürich document carries, read from the affair stored beside
    it: the test itself names nobody."""
    record = json.loads((config.data_dir / "documents" / "zuerich-219587" / "affair.json").read_text(encoding="utf-8"))
    label = record["contributors"]["data"][0]["fullname"]
    first, last = label.split(" ", 1)
    return {"body": "X", "key": label.lower(), "label": label, "first": first, "last": last, "ids": [4711],
            "origin": "stem"}


def read(record: dict, fields: Fields) -> dict[str, list]:
    """The values a record holds per field, read through its fields file: at the field's path, in a list from
    the entries that carry the fixed parts of the field's template."""
    out: dict[str, list] = {}
    for name, f in fields.fields.items():
        if "[]" in f.path:
            at = f.path.index("[]")
            entries = [e for e in get_at(record, f.path[:at]) or []
                       if all(e.get(k) == v for k, v in f.fixed.items())]
            found = [held(e, f.path[at + 1:], f.own_language) for e in entries]
        else:
            value = held(record, f.path, f.own_language)
            found = value if isinstance(value, list) else [value]
        out[name] = [v for v in found if v is not None]
    return out


def held(node: dict, path: list[str], own_language: bool):
    """The value at a path; of a field that stands under the language of its document, the one there is."""
    if not own_language:
        return get_at(node, path)
    under = get_at(node, path[:-1])
    return next(iter(under.values()), None) if isinstance(under, dict) else None


def keys_of(node) -> set[str]:
    """Every key anywhere in a record."""
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in keys_of(v)}
    return {k for v in node for k in keys_of(v)} if isinstance(node, list) else set()


def main(argv: list[str]) -> int:
    dirs = {d.name: d for d in (Path(a) for a in argv if not a.startswith("--")) if (d / "run.json").is_file()}
    if not dirs:
        print("usage: python3 tests/views.py <document dir> ...")
        return 1
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    base = load_config()
    contract = load_contract(base)
    fields = load_field_file(base, contract)
    knowledge = load_knowledge(base)
    plain_contract = Contract.load(PLAIN / "contract.json")
    plain_fields = load_fields(PLAIN / "fields.json", plain_contract)
    shared = sorted(plain_fields.fields)
    check(set(shared) <= set(fields.fields) and len(shared) > 0,
          f"the second fields file places {len(shared)} of the {len(fields.fields)} fields, under the names they were "
          f"read by")

    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        store = open_store(config)
        # a register that knows one of the names, so that an affair holds the id of a person
        store.put_register([known_person(base)])
        out = Path(tmp) / "out"
        out.mkdir()
        documents = []
        for name in sorted(dirs):
            stored = json.loads((dirs[name] / "run.json").read_text(encoding="utf-8"))
            report = {"identity": stored["identity"], "kind": stored.get("kind"), "fields": stored["fields"]}
            (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            values = values_of(stored["fields"])
            date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
            identity = stored["identity"]
            body = "X" if name == "zuerich-219587" else identity.get("body") or ""
            documents.append(Document(len(documents) + 1, name, stored["pages"], stored["body"], values,
                                      identity.get("key") or "dok-" + name, date, body))
        made = _write_affairs(out, documents, fields, contract, knowledge, config, lambda line: None)
        keys = {name: a["key"] for a in made for name in a["documents"]}
        app = App(store, contract, config, Jobs(config))

        def both(key: str) -> tuple[dict, dict]:
            again = view(store, key, plain_fields, plain_contract, knowledge.types, knowledge.answers)
            return store.get_affair(key)["record"], again

        fit = same = clean = 0
        values = 0
        for name, key in sorted(keys.items()):
            first, second = both(key)
            fit += not plain_contract.check(second) and not contract.check(first)
            clean += not (keys_of(second) & set(OWN))
            a, b = read(first, fields), read(second, plain_fields)
            same += all(a[n] == b[n] for n in shared)
            values += sum(len(b[n]) for n in shared)
        check(fit == len(keys), f"{fit} of {len(keys)} affairs fit both contracts, each in its own shape")
        check(clean == len(keys), f"{clean} of {len(keys)} second records carry no blocks, no places, no reviews")
        check(same == len(keys) and values > 0,
              f"{same} of {len(keys)} hold the same values field by field in both, {values} values")

        typed = [(f, s) for f, s in (both(k) for k in keys.values()) if f.get("type_harmonized")]
        check(len(typed) > 0 and all(s["subject"]["form_standard"] == f["type_harmonized"] for f, s in typed),
              f"the standard name of the type stands in both, in {len(typed)} affairs")
        key = keys["zuerich-219587"]
        first, second = both(key)
        told = next(e for e in sources_of(first) if e["label"] == "contributors.person_id")
        check(told["value"] == 4711 and [p.get("person") for p in second["people"]].count(4711) >= 1,
              "the id of a person stands in both, beside the name it was found for")

        # what a person decides shows in both
        entries = {e["label"]: e for e in reversed(sources_of(first))}
        people = [e for e in sources_of(first) if any(".party." in p for p in e.get("values") or {})]
        party_path = next(p for p in people[1]["values"] if ".party." in p)
        asked = [
            {"source": entries["title"]["source"], "decision": "changed", "by": "test", "after": "Ein neuer Titel"},
            {"source": people[1]["source"], "path": party_path, "decision": "changed", "by": "test", "after": "GLP"},
            {"source": entries["polity"]["source"], "decision": "rejected", "by": "test"},
            {"source": told["source"], "decision": "rejected", "by": "test"},
        ]
        check(all(app.decide(key, body)[0] == 200 for body in asked), "four decisions taken in the first shape")
        first, second = both(key)
        check(first["title"]["de"] == second["subject"]["heading"] == "Ein neuer Titel",
              "a changed title is the title in both")
        groups = [p.get("group") for p in second["people"] if p["as"] == "submitted"]
        check(get_at(first, party_path.split(".")) == "GLP" and groups[1] == "GLP" and groups.count("GLP") == 1,
              "a changed party of one person is that person's party in both, and nobody else's")
        marked = next(e for e in sources_of(first) if e["label"] == "polity")
        check(marked["review"]["decision"] == "rejected" and marked["value"] and "polity" not in second["where"],
              "a rejected value stays marked in the first and is left out of the second")
        # the same name stands a second time, as co-signer: that entry was not decided on and keeps its id
        with_id = [p["as"] for p in second["people"] if "person" in p]
        check(with_id == ["co-signed"] and not plain_contract.check(second),
              "a rejected id of a person is left out of the second, which still fits its contract")

        # the first record itself is what the rows give in the first shape
        own = 0
        for name, k in sorted(keys.items()):
            stored = store.get_affair(k)["record"]
            if not any(e["label"] == "contributors.person_id" for e in sources_of(stored)):
                own += view(store, k, fields, contract, knowledge.types, knowledge.answers) == stored
        check(own == len(keys) - 1,
              f"{own} of {len(keys) - 1} stored records without a person's id are the rows laid into the first shape")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
