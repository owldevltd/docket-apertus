"""The texts of the browser app in its four languages, without Node and without a network: every text the app
has stands in the list with a French, an Italian and an English wording, each with the places of values the
German one has; the three files the build reads are what the tool writes from the list; and the tool itself
puts the places back, tells a text without a row, a wording with other places and a row without a text.

    python3 tests/translations.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from translations import LANGUAGES, LOCALE, MESSAGES, WORDS, missing, plain, render, sources, target  # noqa: E402

SMALL = """<xliff version="1.2">
  <file source-language="de" datatype="plaintext" original="ng2.template">
    <body>
      <trans-unit id="1" datatype="html">
        <source>Seite <x id="INTERPOLATION" equiv-text="{{ page() }}"/> von
          <x id="INTERPOLATION_1" equiv-text="{{ pages() }}"/></source>
      </trans-unit>
      <trans-unit id="2" datatype="html">
        <source>{VAR_PLURAL, plural, =1 {1 Wert} other {<x id="INTERPOLATION"/> Werte}}</source>
      </trans-unit>
    </body>
  </file>
</xliff>
"""


def main() -> int:
    failed = False

    def ok(passed: bool, text: str) -> None:
        nonlocal failed
        failed = failed or not passed
        print(("ok   " if passed else "FAIL ") + text)

    messages = MESSAGES.read_text(encoding="utf-8")
    rows = json.loads(WORDS.read_text(encoding="utf-8"))
    texts = sources(messages)
    open_ones = missing(messages, rows)
    ok(not open_ones, f"each of the {len(texts)} texts of the app has a wording in {', '.join(LANGUAGES)} with the "
       "places of the German one" + (f"; open: {open_ones[:5]}" if open_ones else ""))
    for language in LANGUAGES:
        held = (LOCALE / f"messages.{language}.xlf").read_text(encoding="utf-8")
        ok(held == render(messages, rows, language) and held.count("<target>") == len(texts),
           f"the file of {language} is what the tool writes from the list, a target for every text")

    # the tool itself, on a file of two texts
    first, second = sources(SMALL)
    ok(plain(first) == "Seite {INTERPOLATION} von {INTERPOLATION_1}"
       and plain(second) == "{VAR_PLURAL, plural, =1 {1 Wert} other {{INTERPOLATION} Werte}}",
       "a text is known by its wording with the places of its values named")
    turned = target(first, "{INTERPOLATION_1} pages, this is <{INTERPOLATION}> & more")
    ok(turned == '<x id="INTERPOLATION_1" equiv-text="{{ pages() }}"/> pages, this is &lt;'
       '<x id="INTERPOLATION" equiv-text="{{ page() }}"/>&gt; &amp; more',
       "a wording gets the places of the source back, in its own order, and its own signs kept apart from them")
    small = [{"de": plain(first), "fr": "Page {INTERPOLATION} sur {INTERPOLATION_1}", "it": "Pagina {INTERPOLATION}",
              "en": ""},
             {"de": "nicht mehr da", "fr": "a", "it": "b", "en": "c"}]
    told = missing(SMALL, small)
    ok(sorted(told) == sorted([f"other places in it: {plain(first)}", f"no en: {plain(first)}",
                               f"no row: {plain(second)}", "no text of the app any more: nicht mehr da"]),
       "a text without a row, a missing language, a wording with other places and a row without a text are told")
    french = render(SMALL, small, "fr")
    ok('target-language="fr"' in french and french.count("<target>") == 2
       and '<target>Page <x id="INTERPOLATION" equiv-text="{{ page() }}"/> sur' in french
       and "<target>{VAR_PLURAL, plural, =1 {1 Wert} other {<x id=\"INTERPOLATION\"/> Werte}}</target>" in french,
       "the file of a language names it and holds a target for every text; a text without a wording keeps the "
       "German one")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
