"""The page as a text image: what stands side by side on paper stands side by side in the text, what stands
beneath each other beneath each other. The model gets the page as a whole to read, without coordinates."""

from __future__ import annotations

from docket.document.bridge import base_size, pixels_per_point

# width of the text image in characters
COLS = 110

# placeholders for what is not text; smaller than this many font sizes it is a speck and stays away
MARKS = {"image": "[Bild]", "unknown": "[Bild]", "checkbox": "[ ]", "radio": "( )", "input": "____"}
SPECK = 1.5


def text_image(page: dict, marks: dict[int, str] | None = None) -> str:
    """The text image of a page; `marks` prefixes the content of the elements at those indexes ("[1] ...")."""
    size = base_size(page["elements"]) * pixels_per_point(page)
    cw = page["width"] / COLS
    items = []
    for i, e in enumerate(page["elements"]):
        text = e.get("content") or ""
        if not text:
            big = e["type"] not in ("image", "unknown") or min(e["width"], e["height"]) >= SPECK * size
            text = MARKS.get(e["type"], "") if big else ""
        if marks and i in marks and text:
            text = marks[i] + " " + text
        if text:
            width = max(12, int(round(e["width"] / cw)))
            items.append({"x": e["x"], "y": e["y"], "end": e["y"] + e["height"], "lines": _wrap(text, width)})
    items.sort(key=lambda it: it["y"])

    # a band: everything that overlaps in height stands side by side
    out: list[str] = []
    band: list[dict] = []
    end = 0
    for it in [*items, None]:
        if it is not None and band and it["y"] < end - 0.3 * size:
            band.append(it)
            end = max(end, it["end"])
            continue
        if band:
            band.sort(key=lambda b: b["x"])
            for r in range(max(len(b["lines"]) for b in band)):
                line = ""
                for b in band:
                    if r >= len(b["lines"]):
                        continue
                    col = max(int(round(b["x"] / cw)), 0 if line == "" else len(line) + 2)
                    line = line + " " * max(0, col - len(line)) + b["lines"][r]
                out.append(line.rstrip())
            # an empty line where there is space on the paper
            if it is not None and it["y"] - end > size:
                out.append("")
        if it is not None:
            band = [it]
            end = it["end"]
    return "\n".join(out)


def _wrap(text: str, width: int) -> list[str]:
    """Line breaks at word boundaries."""
    lines = []
    line = ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = word if not line else line + " " + word
    lines.append(line)
    return lines
