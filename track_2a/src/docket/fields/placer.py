"""Where a value stands and where it goes: the block on the page that holds it, and its place in the record.

A value counts only with a place. Literal: it stands in a block, a date in any spelling of the same day. Derived:
every word of it stands in the block the model named, only put together differently. Cited: the model named
the block and at least a word of the value stands there; a person has to look. Composed: the model wrote it
(a summary); a person has to look. What the record already holds stays; a different printed value goes beside
it as custom-meta, where the contract has such a place.
"""

from __future__ import annotations

import json
import re
import unicodedata

from docket.affair.validator import Contract
from docket.fields.fields import Field, Fields, has_room
from docket.fluffy import pick_block

# the names a month is written out with, in the languages of the documents; the place in a row is the month
MONTH_NAMES = [
    ["januar", "februar", "märz", "april", "mai", "juni",
     "juli", "august", "september", "oktober", "november", "dezember"],
    ["janvier", "février", "mars", "avril", "mai", "juin",
     "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
     "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"],
    ["january", "february", "march", "april", "may", "june",
     "july", "august", "september", "october", "november", "december"],
]


def bare(t: str) -> str:
    """Lower case and without the marks on letters: a page now and then prints "fevrier" for "février"."""
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if not unicodedata.combining(c))


# every name with the number of its month, with and without the marks on its letters
MONTH = {form: i + 1 for names in MONTH_NAMES for i, name in enumerate(names) for form in (name, bare(name))}
# as a part of a pattern, the longer name first; after the number of the day a point, or what French and
# Italian put there ("1er", "1°")
MONTH_WORDS = "|".join(sorted(MONTH, key=len, reverse=True))
DAY_MARK = r"(?:\.|er|°|º)?"


def fill(record: dict, doc: int, values: dict[str, list[dict]], fields: Fields, contract: Contract,
         body: list[dict], placed: list[dict] | None = None, language: str = "") -> tuple[dict, dict[str, str]]:
    """Builds the values into the record, `values` per field name: value, block, how. Returns the record and a
    note per field: taken, already in the record, differs from the record. With `placed`, every value that
    carries the number of its row ("n") is noted there with where it went: {doc, n, of, source, path}, `of`
    being the row that made the list entry when the value went into the entry of another. `language` is the
    language of the document: a field that is in the document's own language stands under its key."""
    out = json.loads(json.dumps(record))

    def note(hit: dict, source_path: list[str], value_path: list[str], of: int | None = None) -> None:
        if placed is not None and hit.get("n") is not None:
            place = {"doc": doc, "n": hit["n"], "of": of, "source": ".".join(source_path), "path": ".".join(value_path)}
            placed.append(place)

    docs = out.setdefault("docs", {}).setdefault("data", [])
    at = next((i for i, d in enumerate(docs) if d.get("id") == doc), None)
    # the document gets its entry when it has none yet; details about it go there
    if at is None:
        docs.append({"id": doc})
        at = len(docs) - 1
    notes: dict[str, str] = {}
    for name, hits in values.items():
        f = fields.fields[name]
        spath = f.path
        path = own_path(f, language)
        path = ["docs", "data", str(at), *path[3:]] if spath[:3] == ["docs", "data", "[]"] else path
        list_at = path.index("[]") if "[]" in path else None
        rule = contract.part(spath) or {}
        if list_at is None and rule.get("type") == "array":
            # a list of values without entries of their own (keywords): the places go to sources, per value
            have = list(get_at(out, path) or [])
            for hit in hits:
                if hit["value"] in have:
                    continue
                have.append(hit["value"])
                place = {"path": ".".join(path) + f".{len(have) - 1}"}
                out.setdefault("sources", []).append({**place, **source(doc, hit, f, body)})
                note(hit, ["sources", str(len(out["sources"]) - 1)], [*path, str(len(have) - 1)])
            set_at(out, path, have)
            notes[name] = "taken"
            continue
        existing = get_at(record, path)
        if list_at is None and isinstance(existing, (str, int, float)):
            # a field the record already holds: the same stays, a different printed value goes beside it
            for hit in hits:
                if same(f.form, hit["value"], str(existing)):
                    notes[name] = "already in the record"
                    continue
                if not has_room(contract, ["custom-meta"]):
                    # a record without a place beside its fields: the second value stays with its row
                    notes[name] = "differs from the record, no place beside it"
                    continue
                notes[name] = "differs from the record, as custom-meta"
                meta = {"meta-name": name, "meta-value": hit["value"], "source": source(doc, hit, f, body)}
                out.setdefault("custom-meta", []).append(meta)
                beside = ["custom-meta", str(len(out["custom-meta"]) - 1)]
                note(hit, [*beside, "source"], [*beside, "meta-value"])
            continue
        if list_at is None:
            # one value at its path; a place for the source only where the contract has one
            hit = hits[0]
            set_at(out, path, day(hit["value"]) if f.form == "date" else hit["value"])
            parent = contract.part(spath[:-1]) if len(spath) > 1 else None
            if parent and "source" in parent.get("properties", {}):
                set_at(out, [*path[:-1], "source"], source(doc, hit, f, body))
                note(hit, [*path[:-1], "source"], path)
            else:
                out.setdefault("sources", []).append({"path": ".".join(path), **source(doc, hit, f, body)})
                note(hit, ["sources", str(len(out["sources"]) - 1)], path)
            notes[name] = "taken"
            continue
        # lists: every field of the same template goes into the same entries; the first field creates them
        mates = [n for n, o in fields.fields.items() if o.template == f.template]
        if name != mates[0]:
            if mates[0] not in values:
                notes[name] = f"without an entry, since {mates[0]} is missing"
            continue
        into = path[:list_at]
        rows = list(get_at(out, into) or [])
        new = []
        made = []
        # a person the record already names in this list is not created again
        people = (get_at(record, into) or []) if f.lookup == "register" else []
        for hit in hits:
            if people and known(hit["value"], people, path[list_at + 1:]):
                notes[name] = "already in the record"
                continue
            row = json.loads(json.dumps(f.fixed))
            set_at(row, path[list_at + 1:], day(hit["value"]) if f.form == "date" else hit["value"])
            row["source"] = source(doc, hit, f, body)
            entry = [*into, str(len(rows) + len(new))]
            note(hit, [*entry, "source"], [*entry, *path[list_at + 1:]])
            new.append(row)
            made.append(hit)
            notes[name] = "taken"
        # the further fields of the template: one per entry, or a single value for all
        for mate in mates[1:]:
            more = values.get(mate, [])
            if not new or not more:
                continue
            mf = fields.fields[mate]
            for i, row in enumerate(new):
                one = more[0] if len(more) == 1 else (more[i] if i < len(more) else None)
                if one is not None:
                    beside = own_path(mf, language)[list_at + 1:]
                    set_at(row, beside, day(one["value"]) if mf.form == "date" else one["value"])
                    entry = [*into, str(len(rows) + i)]
                    note(one, [*entry, "source"], [*entry, *beside], made[i].get("n"))
            notes[mate] = "taken, into the entries of the first field"
        set_at(out, into, [*rows, *new])
    return out, notes


