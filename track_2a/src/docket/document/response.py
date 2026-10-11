"""The answer within a document: a submission printed together with what the executive answers to it.

Where a heading announces the answer ("Antwort des Gemeinderates", "Réponse du Conseil d'Etat", "Risposta del
14 marzo 2019 ..."), what stands from there on is the answer; the affair keeps it as `response` beside the body
of the document, every block with the id and the place it had. The words that announce an answer are prior
knowledge for all parliaments alike (data/knowledge/sections.json, `response`), in the languages of the
documents; nothing here knows a parliament or a kind of document. Counted 11 October 2026 on 211 stored
documents: 11 carry such a heading, and of the 26 the run took for an answer, 11 have no heading at all.
There the whole document is the answer, which its kind says.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

# what an answer within a document is called in the record
ANSWER = "answer"


def fold(text: str) -> str:
    """Lower case without accents: "RÉPONSE" and "REPONSE" are one name."""
    return "".join(c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c))


def begins_with(text: str, names: Iterable[str]) -> str | None:
    """The name of `names` a heading begins with, a counter before it left out ("2. Antwort des Stadtrats")."""
    t = fold(re.sub(r"^[\d.IVXA-Z]+[.)]\s+|\s*[:.]+$", "", text.strip()).strip())
    for name in names:
        n = fold(name)
        if t == n or t.startswith(n + " "):
            return name
    return None


def lift(blocks: list[dict], answers: Iterable[str]) -> tuple[list[dict], list[dict]]:
    """Splits the blocks of a document into its body and its answers. An answer opens at a section whose
    heading begins with one of `answers`; it runs to the next section with a known name ("Beschluss"), which
    belongs to the body again or opens the next answer, or to the end."""
    names = list(answers)
    body: list[dict] = []
    found: list[dict] = []
    inside = False
    for b in blocks:
        if b.get("type") == "sec":
            opens = bool(names) and (b.get("sec-type") in names or begins_with(b.get("title") or "", names))
            if opens:
                found.append({"response-type": ANSWER, "title": (b.get("title") or "").strip(), "body": []})
                inside = True
            elif b.get("sec-type"):
                inside = False
        (found[-1]["body"] if inside else body).append(b)
    return body, found


def whole(entry: dict | None) -> list[dict]:
    """The blocks of a document entry in reading order, the answers put back where they stood."""
    if not entry:
        return []
    blocks = list(entry.get("body") or [])
    for r in entry.get("response") or []:
        blocks.extend(r.get("body") or [])
    return sorted(blocks, key=_order) if entry.get("response") else blocks


def _order(block: dict) -> int:
    digits = re.sub(r"\D", "", str(block.get("id") or ""))
    return int(digits) if digits else 0
