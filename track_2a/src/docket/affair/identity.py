"""The affair's identity: documents that belong to the same affair get the same key.

The key comes from the read affair number, freed of what stands on the document but is not the number: a prefix
("KR-Nr."), the document number behind the affair number ("15.5098.01"), a version letter ("349a/1994"), digits
the text recognition misread. Where the knowledge holds the number forms of the parliament, the number must have
one of them; otherwise the first page is searched for a number of that form. Without a number the key comes from
what the document gives otherwise and is marked weak ("dok-"). Measured 6 October 2026 on 72 documents: 44 keys
from the number (29 read, 12 found on the page by form), 17 weak.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from docket.fields.placer import day, plain

# the number is the first run of digits with separators, at least two digits; letters before it are a prefix
NUMBER = re.compile(r"\d[\d./\-\s]*\d|\d")

# behind it a document number (".01" after "15.5098"), or a letter as the version ("349a/1994")
DOC_SUFFIX = re.compile(r"^(\d{2}\.\d{4})\.\d{2}$")
VERSION = re.compile(r"(?<=\d)[a-z](?=[/.\-]|$)")

# what the text recognition likes to confuse in numbers
OCR = {"o": "0", "s": "5", "i": "1", "l": "1"}

# the weak key: this many words of the title
TITLE_WORDS = 3


@dataclass
class Identity:
    key: str
    body: str
    read: str
    way: str
    found: str = ""


def make_key(values: dict[str, str], file: str, text: str, forms_of: dict[str, dict[str, int]],
             bodies: dict[str, dict]) -> Identity:
    """The key from the read values of a document (number, place, parliament, date, title): "nr-..." from the
    number, else "dok-..." from place, date and title, else from the file name. With the text of the first page
    and the knowledge the number is held against the forms of the parliament and, if need be, looked for on the
    page; what happened stands in the identity."""
    body = body_of(values.get("place", ""), values.get("parliament", ""), bodies)
    forms = list(forms_of.get(body, {})) if body else []
    read = values.get("number", "")
    num = number(read)
    way = "read number" if num else "no number read"
    found = ""
    # when the read number does not fit the forms of the parliament, or is missing, a number of that form on
    # the page counts
    if forms and text and (not num or shape(read) not in forms):
        found = search(text, forms)
        if found:
            way = "found on the page" if not num else "read number does not fit the form, found on the page"
            num = number(found)
        elif num:
            way = "read number does not fit the parliament's form"
    if num:
        return Identity("nr-" + num, body, read, way, found)
    place = plain(values.get("place") or values.get("parliament") or "")
    d = day(values.get("date", ""))
    title = "-".join(re.sub(r"[\W_]+", " ", values.get("title", "").lower()).split()[:TITLE_WORDS])
    weak = (place + "-" + d + "-" + title).strip("-")
    return Identity("dok-" + (weak if weak and weak != "--" else plain(file)), body, read, way, found)


def shape(number_text: str) -> str:
    """The form of a number: digits become 9, letters a, separators stay, spaces vanish ("15.5098.01" to
    "99.9999.99")."""
    t = re.sub(r"\s+", "", number_text.strip())
    return re.sub(r"[^\W\d_]", "a", re.sub(r"\d", "9", t))


# the word in front of a name that says which of two bodies of the same name is meant ("Kanton Luzern", "Stadt
# Luzern"), in the languages of the documents
LEVEL_WORDS = {
    "canton": re.compile(r"\b(kanton|kantons|canton|cantone|chantun|staat|etat|état|stato)\b", re.I),
    "local": re.compile(
        r"\b(stadt|ville|città|citta|gemeinde|einwohnergemeinde|commune|comune|municipio|municipalité)\b", re.I
    ),
}


def body_of(place: str, parliament: str, bodies: dict[str, dict]) -> str:
    """The parliament for a read place or parliament name, as OpenParlData's body key ("ZH"); empty when
    unknown. The place decides, by the body's name in any language it is held in ("Vaud", "Waadt"). Where a
    canton and a town carry the same name, the word in front of it says which ("Kanton", "Stadt", "canton",
    "ville"), and then the name of the parliament ("Kantonsrat", "Grosser Stadtrat"). The name of the
    parliament alone counts only when it is unambiguous ("Kantonsrat" exists several times)."""
    read = (place + " " + parliament).strip()
    place, parliament = plain(place), plain(parliament)
    strong, weak = [], []

    def fits(w: str, n: str) -> bool:
        return w != "" and n != "" and (w == n or n in w)

    def halls(key: str) -> list[str]:
        b = bodies[key]
        return [plain(str(n)) for n in (b.get("parliaments") or [b.get("parliament")]) if n]

    for key, b in bodies.items():
        towns = [plain(str(n)) for n in (b.get("names") or [b.get("name")]) if n]
        if any(fits(place, t) or fits(parliament, t) for t in towns):
            strong.append(str(key))
        elif any(fits(parliament, h) or fits(place, h) for h in halls(str(key))):
            weak.append(str(key))
    if len(strong) > 1:
        level = next((name for name, words in LEVEL_WORDS.items() if words.search(read)), "")
        if level:
            same = [k for k in strong if (bodies[k].get("level") == "canton") == (level == "canton")]
            strong = same or strong
    if len(strong) > 1:
        named = [k for k in strong if any(fits(parliament, h) for h in halls(k))]
        strong = named if len(named) == 1 else strong
    if len(strong) == 1:
        return strong[0]
    return weak[0] if not strong and len(weak) == 1 else ""


def search(text: str, forms: list[str]) -> str:
    """The first number on the page that has one of the forms; empty when none."""
    for token in text.split():
        token = token.strip(".,;:()[]")
        # also without a prefix of letters ("GR.19.196" to "19.196")
        for attempt in (token, re.sub(r"^[^\W\d_]+[.\-/]?", "", token)):
            if attempt and re.search(r"\d", attempt) and shape(attempt) in forms:
                return attempt
    return ""


def number(text: str) -> str:
    """The affair number as it serves for comparing: letters and digits only, without prefix, without document
    number, without version letter, misread digits corrected. Empty when no number is in it."""
    t = text.strip().lower()
    # misreadings only where a character stands between digits or before a run of digits ("11 S230", "2O1O")
    t = re.sub(r"(?<=\d)[osil](?=\d)|\b[osil](?=\d{2,})", lambda m: OCR[m.group(0)], t)
    # a single letter behind a number is a version ("349a/1994"), not part of the number
    t = VERSION.sub("", t)
    m = NUMBER.search(t)
    if m is None:
        return ""
    at = m.start()
    num = m.group(0).strip()
    # letters right before the number belong to it when there are at least two and no dot or space between
    # ("vnl1000876"; "p135049" and "m 185" not: one letter is a prefix)
    before = t[:at]
    lead = re.search(r"([a-zäöü]+)$", before)
    pre = lead.group(1) if lead and len(lead.group(1)) >= 2 else ""
    d = DOC_SUFFIX.match(num)
    if d:
        num = d.group(1)
    rest = t[m.end():]
    # short groups of letters with digits behind them still belong to the number ("20/wa 63/372")
    r = re.match(r"^[/.\-\s]*([a-z]{1,3}[/.\-\s]*\d[\d./\-\s]*)", rest)
    tail = r.group(1) if r else ""
    return plain(pre + num + tail)
