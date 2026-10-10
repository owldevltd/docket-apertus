"""A second opinion on where the value of a field stands, without the model, learnt from the rows of the store.

Two ways name a block for a field. The place: where in the documents of a parliament the value usually stood,
told by the page and a coarse grid over it. The network: a small net that has learnt, from every block that
held a value, what such a block looks like: its page and box, its kind, its font, its length, its share of
digits and capitals, whether a date stands in it, its place in the reading order, the parliament. No word of
the text goes in. The teacher is what the model read, and where a person decided, what the person said.

Neither is trusted by a number somebody chose. When they are learnt they are tried on documents held back:
the place on each document of a parliament from the others, the network on a fifth of the documents from the
other four. An opinion agrees when the value that counts stands in the block it names (it was taken from
that block, or it stands there literally) and what the code itself fetches from that block by the field's
form, where it can fetch anything, is the same value. Per parliament and
field for the place, per field for the network, the cut is taken at which agreeing outweighs disagreeing by
most, and the way is used only where it outweighs at all.

In a run the opinion stands beside the model. Where the model found no value, what has the form of the field
in the named block is taken and marked for a person to look at. Where the model's value does not stand in the
named block, the value stays and is marked. Where the two agree, nothing changes: the agreement is noted at
the row, and a mark the model's reading set stays (measured on documents held back, 10 October 2026: of 97
wrong values 57 pass unmarked without a second opinion, 54 if agreeing took the mark off, 29 as it is).

For a field of several values, a list of names, only a network speaks, one of its own, and it names every
block it takes to hold some of them. A value the model placed in another block is marked. It fills no gap
there: which names of a block belong to the field the look of the block does not tell. Tried the same way, it
is kept for few such fields: on 151 documents for the authors alone, on four fifths of them for none.
"""

from __future__ import annotations

import math
import re
import zlib
from collections import Counter

import numpy as np

from docket.affair.identity import number, search
from docket.fields.fields import Field, Fields
from docket.fields.placer import block_text, blocks_of, day, plain, within
from docket.store.base import Store
from docket.store.vocabulary import Vocabulary

# a page at 300 dpi, the least a block's place is measured against, and the grid a place is told by: bands
# from the top and from the left
PAGE = (2480, 3508)
BANDS = (10, 4)
KINDS = ("p", "sec", "def-list", "list", "table", "graphic", "sig-block")
# the parts the documents are split into to try the network, its size, and the cuts that are tried
FOLDS = 5
HIDDEN, EPOCHS, RATE = 32, 400, 0.01
CUTS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


def speaks_for(f: Field) -> bool:
    """Whether a second opinion is formed for the field: not for wording the model composed."""
    return not f.free


def several(f: Field) -> bool:
    """Whether the field holds several values (a list of names): then the opinion names every block that
    holds some of them, not one block for the one value."""
    return f.form == "list"


def _boxes(blocks: list[dict]) -> list[tuple[int, float, float, float, float]]:
    """Per block its page and its box as shares of the page."""
    wide = max([PAGE[0], *(float(b["x"]) + float(b["width"]) for b in blocks)])
    high = max([PAGE[1], *(float(b["y"]) + float(b["height"]) for b in blocks)])
    return [(int(b.get("page") or 1), float(b["x"]) / wide, float(b["y"]) / high, float(b["width"]) / wide,
             float(b["height"]) / high) for b in blocks]


def zones(blocks: list[dict]) -> list[tuple[int, int, int]]:
    """Per block the place it stands at: its page, the band from the top and the band from the left its
    middle falls into."""
    return [(page, min(BANDS[0] - 1, int((y + h / 2) * BANDS[0])), min(BANDS[1] - 1, int((x + w / 2) * BANDS[1])))
            for page, x, y, w, h in _boxes(blocks)]


