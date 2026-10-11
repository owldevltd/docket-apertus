"""Writes the translation files of the browser app from the list of its texts in four languages.

    python3 tools/translations.py           writes app/src/locale/messages.{fr,it,en}.xlf
    python3 tools/translations.py --open    only lists the texts that have no translation yet

The app is written in German and built once per language by the localisation of Angular. Its texts are taken
out of the templates and the code into app/src/locale/messages.xlf (in app/: npx ng extract-i18n --format xlf
--output-path src/locale); the build wants one file per further language with a target beside every source.
Those files are written here, from app/src/locale/words.json: one row per text with "de", "fr", "it" and "en",
side by side, so a reader of one of the languages can go through them in one place. A text is found by its
German wording with the places of its values written as {NAME}, as the rows have them; the same places have
to stand in every translation.

A text without a row keeps its German wording in the file, so the build goes through, and is listed; the exit
code is then 1. The French, Italian and English wordings were set by the assistant and are open: no native
speaker has read them yet.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALE = ROOT / "app" / "src" / "locale"
MESSAGES = LOCALE / "messages.xlf"
WORDS = LOCALE / "words.json"

SOURCE = "de"
LANGUAGES = ("fr", "it", "en")

UNIT = re.compile(r"(<trans-unit\b[^>]*>\s*)<source>(.*?)</source>", re.S)
PLACE = re.compile(r'<x id="([^"]+)"[^>]*/>')
NAMED = re.compile(r"\{([A-Za-z_0-9]+)\}")


def plain(source: str) -> str:
    """The wording of a source as the rows hold it: every place of a value as {NAME}, white space as one
    blank."""
    return re.sub(r"\s+", " ", PLACE.sub(lambda m: "{" + m.group(1) + "}", source)).strip()


def places(text: str) -> list[str]:
    """The places of values in a wording, in order; the words of a plural form are not places."""
    return sorted(NAMED.findall(text))


def sources(messages: str) -> list[str]:
    """The texts of the app, each once, in the order of the file."""
    return [m.group(2) for m in UNIT.finditer(messages)]


def table(rows: list[dict]) -> dict[str, dict]:
    return {r[SOURCE]: r for r in rows}


def target(source: str, wording: str) -> str:
    """A translation as the file wants it: the places of the source put back where the wording names them."""
    held = {m.group(1): m.group(0) for m in PLACE.finditer(source)}
    out, at = [], 0
    for m in NAMED.finditer(wording):
        if m.group(1) in held:
            out += [escape(wording[at:m.start()]), held[m.group(1)]]
            at = m.end()
    return "".join([*out, escape(wording[at:])])


def escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(messages: str, rows: list[dict], language: str) -> str:
    """The file of one language: the extracted file with a target after every source."""
    known = table(rows)

    def with_target(m: re.Match) -> str:
        source = m.group(2)
        wording = (known.get(plain(source)) or {}).get(language)
        indent = re.search(r"\n([ \t]*)$", m.group(1))
        gap = "\n" + (indent.group(1) if indent else "        ")
        said = target(source, wording) if wording else source
        return f"{m.group(1)}<source>{source}</source>{gap}<target>{said}</target>"

    out = UNIT.sub(with_target, messages)
    return out.replace(f'source-language="{SOURCE}"', f'source-language="{SOURCE}" target-language="{language}"', 1)


def missing(messages: str, rows: list[dict]) -> list[str]:
    """What cannot be written: a text without a row or without one of the languages, a translation whose
    places are not the ones of the German wording, and a row no text of the app has any more."""
    known = table(rows)
    texts = [plain(s) for s in sources(messages)]
    out = []
    for text in texts:
        row = known.get(text)
        if row is None:
            out.append(f"no row: {text}")
            continue
        for language in LANGUAGES:
            if not row.get(language):
                out.append(f"no {language}: {text}")
            elif places(row[language]) != places(text):
                out.append(f"other places in {language}: {text}")
    out += [f"no text of the app any more: {r[SOURCE]}" for r in rows if r[SOURCE] not in set(texts)]
    return out


def main() -> int:
    messages = MESSAGES.read_text(encoding="utf-8")
    rows = json.loads(WORDS.read_text(encoding="utf-8"))
    open_ones = missing(messages, rows)
    for line in open_ones:
        print(line)
    if "--open" not in sys.argv[1:]:
        for language in LANGUAGES:
            (LOCALE / f"messages.{language}.xlf").write_text(render(messages, rows, language), encoding="utf-8")
        print(f"wrote {len(LANGUAGES)} files with {len(sources(messages))} texts each")
    return 1 if open_ones else 0


if __name__ == "__main__":
    sys.exit(main())
