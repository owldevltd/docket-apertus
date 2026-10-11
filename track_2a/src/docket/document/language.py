"""The language a document is written in, told by code from its own words.

Counted are the small words a language cannot do without (articles, prepositions, conjunctions), only those no
other of the languages shares. The language with the most of them is the document's, when it leads clearly;
else none is told. For the languages of the Swiss parliaments and English. Tried on 11 October 2026 on 211
documents whose language is known from the parliament they come from: see docs/evidence.md.
"""

from __future__ import annotations

import re

from docket.fields.placer import block_text, blocks_of

WORDS = {
    "de": "der die das und nicht mit von für ist des den dem ein eine auf zu im werden wird dass sich auch bei "
          "nach oder wir sind durch zur zum über",
    "fr": "les des et est une que qui dans pour du au aux sur pas ce cette sont avec ne plus nous leur ces être "
          "par ou comme ainsi",
    "it": "il di che per del della dei delle con non sono alla nel si anche gli è più questo questa sul dal "
          "degli come essere",
    "rm": "ils las dal dals cun ina èn quai betg tar pli era sco vegn dals tras nus",
    "en": "the and of to is that with this are be for which from has have by as not",
}
SETS = {code: set(words.split()) for code, words in WORDS.items()}
# a word several languages share tells none of them
SHARED = {w for code, words in SETS.items() for w in words if any(w in other for c, other in SETS.items() if c != code)}

# so many of its words at least, and so many times the next language
ENOUGH = 8
LEAD = 1.5


def language_of_text(text: str) -> str:
    """The code of the language ("de", "fr", "it", "rm", "en"), or empty when none leads clearly."""
    counts = dict.fromkeys(SETS, 0)
    for word in re.findall(r"[^\W\d_]+", text.lower()):
        if word in SHARED:
            continue
        for code, words in SETS.items():
            if word in words:
                counts[code] += 1
    first, second = sorted(counts.items(), key=lambda item: -item[1])[:2]
    return first[0] if first[1] >= ENOUGH and first[1] >= LEAD * second[1] else ""


def language_of(body: list[dict]) -> str:
    """The language of a document from the text of its blocks."""
    return language_of_text(" ".join(block_text(c) for c in blocks_of(body)))
