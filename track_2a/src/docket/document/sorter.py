"""What the bridge leaves over, the model sorts: per call the text image of a page with a few marked places and
the question what each place is. The answer becomes the block. What gets no answer becomes a paragraph, so that
every text has a place. Measured 6 October 2026: six places per call; the same answer in both of two runs for
64 of 150 places, so this is in the pipeline as the lesser evil, not as a finding."""

from __future__ import annotations

import re
from pathlib import Path

from docket.document.picture import text_image
from docket.model.client import Client, ask

BUNDLE = 6

# what is offered, and which block it becomes; margin and footnote have no block of their own in the body
KINDS = {
    "Überschrift": ("Titel des Dokuments oder eines Abschnitts", "head"),
    "Absatz": ("ein Satz oder Fliesstext", "p"),
    "Aufzählungspunkt": ("ein Punkt einer Liste", "list"),
    "Bezeichnung": ('ein Feldname wie "Datum:" oder "Eingereicht von:", mit oder ohne Wert dahinter', "def-list"),
    "Angabe": (
        "ein einzelner Wert wie eine Nummer, ein Datum, ein Ort oder ein Name, der zum Kopf des Dokuments gehört", "p"
    ),
    "Unterschrift": ("Name oder Amt von jemandem, der das Dokument unterschreibt", "sig-block"),
    "Seitenrand": ("Seitenzahl, Briefkopf, Absender oder Fusszeile", "p"),
    "Fussnote": ("Anmerkung am Seitenende", "p"),
}


def sort_rest(
    client: Client | None, pages: list[dict], rest: list[dict], only: list[int], log: Path | None = None
) -> tuple[dict[int, str], dict[str, int]]:
    """Kinds for the rest of the pages in `only` (1 ...) from the model; the rest of every page becomes a
    paragraph. Returns the kind per index of the rest and how often each answer was given."""
    kinds: dict[int, str] = {}
    count: dict[str, int] = {}
    for n in only:
        page = pages[n - 1]
        on_page = [i for i, e in enumerate(rest) if e["page"] == n and e.get("content")]
        indexes = sorted(on_page, key=lambda i: (rest[i]["y"], rest[i]["x"]))
        for k in range(0, len(indexes), BUNDLE):
            chunk = indexes[k : k + BUNDLE]
            if client is None or client.halted:
                break
            answer = _ask(client, page, [rest[i] for i in chunk], n, log)
            for line in (answer or "").splitlines():
                m = re.match(r"^\s*\[?(\d+)\]?\s*[:.\-]\s*(.+?)\s*$", line)
                if not m or not 1 <= int(m.group(1)) <= len(chunk):
                    continue
                for kind, (_, block) in KINDS.items():
                    if m.group(2).lower().startswith(kind.lower()):
                        kinds[chunk[int(m.group(1)) - 1]] = block
                        count[kind] = count.get(kind, 0) + 1
    for i, e in enumerate(rest):
        if i not in kinds and e.get("content"):
            kinds[i] = "p"
            count["ohne Antwort"] = count.get("ohne Antwort", 0) + 1
    return kinds, count


def _ask(client: Client, page: dict, chunk: list[dict], n: int, log: Path | None) -> str | None:
    """Marks the places in the text image (the same element of the page, found by position and content)."""
    marks: dict[int, str] = {}
    for k, e in enumerate(chunk, 1):
        box = (e["x"], e["y"], e["width"], e["height"])
        for i, o in enumerate(page["elements"]):
            same_box = (o["x"], o["y"], o["width"], o["height"]) == box
            if same_box and (o.get("content") or "") == (e.get("content") or ""):
                marks[i] = f"[{k}]"
                break
    k = len(chunk)
    where = "Eine Stelle ist mit [1] markiert." if k == 1 else f"{k} Stellen sind mit [1] bis [{k}] markiert."
    choices = "\n".join(f"- {kind}: {what}" for kind, (what, _) in KINDS.items())
    prompt = (
        f"Unten steht Seite {n} eines Dokuments aus einem Schweizer Parlament als Text, "
        "ungefähr so angeordnet wie auf dem Papier. "
        f"[Bild] steht für ein Bild, einen Stempel oder eine Unterschrift. {where}\n\n"
        f"-----\n{text_image(page, marks)}\n-----\n\n"
        f"Sage für jede markierte Stelle, was sie ist. Zur Wahl:\n{choices}\n\n"
        'Antworte mit genau einer Zeile je Stelle, in der Form "1: Überschrift", ohne weiteren Text.'
    )
    answer = ask(client, prompt, room=200, log=log, tag=f"sort page {n}")
    return answer.text if answer else None