def read_at(record: dict, f: Field):
    """The value of a field that stands once in a record; of a field that stands under the language of its
    document, the one there is."""
    if not f.own_language:
        return get_at(record, f.path)
    held = get_at(record, f.path[:-1])
    return next((v for v in held.values() if v not in (None, "")), None) if isinstance(held, dict) else None


def own_path(f: Field, language: str) -> list[str]:
    """The path of a field in the record of a document in this language."""
    return [*f.path[:-1], language] if f.own_language and language else list(f.path)


def source(doc: int, hit: dict, f: Field, body: list[dict]) -> dict:
    """The place of a value with its notes: how it got there, and approve where a person should look: not
    found literally or derived, or the block itself carries approve (read from a scan). A value that comes
    with a word on this of its own keeps it: a second opinion marks a value it speaks against
    (docket.fields.second)."""
    how = hit.get("how", "literal")
    how = "composed" if f.free else (how if how in ("literal", "derived") else "cited")
    block = find_block(hit["block"], body)
    out = {"doc": doc, "block": hit["block"], "how": how}
    look = how not in ("literal", "derived") or (block is not None and bool(block.get("approve")))
    if hit.get("approve", look):
        out["approve"] = True
    return out


def locate(value: str, body: list[dict], which: list[int]) -> str | None:
    """The id of the block on the pages in which the value stands literally; None when none. A date in any
    spelling of the same day. Of several blocks the header entry before the running text."""
    found = {c["id"]: c for c in blocks_of(body) if c["page"] in which and within(value, block_text(c))}
    return pick_block(value, found) if found else None


def blocks_of(body: list[dict]) -> list[dict]:
    """Every block of the body, the ones inside sections too."""
    out = []
    for b in body:
        out.append(b)
        if b["type"] == "sec":
            out.extend(b.get("content", []))
    return out


