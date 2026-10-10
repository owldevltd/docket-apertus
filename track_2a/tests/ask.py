"""Asking stored documents a field they were never asked; without a model (its answer is played).

A document is stored as a run left it, but under a definition that did not have the date yet. A person decides
on its title. Then the document is asked what it was never asked: only that question goes out, over the pages
the store kept, and the played answer names the date and its block. Checked: the date is in the document's
report, among its rows and in the affair's record; the decision on the title is still there; the store counts
no document as never asked for the date any more; a second asking sends nothing.

    python3 tests/ask.py --pages=<analyzed dir> <document dir> ...
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import docket.fields.filler as filler  # noqa: E402
from docket.affair.merge import Document, values_of  # noqa: E402
from docket.api import App  # noqa: E402
from docket.config import load_config  # noqa: E402
from docket.jobs import Jobs  # noqa: E402
from docket.model.client import Answer  # noqa: E402
from docket.pipeline import load_contract, load_field_file, load_knowledge  # noqa: E402
from docket.runner import _write_affairs, ask_missing  # noqa: E402
from docket.store import open_store  # noqa: E402
from docket.store.review import sources_of  # noqa: E402


def main(argv: list[str]) -> int:
    pages_dir = next((Path(a[8:]) for a in argv if a.startswith("--pages=")), None)
    source = next((Path(a) for a in argv if (Path(a) / "run.json").is_file() and Path(a).name == "nidau-m185"), None)
    if source is None or pages_dir is None:
        print("usage: python3 tests/ask.py --pages=<analyzed dir> <document dir> ...   (needs nidau-m185)")
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
    name = "nidau-m185"
    stored = json.loads((source / "run.json").read_text(encoding="utf-8"))
    date = stored["fields"]["date"]["items"][0]
    sent: list[str] = []

    def played(client, prompt, **_):
        """The model's part: it answers the one question with the date the stored run had read."""
        client.calls += 1
        sent.append(prompt)
        return Answer(f"date: {date['value']} [{date['block']}]", 200, {"prompt_tokens": 0}, "stop")

    with tempfile.TemporaryDirectory() as tmp:
        config = type(base)(**{**base.__dict__, "storage_dir": Path(tmp) / "storage", "api_key": "played"})
        out = Path(tmp) / "out"
        out.mkdir()
        # the document as read before the date was a field
        earlier = {k: v for k, v in stored["fields"].items() if k != "date"}
        report = {"identity": stored["identity"], "kind": stored.get("kind"), "fields": earlier}
        (out / f"{name}-fields.json").write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
        (out / name).mkdir()
        for page in sorted(pages_dir.glob(f"{name}-s*")):
            if page.is_file():
                (out / name / page.name).write_bytes(page.read_bytes())
        document = Document(1, name, stored["pages"], stored["body"], values_of(earlier), stored["identity"]["key"],
                            "", stored["identity"].get("body") or "")
        key = _write_affairs(out, [document], fields, contract, knowledge, config, lambda line: None)[0]["key"]
        store = open_store(config)
        app = App(store, contract, config, Jobs(config))
        never = {f["name"]: f["never"] for f in app.definition()["fields"]}
        check(never["date"] == 1 and never["title"] == 0 and "begin_date" not in store.get_affair(key)["record"],
              "a document read before the date was a field counts as never asked for it")
        title = next(e for e in sources_of(store.get_affair(key)["record"]) if e["label"] == "title")
        status, _ = app.decide(key, {"source": title["source"], "decision": "changed", "by": "test", "after": "Neu"})
        check(status == 200, "a person changes its title")

        asked_before = filler.ask
        filler.ask = played
        try:
            result = ask_missing(config, say=lambda line: None)
            again = ask_missing(config, say=lambda line: None)
        finally:
            filler.ask = asked_before
        record = store.get_affair(key)["record"]
        check(result.calls == 1 and len(sent) == 1 and "date:" in sent[0] and "title:" not in sent[0]
              and result.documents[0]["asked"] == ["date"],
              "the document is asked the one field it lacks, in one call")
        row = next((r for r in store.get_rows(name) if r["field"] == "date"), None)
        check("date" in store.get_fields(name)["fields"] and row is not None and row["block"] == date["block"]
              and bool(record.get("begin_date")),
              f"the answer is in its report, among its rows and in the affair ({record.get('begin_date')})")
        kept = next(e for e in sources_of(record) if e["label"] == "title")
        check(kept["value"] == "Neu" and kept["review"]["decision"] == "changed",
              "the decision a person took before the asking is still there")
        never = {f["name"]: f["never"] for f in app.definition()["fields"]}
        check(never["date"] == 0 and again.calls == 0 and not again.documents,
              "nothing is left to ask: a second asking sends nothing")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