def features(blocks: list[dict], parliament: str, parliaments: list[str]) -> np.ndarray:
    """What the network sees of every block of a document; nothing of it is a word of the text."""
    sizes = sorted(float(b.get("font-size") or 0) for b in blocks if b.get("font-size"))
    median = sizes[len(sizes) // 2] if sizes else 0.0
    per_page = Counter(int(b.get("page") or 1) for b in blocks)
    seen: Counter = Counter()
    rows = []
    for i, (b, (page, x, y, w, h)) in enumerate(zip(blocks, _boxes(blocks))):
        seen[page] += 1
        t = block_text(b)
        letters = [c for c in t if c.isalpha()]
        size = float(b.get("font-size") or 0)
        rows.append([
            1.0 if page == 1 else 0.0, min(page, 4) / 4, x, y, w, h, x + w / 2, y + h / 2,
            *[1.0 if b.get("type") == k else 0.0 for k in KINDS],
            size / median if median and size else 1.0,
            1.0 if re.search(r"fett|bold|gras|grassetto", str(b.get("font") or ""), re.I) else 0.0,
            math.log1p(len(t.split())), math.log1p(len(t)),
            sum(c.isdigit() for c in t) / max(1, len(t)), sum(c.isupper() for c in letters) / max(1, len(letters)),
            1.0 if day(t) else 0.0, 1.0 if ":" in t else 0.0, 1.0 if t[:1].isdigit() else 0.0,
            1.0 if len(t.split()) <= 3 else 0.0,
            i / max(1, len(blocks) - 1), seen[page] / max(1, per_page[page]),
            *[1.0 if parliament == p else 0.0 for p in parliaments],
        ])
    return np.array(rows, dtype=np.float64).reshape(len(blocks), -1)


def counted(rows: list[dict]) -> dict[str, dict]:
    """Per field the value that counts and the block it stands in, from the rows of a document: the first
    placed value the model read, as a person left it. A value a person rejected does not count, and a value a
    second opinion put in is no teacher."""
    out: dict[str, dict] = {}
    for row in sorted(rows, key=lambda r: r["n"]):
        if row["state"] != "placed" or row["field"] in out or row.get("by"):
            continue
        decided = next((d for d in row.get("decisions") or [] if d.get("of") is None and not d.get("part")), None)
        if decided is not None and decided["review"].get("decision") == "rejected":
            continue
        value = decided["value"] if decided is not None and decided.get("value") is not None else row["value"]
        out[row["field"]] = {"value": str(value), "block": row["block"]}
    return out


def stood(rows: list[dict]) -> dict[str, set[str]]:
    """Per field every block a value of it stands in, from the rows of a document: what the model read, as far
    as a person did not reject it."""
    out: dict[str, set[str]] = {}
    for row in rows:
        if row["state"] != "placed" or row.get("by") or row.get("about"):
            continue
        if any(d["review"].get("decision") == "rejected" and not d.get("part") for d in row.get("decisions") or []):
            continue
        out.setdefault(row["field"], set()).add(row["block"])
    return out


def fetch(f: Field, text: str, parliament: str, forms: dict[str, dict[str, int]],
          vocabulary: Vocabulary) -> str | None:
    """What in the text of a block has the form of the field; None when nothing has."""
    flat = re.sub(r"\s+", " ", text).strip()
    if not flat:
        return None
    if f.role == "number":
        # the form of the parliament first; a printed number often carries an addition the forms do not know
        found = search(flat, list(forms.get(parliament, {})))
        return found or (flat if len(flat.split()) <= 3 and number(flat) else None)
    if f.form == "date":
        return day(flat) or None
    if f.lookup == "vocabulary":
        low = " " + flat.lower() + " "
        names = [r["label"] for r in vocabulary.names(f.list_name, parliament)]
        hits = [n for n in names
                if re.search(r"(?<![^\W\d_])" + re.escape(n.lower()) + r"(?![^\W\d_])", low)]
        return max(hits, key=len) if hits else None
    if f.block_text:
        return flat
    return None


def agrees(f: Field, value: str, at: str | None, block: dict, parliament: str, forms: dict[str, dict[str, int]],
           vocabulary: Vocabulary) -> bool:
    """Whether a value and the block an opinion names agree: the value was taken from that block or stands
    there literally, and what the code itself fetches from the block by the field's form, if it can fetch
    anything, is the same value. Held against OpenParlData's values for number, title, type and date on
    documents held back (10 October 2026): a value that agreed was right in 229 of 283 cases, one that did not
    in 33 of 76, the model's values overall in 271 of 370."""
    text = block_text(block)
    if at != block["id"] and not within(value, text):
        return False
    fetched = fetch(f, text, parliament, forms, vocabulary)
    if fetched is None:
        return True
    if f.role == "number":
        return number(fetched) == number(value)
    if f.form == "date":
        return day(fetched) == day(value)
    a, b = plain(fetched), plain(value)
    return bool(a) and bool(b) and (a in b or b in a)


def _best_cut(tried: list[tuple[float, bool]], cuts) -> dict:
    """Of the cuts the one at which agreeing outweighs disagreeing by most, the lowest of several; `tried` is
    per held-back document how sure the opinion was and whether it agreed. The way is used when agreeing
    outweighs at that cut; the counts are told either way."""
    best: dict | None = None
    for cut in sorted(cuts):
        agree = sum(1 for sure, ok in tried if sure >= cut and ok)
        disagree = sum(1 for sure, ok in tried if sure >= cut and not ok)
        if best is None or agree - disagree > best["agree"] - best["disagree"]:
            best = {"cut": cut, "agree": agree, "disagree": disagree}
    best = best or {"cut": None, "agree": 0, "disagree": 0}
    return {**best, "use": best["agree"] > best["disagree"]}


def _best_cut_several(tried: list[tuple[float, bool]], cuts) -> dict:
    """The same for a field of several values; `tried` is per block of the held-back documents how sure the
    network was and whether the block holds the field. A named block that holds it agrees; a named block that
    does not, and a block that holds it and is not named, disagree."""
    holding = sum(1 for _, ok in tried if ok)
    best: dict | None = None
    for cut in sorted(cuts):
        agree = sum(1 for sure, ok in tried if sure >= cut and ok)
        disagree = sum(1 for sure, ok in tried if sure >= cut and not ok) + holding - agree
        if best is None or agree - disagree > best["agree"] - best["disagree"]:
            best = {"cut": cut, "agree": agree, "disagree": disagree}
    best = best or {"cut": None, "agree": 0, "disagree": 0}
    return {**best, "use": best["agree"] > best["disagree"]}


def _train(x: np.ndarray, y: np.ndarray, seed: int = 1) -> dict:
    """One hidden layer, a sigmoid per field, cross entropy, Adam; a block that holds a field weighs more,
    since most blocks hold none."""
    rng = np.random.default_rng(seed)
    mu, sd = x.mean(0), x.std(0) + 1e-6
    x = (x - mu) / sd
    params = [rng.normal(0, math.sqrt(2 / x.shape[1]), (x.shape[1], HIDDEN)), np.zeros(HIDDEN),
              rng.normal(0, math.sqrt(2 / HIDDEN), (HIDDEN, y.shape[1])), np.zeros(y.shape[1])]
    weight = np.clip((len(y) - y.sum(0)) / np.maximum(1, y.sum(0)), 1, 30)
    first = [np.zeros_like(p) for p in params]
    second = [np.zeros_like(p) for p in params]
    for step in range(1, EPOCHS + 1):
        hidden = np.maximum(0, x @ params[0] + params[1])
        out = 1 / (1 + np.exp(-(hidden @ params[2] + params[3])))
        g = (out - y) * (1 + (weight - 1) * y) / len(x)
        back = (g @ params[2].T) * (hidden > 0)
        grads = [x.T @ back + 1e-4 * params[0], back.sum(0), hidden.T @ g + 1e-4 * params[2], g.sum(0)]
        for k in range(4):
            first[k] = 0.9 * first[k] + 0.1 * grads[k]
            second[k] = 0.999 * second[k] + 0.001 * grads[k] ** 2
            params[k] -= RATE * (first[k] / (1 - 0.9 ** step)) / (np.sqrt(second[k] / (1 - 0.999 ** step)) + 1e-8)
    return {"mu": mu, "sd": sd, "w1": params[0], "b1": params[1], "w2": params[2], "b2": params[3]}


def _scores(net: dict, x: np.ndarray) -> np.ndarray:
    hidden = np.maximum(0, ((x - np.asarray(net["mu"])) / np.asarray(net["sd"])) @ np.asarray(net["w1"])
                        + np.asarray(net["b1"]))
    return 1 / (1 + np.exp(-(hidden @ np.asarray(net["w2"]) + np.asarray(net["b2"]))))


def learn(documents: list[dict], fields: Fields, forms: dict[str, dict[str, int]], vocabulary: Vocabulary) -> dict:
    """Learns both ways from the documents of a store ({name, parliament, blocks, rows}) and tries them on
    documents held back. Returns what a run needs, with what the trying showed: per parliament and field the
    place, per field the network's cut, each with how often it agreed and disagreed and whether it is used."""
    names = [n for n, f in fields.fields.items() if speaks_for(f)]
    docs = []
    for d in documents:
        blocks = [b for b in blocks_of(d["blocks"]) if b.get("y") is not None]
        if blocks:
            docs.append({**d, "blocks": blocks, "counts": counted(d["rows"]), "stood": stood(d["rows"]),
                         "zones": zones(blocks)})
    out: dict = {"documents": len(docs), "places": {}, "network": None, "lists": None}

    # the place, per parliament: every document from the others
    for parliament in sorted({d["parliament"] for d in docs if d["parliament"]}):
        own = [d for d in docs if d["parliament"] == parliament]
        for name in (n for n in names if not several(fields.fields[n])):
            at_zone = []
            for d in own:
                block = (d["counts"].get(name) or {}).get("block")
                z = next((z for b, z in zip(d["blocks"], d["zones"]) if b["id"] == block), None)
                if z is not None:
                    at_zone.append((d, z))
            if len(at_zone) < 3:
                continue
            tried = []
            for d, _ in at_zone:
                others = Counter(z for o, z in at_zone if o is not d)
                top, count = others.most_common(1)[0]
                at = next((b for b, z in zip(d["blocks"], d["zones"]) if z == top), None)
                # a place counts as usual when more than one other document has the value there
                if count < 2 or at is None:
                    continue
                counts = d["counts"][name]
                ok = agrees(fields.fields[name], counts["value"], counts["block"], at, parliament, forms, vocabulary)
                tried.append((count / sum(others.values()), ok))
            cut = _best_cut(tried, sorted({share for share, _ in tried}))
            top, count = Counter(z for _, z in at_zone).most_common(1)[0]
            out["places"].setdefault(parliament, {})[name] = {
                "zone": list(top), "share": round(count / len(at_zone), 3), "documents": len(at_zone), **cut}

    # the networks, over all documents: every fifth from the other four. One for the fields with one value and
    # one for the fields of several: learnt together, the lists took from the others (10 October 2026: with
    # one network the type of 28 instead of 13 right values was spoken against)
    if len(docs) >= FOLDS:
        out["network"] = _network(docs, [n for n in names if not several(fields.fields[n])], fields, forms, vocabulary)
        out["lists"] = _network(docs, [n for n in names if several(fields.fields[n])], fields, forms, vocabulary)
    return out


def _network(docs: list[dict], names: list[str], fields: Fields, forms: dict[str, dict[str, int]],
             vocabulary: Vocabulary) -> dict | None:
    """A network for these fields, tried on every fifth of the documents from the other four, then learnt
    from all; None without fields."""
    if not names:
        return None
    parliaments = sorted({d["parliament"] for d in docs if d["parliament"]})
    x = [features(d["blocks"], d["parliament"], parliaments) for d in docs]
    y = []
    for d in docs:
        ids = {b["id"]: i for i, b in enumerate(d["blocks"])}
        marks = np.zeros((len(d["blocks"]), len(names)))
        for j, name in enumerate(names):
            if several(fields.fields[name]):
                for block in d["stood"].get(name, ()):
                    if block in ids:
                        marks[ids[block], j] = 1.0
            elif name in d["counts"] and d["counts"][name]["block"] in ids:
                marks[ids[d["counts"][name]["block"]], j] = 1.0
        y.append(marks)
    part = [zlib.crc32(d["name"].encode("utf-8")) % FOLDS for d in docs]
    tried: dict[str, list[tuple[float, bool]]] = {name: [] for name in names}
    for k in range(FOLDS):
        train = [i for i in range(len(docs)) if part[i] != k]
        if not train or len(train) == len(docs):
            continue
        net = _train(np.vstack([x[i] for i in train]), np.vstack([y[i] for i in train]))
        for i in (i for i in range(len(docs)) if part[i] == k):
            scores = _scores(net, x[i])
            for j, name in enumerate(names):
                if several(fields.fields[name]):
                    holding = docs[i]["stood"].get(name)
                    if holding:
                        tried[name].extend((float(scores[n, j]), b["id"] in holding)
                                           for n, b in enumerate(docs[i]["blocks"]))
                elif name in docs[i]["counts"]:
                    best = int(np.argmax(scores[:, j]))
                    counts = docs[i]["counts"][name]
                    ok = agrees(fields.fields[name], counts["value"], counts["block"], docs[i]["blocks"][best],
                                docs[i]["parliament"], forms, vocabulary)
                    tried[name].append((float(scores[best, j]), ok))
    net = _train(np.vstack(x), np.vstack(y))
    return {
        "fields": names, "parliaments": parliaments,
        **{k: np.asarray(v).round(6).tolist() for k, v in net.items()},
        "cuts": {name: (_best_cut_several if several(fields.fields[name]) else _best_cut)(tried[name], CUTS)
                 for name in names},
    }


def from_store(store: Store) -> list[dict]:
    """The documents of a store as learn takes them: per document its parliament (as the run told it), its
    blocks from the affair's record and its rows."""
    out = []
    for affair in store.list_affairs():
        entries = {e.get("id"): e for e in (affair["record"].get("docs") or {}).get("data", [])}
        for document in affair["documents"]:
            rows = [r for r in store.get_rows(document["name"]) if r.get("affair") == affair["key"]]
            body = (entries.get(document["id"]) or {}).get("body") or []
            report = store.get_fields(document["name"]) or {}
            if rows and body:
                out.append({"name": document["name"], "blocks": body, "rows": rows,
                            "parliament": str((report.get("identity") or {}).get("body") or "")})
    return out


def opinions(blocks: list[dict], parliament: str, fields: Fields, learnt: dict) -> dict[str, dict]:
    """Per field the block a second opinion names in a document, and by which way; of the two ways the one
    that outweighed by more when it was tried. Only ways the trying kept."""
    blocks = [b for b in blocks_of(blocks) if b.get("y") is not None]
    out: dict[str, dict] = {}
    if not blocks or not learnt:
        return out
    by_zone: dict[tuple, dict] = {}
    for b, z in zip(blocks, zones(blocks)):
        by_zone.setdefault(z, b)
    for name, place in ((learnt.get("places") or {}).get(parliament) or {}).items():
        at = by_zone.get(tuple(place["zone"]))
        if place.get("use") and at is not None and place["share"] >= place["cut"] and name in fields.fields:
            out[name] = {"block": at["id"], "by": "place", "gain": place["agree"] - place["disagree"]}
    for net in (learnt.get("network"), learnt.get("lists")):
        if not net:
            continue
        scores = _scores(net, features(blocks, parliament, net["parliaments"]))
        for j, name in enumerate(net["fields"]):
            cut = net["cuts"].get(name) or {}
            best = int(np.argmax(scores[:, j]))
            gain = cut.get("agree", 0) - cut.get("disagree", 0)
            if not cut.get("use") or name not in fields.fields:
                continue
            if several(fields.fields[name]):
                named = [b["id"] for n, b in enumerate(blocks) if scores[n, j] >= cut["cut"]]
                out[name] = {"blocks": named, "by": "network", "gain": gain}
            elif scores[best, j] >= cut["cut"] and gain > out.get(name, {}).get("gain", 0):
                out[name] = {"block": blocks[best]["id"], "by": "network", "gain": gain}
    return out


def apply(doc: str, rows: list[dict], blocks: list[dict], parliament: str, fields: Fields, learnt: dict,
          forms: dict[str, dict[str, int]], vocabulary: Vocabulary) -> int:
    """Holds the second opinion against the rows of a document, in place: a value it speaks against is marked,
    a value it agrees with is noted as such, and where the model found none, what has the form of the field
    in the named block becomes a row of its own, marked. Returns how many rows it touched or added."""
    by_id = {b["id"]: b for b in blocks_of(blocks)}
    touched = 0
    for name, opinion in opinions(blocks, parliament, fields, learnt).items():
        f = fields.fields[name]
        mine = [r for r in rows if r["field"] == name and r["state"] == "placed" and not r.get("by")]
        if "blocks" in opinion:
            # several values: a value in a block the network does not take for one of this field is marked
            for row in mine:
                ok = row["block"] in opinion["blocks"]
                if not ok:
                    row["approve"] = True
                row["second"] = {"by": opinion["by"], "agrees": ok}
                touched += 1
            continue
        text = block_text(by_id.get(opinion["block"]))
        if mine:
            row = mine[0]
            ok = agrees(f, str(row["value"]), row["block"], by_id[opinion["block"]], parliament, forms, vocabulary)
            # agreeing leaves the value as the model's reading marked it; only speaking against it adds a mark
            if not ok:
                row["approve"] = True
            row["second"] = {"by": opinion["by"], "block": opinion["block"], "agrees": ok}
            touched += 1
            continue
        value = fetch(f, text, parliament, forms, vocabulary) if speaks_for(f) else None
        at = by_id.get(opinion["block"])
        if value is None or at is None:
            continue
        rows.append({
            "doc": doc, "n": max((r["n"] for r in rows), default=-1) + 1,
            "entity": f.entity, "role": f.role, "field": name, "entry": 0, "value": value, "state": "placed",
            "how": "literal", "block": at["id"], "page": at.get("page"),
            "box": [at.get(k) for k in ("x", "y", "width", "height")], "approve": True, "by": opinion["by"],
        })
        touched += 1
    return touched
