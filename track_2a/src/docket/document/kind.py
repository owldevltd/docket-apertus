"""The kind of a document: its role in the affair, not the type of the affair. The submitted text, the
answer to it, the bill of the executive, the minutes, the committee report, the act, the attachment.

The printed type ("Motion", "Beschluss") names the affair and stands on 60 of 64 first pages of the working
set; the role sits in the headline and the section names, which the geometry and the bridge deliver. The
kinds and their words are data (data/knowledge/kinds.json) in the order of the rule: the first kind whose
words are found wins; a document with none of them gets no kind, so nobody takes an attachment for granted.
Measured 8 October 2026 on 48 documents of the file server against a reading by hand: 30 of 48 with the
draft, 36 expected with the answer before the minutes; 8 scans without text have no signal before the reading.
"""

from __future__ import annotations

import re

from docket.document.bridge import Knowledge
from docket.fields.placer import block_text, blocks_of

# the headline of a page: this many of its largest texts
HEADLINE = 3


def document_kind(pages: list[dict], body: list[dict], knowledge: Knowledge,
                  printed_type: str | None = None) -> dict | None:
    """The kind of the document, with its block and why; None when no words of any kind stand on page 1."""
    if not pages or not knowledge.kinds:
        return None
    page = pages[0]
    texts = [e for e in page["elements"] if e["type"] == "text" and (e.get("content") or "").strip()]
    heads = sorted(texts, key=lambda e: -float(e.get("fontSize") or 0))[:HEADLINE]
    headline = " ".join(e["content"] for e in heads).lower()
    first = [c for c in blocks_of(body) if c.get("page") == 1]
    sections = [c for c in first if c["type"] == "sec"]
    text1 = re.sub(r"\s+", " ", " ".join((e.get("content") or "") for e in page["elements"]).lower())
    labels = [lab for lab in knowledge.types if len(lab) > 3 and _word_in(lab, text1)]
    if printed_type:
        labels.append(printed_type.lower())
    signed = any(c["type"] == "sig-block" for c in first)

    for kind in knowledge.kinds:
        if kind.get("rule") is False:
            continue
        hit = _first(kind.get("headline", []), headline)
        if hit:
            return _found(kind, f"'{hit}' in the headline", _block_with(first, hit) or _head_block(first, heads))
        section = _section(kind.get("sections", []), sections)
        if section is not None:
            word = section[1]
            return _found(kind, f"section '{word}'", section[0]["id"])
        words = kind.get("labels", [])
        if words:
            label = next((lab for lab in labels if any(w in lab for w in words)), None)
            if label is None:
                continue
            if _section(kind.get("sections", []), sections) or signed or any(w in headline for w in words):
                why = f"label '{label}'" + (" with a signature block" if signed else " in the headline")
                return _found(kind, why, _block_with(first, label) or _head_block(first, heads))
    return None


def _found(kind: dict, why: str, block: str | None) -> dict:
    return {"kind": kind["id"], "name": kind.get("name", {}), "why": why, "block": block}


def _first(words: list[str], text: str) -> str | None:
    return next((w for w in words if w in text), None)


def _section(words: list[str], sections: list[dict]) -> tuple[dict, str] | None:
    for c in sections:
        name = ((c.get("sec-type") or "") + " " + (c.get("title") or "")).lower()
        for w in words:
            if w in name:
                return c, w
    return None


def _word_in(label: str, text: str) -> bool:
    return re.search(r"(?<![\w])" + re.escape(label) + r"(?![\w])", text) is not None


def _block_with(blocks: list[dict], word: str) -> str | None:
    """The first block of the page whose text holds the word."""
    for c in blocks:
        if word in block_text(c).lower():
            return c["id"]
    return None


def _head_block(blocks: list[dict], heads: list[dict]) -> str | None:
    """The block that holds the largest text of the page."""
    for e in heads:
        cx, cy = e["x"] + e["width"] / 2, e["y"] + e["height"] / 2
        for c in blocks:
            if c["x"] <= cx <= c["x"] + c["width"] and c["y"] <= cy <= c["y"] + c["height"]:
                return c["id"]
    return blocks[0]["id"] if blocks else None
