"""The affair's identity: documents that belong to the same affair get the same key.

The key comes from the read affair number, freed of what stands on the document but is not the number: a prefix
("KR-Nr."), the document number behind the affair number ("15.5098.01"), a version letter ("349a/1994"), digits
the text recognition misread. Where the knowledge holds the number forms of the parliament, the number must have
one of them; otherwise the first page is searched for a number of that form. Without a number the key comes from
what the document gives otherwise and is marked weak ("dok-"). Measured 6 October 2026 on 72 documents: 44 keys
from the number (29 read, 12 found on the page by form), 17 weak.

What is the number and what is not, the forms of the parliament tell (11 October 2026): the number is the part
of the printed text that has one of them, and all of it counts, letters too. "M 1395" and "IUE 1395" are two
affairs in Geneva, "2015.RRGR.1112" is not the affair "2015" of Berne; told without the forms, 27 487 of the
322 383 numbers OpenParlData holds fell onto the key of another number of the same parliament. And the key
names the parliament ("nr-be-2015rrgr1112"): the same number is used by many, 144 123 of the affairs there had
a key that an affair of another parliament had as well.
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
# the same, held against the forms of a parliament: a last group of digits, a letter behind a digit, letters
# in front
LAST_GROUP = re.compile(r"[./\-]\d{1,3}$")
VERSION_LETTER = re.compile(r"(?<=\d)[a-zA-Z](?=[/.\-]|$)")
LETTERS_BEFORE = re.compile(r"^[^\W\d_]+[.\-/\s]*")

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


def key_of(body: str, num: str) -> str:
    """The key of an affair from its parliament and its number as it is compared; without a parliament the
    number alone."""
    return "nr-" + (plain(body) + "-" if body else "") + num


def make_key(values: dict[str, str], file: str, text: str, forms_of: dict[str, dict[str, int]],
             bodies: dict[str, dict], body: str = "") -> Identity:
    """The key from the read values of a document (number, place, parliament, date, title): "nr-..." from the
    parliament and the number, else "dok-..." from place, date and title, else from the file name. With the
    text of the first page and the knowledge the number is held against the forms of the parliament and, if
    need be, looked for on the page; what happened stands in the identity. `body` is the parliament where
    whoever hands the document in has told it; else it is read from the document."""
    body = body or body_of(values.get("place", ""), values.get("parliament", ""), bodies)
    forms = list(forms_of.get(body, {})) if body else []
    read = values.get("number", "")
    num = number(read)
    way = "read number" if num else "no number read"
    found = ""
    fit = fitted(read, forms) if forms and read else ""
    if fit:
        num = plain(fit)
    # when the read number does not fit the forms of the parliament, or is missing, a number of that form on
    # the page counts
    elif forms and text:
        found = search(text, forms)
        if found:
            way = "found on the page" if not num else "read number does not fit the form, found on the page"
            num = plain(found)
        elif num:
            way = "read number does not fit the parliament's form"
    if num:
        return Identity(key_of(body, num), body, read, way, found)
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


# so many capitals at most are the prefix of a number when they stand as a word before it
PREFIX = 3


def attempts(printed: str) -> list[str]:
    """The readings of a printed number that may have the form of a parliament, the fullest first: as it
    stands; without a last group of digits (the document number behind "15.5098.01"); without a letter behind
    a digit (the version in "349a/1994"); without letters in front ("GR.19.196"); and these together."""
    t = printed.strip()
    out = [t]
    for cut in (LAST_GROUP, VERSION_LETTER, LETTERS_BEFORE):
        out += [cut.sub("", x) for x in list(out)]
    seen: list[str] = []
    for x in out:
        if x and re.search(r"\d", x) and x not in seen:
            seen.append(x)
    return seen


def loose(form: str) -> str:
    """A form without the length of its runs ("aa9999" and "aa99" both "a9"): a parliament numbers on, and
    the forms the knowledge holds are only the frequent ones."""
    return re.sub(r"a+", "a", re.sub(r"9+", "9", form))


def fitted(printed: str, forms: list[str]) -> str:
    """The part of a printed number that has one of the forms of the parliament; empty when none has. What
    is printed as a number may differ from the forms in the length of its runs; a word of a whole page may
    not (search)."""
    wide = {loose(f) for f in forms}
    # the fullest reading first: one that fits but for the length of its runs counts before a shorter one
    for attempt in attempts(printed):
        if shape(attempt) in forms or loose(shape(attempt)) in wide:
            return attempt
    return search(printed, forms)


def own(body: str, held: str) -> str:
    """The key of an affair from the number its parliament holds for it: all of the number counts."""
    return key_of(body, plain(held))


def number_in(printed: str, forms: list[str] | None) -> str:
    """The affair number in a printed text as it serves for comparing, by the forms of the parliament: the
    part that has one of them, letters and digits. Without forms, or when no part has one, as `number` tells
    it."""
    fit = fitted(printed, forms) if forms else ""
    return plain(fit) if fit else number(printed)


def search(text: str, forms: list[str]) -> str:
    """The first number on the page that has one of the forms; empty when none. The text holds one element
    of the page per line."""
    for token in text.split():
        for attempt in attempts(token.strip(".,;:()[]")):
            if shape(attempt) in forms:
                return attempt
    # a prefix printed as a word of its own ("M 185", "I 17/23"): capitals, then the number, together of the
    # form. Only within one element: a single letter set large on the page is not the prefix of the next number
    for line in text.splitlines():
        tokens = [token.strip(".,;:()[]") for token in line.split()]
        for prefix, rest in zip(tokens, tokens[1:]):
            if prefix.isalpha() and prefix.isupper() and len(prefix) <= PREFIX and re.match(r"\d", rest) \
                    and shape(prefix + rest) in forms:
                return prefix + " " + rest
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
    # short groups of letters with digits behind them still belong to the number ("20/wa 63/372"), also where
    # an underscore joins the parts ("18_INT_168": without it every affair of Vaud of one year got one key)
    r = re.match(r"^[/.\-\s_]*([a-z]{1,3}[/.\-\s_]*\d[\d./\-\s]*)", rest)
    tail = r.group(1) if r else ""
    return plain(pre + num + tail)
