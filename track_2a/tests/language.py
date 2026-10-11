"""The language of a document, without a model: told from its own small words, for the languages of the Swiss
parliaments and English, and not told where too little stands there or two languages are level. On the shipped
documents it is the language their description names; it stands at the document in the affair, and the summary
stands under it. The question for a summary names the language to the model.

    python3 tests/language.py data/documents/*
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.config import load_config  # noqa: E402
from docket.document.language import language_of, language_of_text  # noqa: E402
from docket.fields.filler import prompt  # noqa: E402
from docket.pipeline import load_contract, load_field_file  # noqa: E402

SAMPLES = {
    "de": "Der Gemeinderat wird beauftragt, dem Stadtrat einen Bericht und einen Antrag vorzulegen, der zeigt, wie "
          "die Stadt mit den Anliegen umgeht und was sie für die Betroffenen tun wird.",
    "fr": "Le Conseil d'Etat est invité à présenter au Grand Conseil un rapport sur les mesures qui sont prises "
          "dans les communes et sur ce que le canton fait pour les personnes concernées.",
    "it": "Il Consiglio di Stato è invitato a presentare al Gran Consiglio un rapporto sulle misure che sono "
          "state prese nei comuni e su ciò che il Cantone fa per le persone interessate, anche con gli altri.",
    "en": "The council is asked to present a report to the parliament that shows which measures are taken and "
          "what the canton has done for the people who are concerned by this, and by which means it has to be.",
}


def main(argv: list[str]) -> int:
    failed = False

    def check(ok: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not ok
        print(("ok   " if ok else "FAIL ") + text)

    got = {code: language_of_text(text) for code, text in SAMPLES.items()}
    check(got == {code: code for code in SAMPLES}, f"a paragraph tells its language: {got}")
    check(language_of_text("Motion 2018.123") == "" and language_of_text("") == "",
          "a line without the small words of a language tells none")
    check(language_of_text(SAMPLES["de"] + " " + SAMPLES["fr"]) == "", "two languages level tell none")

    config = load_config()
    contract = load_contract(config)
    fields = load_field_file(config, contract)
    told, placed, total = 0, 0, 0
    for folder in sorted(Path(a) for a in argv if not a.startswith("--")):
        files = [folder / n for n in ("document.json", "run.json", "affair.json")]
        if not all(f.is_file() for f in files):
            continue
        meta, run, affair = (json.loads(f.read_text(encoding="utf-8")) for f in files)
        entry = affair["docs"]["data"][0]
        total += 1
        told += language_of(run["body"]) == meta["language"] == entry.get("language")
        placed += list(entry.get("abstract") or {}) == [meta["language"]]
    check(told == total, f"{told} of the {total} shipped documents are told to be in the language their description "
          "names, and say so in their affair")
    check(placed == total, f"{placed} of {total} carry their summary under that language")

    line = {lang: next(row for row in prompt(["summary"], "", [1, 2], 2, fields, contract, lang).split("\n")
                       if row.startswith("- summary")) for lang in ("fr", "it", "")}
    check("{sprache}" not in "".join(line.values()) and "en français" in line["fr"] and "in italiano" in line["it"]
          and "in der Sprache des Dokuments" in line[""],
          "the question for the summary names the language of the document, or says so where none is told")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