def find_block(ident: str | None, body: list[dict], which: list[int] | None = None) -> dict | None:
    """The block with this id, on these pages when given."""
    if ident is None:
        return None
    for c in blocks_of(body):
        if c["id"] == ident and (which is None or c["page"] in which):
            return c
    return None


def block_text(block: dict | None) -> str:
    if not block:
        return ""
    if "rows" in block:
        return " ".join(cell for row in block["rows"] for cell in row)
    if "items" in block:
        return " ".join(f"{i['term']}: {i['def']}" if isinstance(i, dict) else i for i in block["items"])
    return str(block.get("title") or block.get("text") or "")


def day(t: str) -> str:
    """The day as YYYY-MM-DD from "22.11.2018", "2018-11-22" or written out with the name of the month in
    German, French, Italian or English ("22. November 2018", "1er mars 2020", "3 marzo 2020"); empty when
    none."""
    t = t.lower()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", t)
    if m:
        return f"{int(m.group(3)):04d}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.search(r"(\d{1,2})" + DAY_MARK + r"\s*(" + MONTH_WORDS + r")\s*(\d{4})", t)
    if m:
        return f"{int(m.group(3)):04d}-{MONTH[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return ""


def plain(t: str) -> str:
    """Letters and digits only, lower case."""
    return re.sub(r"[\W_]+", "", t.lower())


def within(value: str, text: str) -> bool:
    """Whether the value stands literally in the text; a date in any usual spelling of the same day, the month
    written out in any of the languages of the documents."""
    d = day(value)
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", d) if d else None
    if m:
        flat = bare(re.sub(r"\s+", "", text))
        year, month, dd = m.group(1), m.group(2), m.group(3)
        forms = [f"{int(dd)}.{int(month)}.{year}", f"{dd}.{month}.{year}", d]
        # written out: the name of the month in each language, the day with a point, bare, or as "1er", "1°"
        names = {bare(row[int(month) - 1]) for row in MONTH_NAMES}
        forms += [f"{int(dd)}{mark}{name}{year}" for name in names for mark in (".", "", "er", "°", "º")]
        # no digit before it, else the 9th hides in the 19th
        return any(re.search(r"(?<!\d)" + re.escape(form), flat) for form in forms)
    return plain(value) != "" and plain(value) in plain(text)


def same(form: str, a: str, b: str) -> bool:
    """Whether two values say the same: for a date the same day, else the same letters and digits."""
    if form == "date":
        return day(a) != "" and day(a) == day(b)
    return plain(a) == plain(b)


def known(name: str, people: list[dict], key: list[str]) -> bool:
    """Whether a person of this name is already among the entries, the name standing at `key` in each: every
    word of the name in one entry."""
    for p in people:
        full = plain(str(get_at(p, key) or ""))
        if full and all(plain(w) == "" or plain(w) in full for w in name.split()):
            return True
    return False


def overlap(value: str, text: str) -> float:
    """Share of the value's words (from four characters) that occur in the text; 0 to 1."""
    ws = [w for w in _plain_words(value).split() if len(w) >= 4]
    if not ws:
        return 0.0
    haystack = " " + _plain_words(text) + " "
    return round(sum(1 for w in ws if " " + w + " " in haystack) / len(ws), 2)


def covers(value: str, text: str) -> bool:
    """Whether every word of the value, short ones and numbers too, stands in the text."""
    ws = _plain_words(value).split()
    haystack = " " + _plain_words(text) + " "
    return bool(ws) and all(" " + w + " " in haystack for w in ws)


def words(text: str) -> int:
    return len(_plain_words(text).split())


def _plain_words(t: str) -> str:
    return re.sub(r"[\W_]+", " ", t.lower()).strip()


def get_at(data, path: list[str]):
    """The value at a path through dicts and lists; None where there is none."""
    for key in path:
        if isinstance(data, list):
            if not key.isdigit() or int(key) >= len(data):
                return None
            data = data[int(key)]
        elif isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data


def set_at(data, path: list[str], value) -> None:
    """Sets the value at a path, creating the dicts on the way."""
    at = data
    for key in path[:-1]:
        if isinstance(at, list):
            at = at[int(key)]
            continue
        if not isinstance(at.get(key), (dict, list)):
            at[key] = {}
        at = at[key]
    if isinstance(at, list):
        at[int(path[-1])] = value
    else:
        at[path[-1]] = value
