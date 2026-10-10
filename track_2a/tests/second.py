"""The second opinion on where a field stands, learnt from a store and held against the model; without a model.

A store is filled with documents of one parliament that all look alike (a shipped document under several
names). The second opinion is learnt from it and tried on documents held back: for a field that always stands
at the same place it must keep a way, and it must tell how often it agreed. Then three documents are run
with it: one where the model found no date (the date is taken from the named block and marked for a
person), one where the model's value stands in the named block (nothing changes, a mark it had stays),
and one where the model took its value from another block (it is marked). A store that has learnt
nothing leaves every record as it was.

    python3 tests/second.py <document dir> ...
"""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.affair.merge import Document, values_of  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.fields import second  # noqa: E402
from docket.fields.placer import block_text, blocks_of, day  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.runner import _write_affairs  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.review import sources_of  # noqa: E402
from docket.store.vocabulary import Vocabulary  # noqa: E402

PARLIAMENT = "X"


def main(argv: list[str]) -> int:
    source = next((Path(a) for a in argv if (Path(a) / "run.json").is_file() and Path(a).name == "nidau-m185"), None)
    if source is None:
        print("usage: python3 tests/second.py <document dir> ...   (needs nidau-m185 with its stored run)")
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
    stored = json.loads((source / "run.json").read_text(encoding="utf-8"))

    def run(config, out: Path, runs: dict[str, dict]) -> None:
        """Forms one affair per document from the given runs, the way a run does."""
        out.mkdir(exist_ok=True)
        documents = []
        for name, one in runs.items():
            report = {"identity": {**one["identity"], "body": PARLIAMENT}, "fields": one["fields"]}
            (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
            values = values_of(one["fields"])
            date = next((day(i["value"]) for i in values.get(fields.by_role().get("date", ""), [])), "")
            documents.append(Document(len(documents) + 1, name, one["pages"], one["body"], values, "key-" + name,
                                      date, PARLIAMENT))
        _write_affairs(out, documents, fields, contract, knowledge, config, lambda line: None)

    def place_of(store, name: str, label: str) -> dict:
        return next(e for e in sources_of(store.get_affair("key-" + name)["record"]) if e["label"] == label)

    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        store = open_store(config)
        alike = {f"alike-{i}": stored for i in range(8)}
        run(config, Path(tmp) / "out", alike)
        before = store.get_affair("key-alike-0")["record"]
        check(store.get_learnt() is None and not any("second" in r for r in store.get_rows("alike-0")),
              "a store that has learnt nothing holds no second opinion")

        learnt = second.learn(second.from_store(store), fields, knowledge.forms, Vocabulary(store.get_vocabulary()))
        store.put_learnt(learnt)
        places = learnt["places"].get(PARLIAMENT, {})
        number = places.get("number") or {}
        check(learnt["documents"] == 8 and number.get("use") and number["agree"] == 8 and number["disagree"] == 0
              and number["share"] == 1.0,
              f"the place of the number is learnt from 8 documents and kept: held back it agreed {number.get('agree')} "
              f"times and never disagreed")
        cuts = {**((learnt["network"] or {}).get("cuts") or {}), **((learnt["lists"] or {}).get("cuts") or {})}
        check(bool(learnt["network"]) and cuts["number"]["use"] and cuts["number"]["disagree"] == 0,
              f"the network is learnt as well and kept for the number: agreed {cuts['number']['agree']}, disagreed "
              f"{cuts['number']['disagree']}")
        check(store.get_learnt() == json.loads(json.dumps(learnt)), "what was learnt comes back from the store")
        told = App(store, contract, config, Jobs(config)).learnt()
        ways = {(w["way"], w["parliament"], w["field"]): w for w in told["ways"]}
        check(told["documents"] == 8 and ways[("place", PARLIAMENT, "number")]["use"]
              and ways[("network", "", "number")]["agree"] == cuts["number"]["agree"],
              f"the server tells what was learnt, way by way: {len(ways)} ways")
        unused = [n for n, f in fields.fields.items() if not second.speaks_for(f)]
        lists = [n for n, f in fields.fields.items() if second.several(f) and second.speaks_for(f)]
        check(all(n not in places and n not in cuts for n in unused) and "summary" in unused
              and all(n not in places for n in lists) and cuts["authors"]["use"],
              f"no opinion for wording the model composed; for a list of names only the network speaks (authors: "
              f"agreed {cuts['authors']['agree']}, disagreed {cuts['authors']['disagree']})")

        # three further documents, read with the second opinion beside the model
        gap = copy.deepcopy(stored)
        gap["fields"]["date"] = {"value": None, "state": "missing", "items": []}
        marked = copy.deepcopy(stored)
        marked["fields"]["title"]["items"][0]["how"] = "cited"
        apart = copy.deepcopy(stored)
        # the model takes for the title what stands literally in another block: the last one of the document
        elsewhere = blocks_of(stored["body"])[-1]
        other = elsewhere["id"]
        apart["fields"]["title"]["items"][0].update({"value": block_text(elsewhere), "block": other, "how": "literal"})
        run(config, Path(tmp) / "out", {"gap": gap, "marked": marked, "apart": apart})

        filled = place_of(store, "gap", "begin_date")
        row = next(r for r in store.get_rows("gap") if r["field"] == "date")
        check(filled["value"] == day(stored["fields"]["date"]["items"][0]["value"]) and filled["approve"]
              and row.get("by") in ("place", "network"),
              f"where the model found no date, the one in the named block is taken ({filled['value']}), marked for "
              f"a person, by the {row.get('by')}")
        agreed = place_of(store, "marked", "title")
        check(agreed["how"] == "cited" and agreed["approve"]
              and next(r for r in store.get_rows("marked") if r["field"] == "title")["second"]["agrees"],
              "a value the second opinion agrees with keeps the mark the model's reading gave it; the agreement "
              "is noted")
        differs = place_of(store, "apart", "title")
        told = next(r for r in store.get_rows("apart") if r["field"] == "title")["second"]
        check(differs["approve"] and not told["agrees"] and told["block"] != other,
              "a value that stands literally, but in another block than the second opinion names, is marked")
        # a name the model placed in a block the network does not take for the authors' is marked
        moved = copy.deepcopy(stored)
        moved["fields"]["authors"]["items"][0]["block"] = other
        run(config, Path(tmp) / "out", {"moved": moved})
        names = [r for r in store.get_rows("moved") if r["field"] == "authors" and r["state"] == "placed"]
        check(names[0]["approve"] and not names[0]["second"]["agrees"]
              and all(r["second"]["agrees"] and "approve" not in r for r in names[1:]),
              "of several names, the one placed in a block the network does not take for theirs is marked, the "
              "others are not")
        same = store.get_affair("key-alike-0")["record"]
        check(same == before, "the documents read before the learning stay as they were until they are run again")

    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage"})
        store = open_store(config)
        run(config, Path(tmp) / "out", {"a": stored, "b": stored})
        learnt = second.learn(second.from_store(store), fields, knowledge.forms, Vocabulary(store.get_vocabulary()))
        check(not learnt["places"] and learnt["network"] is None and learnt["lists"] is None,
              "from two documents nothing is learnt: no place is usual yet, and too few to hold any back")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
