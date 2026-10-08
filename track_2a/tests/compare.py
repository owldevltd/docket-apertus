"""Holds the object layer against the reference from the PDF.

Counting rule: a word belongs to the object whose box contains the centre of its ink (the smallest one when
several do). Lines and blocks follow from their words.
"""

from __future__ import annotations

# an image from this share of the page on is the page itself (a scan), not an object on it
PAGE_IMAGE = 0.5


def compare(ref: dict, got: dict) -> dict:
    pad = got["scale"]
    words = []
    per_object: dict[int, dict] = {}
    for word in ref["words"]:
        if not word.get("ink"):
            continue
        w = dict(word)
        cx = w["ink"]["x"] + w["ink"]["w"] // 2
        cy = w["ink"]["y"] + w["ink"]["h"] // 2
        w["obj"] = inside(got["objects"], cx, cy, 0)
        w["state"] = "object"
        if w["obj"] < 0:
            w["state"] = "line" if inside(got["lines"], cx, cy, pad) >= 0 else "missed"
        else:
            per_object.setdefault(w["obj"], {})[w["block"]] = True
        words.append(w)

    lines = group(words, "line")
    blocks = group(words, "block")
    for b in blocks.values():
        if b["state"] == "whole":
            b["state"] = "merged" if len(per_object[b["objs"][0]]) > 1 else "single"
        elif b["state"] == "cut":
            cut = [line for line in b["lines"] if lines[line]["state"] == "cut"]
            b["state"] = "cut inside a line" if cut else "cut between lines"

    # raster images count only where the page is not an image itself
    page = ref["width"] * ref["height"]
    images = []
    for image in ref.get("images", []):
        if not image.get("ink") or ref["kind"].startswith("scan") or image["w"] * image["h"] > PAGE_IMAGE * page:
            continue
        im = dict(image)
        area = im["ink"]["w"] * im["ink"]["h"]
        im["objs"] = [i for i, o in enumerate(got["objects"]) if overlap(o, im["ink"]) * 2 > min(o["w"] * o["h"], area)]
        im["state"] = "missed" if not im["objs"] else ("one object" if len(im["objs"]) == 1 else "several objects")
        images.append(im)

    objects = []
    largest = 0
    for i, o in enumerate(got["objects"]):
        obj = dict(o)
        largest = max(largest, o["w"] * o["h"])
        n = len(per_object.get(i, {}))
        obj["state"] = "several blocks" if n > 1 else ("one block" if n == 1 else "no reference")
        if n == 0 and any(i in im["objs"] for im in images):
            obj["state"] = "image"
        objects.append(obj)

    return {
        "count": {
            "words": tally(words, ["object", "line", "missed"]),
            "lines": tally(list(lines.values()), ["whole", "cut", "line", "missed"]),
            "blocks": tally(
                list(blocks.values()), ["single", "merged", "cut between lines", "cut inside a line", "line", "missed"]
            ),
            "images": tally(images, ["one object", "several objects", "missed"]),
            "objects": tally(objects, ["one block", "several blocks", "image", "no reference"]),
        },
        # share of the largest object in the page: a page-sized object catches every word
        "share": largest / page,
        "words": words,
        "lines": lines,
        "blocks": blocks,
        "images": images,
        "objects": objects,
    }


def group(words: list[dict], key: str) -> dict:
    """Words gathered into the lines or blocks of the reference. whole = all words in the same object, cut =
    spread over several, line = only found as a line, missed = at least one word in no object."""
    sets: dict = {}
    for w in words:
        sets.setdefault(w[key], []).append(w)
    out = {}
    for ident, members in sets.items():
        x0 = min(w["ink"]["x"] for w in members)
        y0 = min(w["ink"]["y"] for w in members)
        x1 = max(w["ink"]["x"] + w["ink"]["w"] for w in members)
        y1 = max(w["ink"]["y"] + w["ink"]["h"] for w in members)
        objs: list[int] = []
        miss = []
        text = ""
        last = None
        for w in members:
            if w["state"] == "missed":
                miss.append(w["t"])
            if w["obj"] >= 0 and w["obj"] not in objs:
                objs.append(w["obj"])
            # make the cuts visible in the text
            text += ("" if text == "" else (" ¦ " if last is not None and w["obj"] != last else " ")) + w["t"]
            last = w["obj"]
        out[ident] = {
            "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
            "t": text,
            "lines": sorted({w["line"] for w in members}),
            "objs": objs,
            "miss": miss,
            "state": "missed" if miss else ("cut" if len(objs) > 1 else ("whole" if objs else "line")),
        }
    return out


def inside(boxes: list[dict], x: int, y: int, pad: int) -> int:
    """Index of the smallest box containing the point, else -1."""
    hit = -1
    size = float("inf")
    for i, b in enumerate(boxes):
        if x < b["x"] - pad or x > b["x"] + b["w"] + pad or y < b["y"] - pad or y > b["y"] + b["h"] + pad:
            continue
        if b["w"] * b["h"] < size:
            size = b["w"] * b["h"]
            hit = i
    return hit


def overlap(a: dict, b: dict) -> int:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return w * h if w > 0 and h > 0 else 0


def tally(items: list[dict], states: list[str]) -> dict:
    n = {"all": len(items)}
    for s in states:
        n[s] = 0
    for e in items:
        n[e["state"]] += 1
    return n
