"""The text layer in the elements, without a model: on every shipped page with a text layer the words of the
reference must lie in elements that carry text, and a page without a layer must be seen as such.

    python3 tests/text.py --got=<analyzed dir> <reference dir> [<reference dir> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main(argv: list[str]) -> int:
    ref_dirs = [Path(a) for a in argv if not a.startswith("--")]
    got_dir = next((Path(a[6:]) for a in argv if a.startswith("--got=")), None)
    if not ref_dirs or got_dir is None:
        print("usage: python3 tests/text.py --got=<analyzed dir> <reference dir> ...")
        return 1
    failed = False
    total_words = 0
    total_in = 0
    pages = 0
    for d in ref_dirs:
        if not d.is_dir():
            continue
        for file in sorted(f for f in d.iterdir() if f.suffix == ".json" and f.name != "document.json"):
            got_file = got_dir / file.name
            if not got_file.is_file():
                continue
            ref = json.loads(file.read_text(encoding="utf-8"))
            got = json.loads(got_file.read_text(encoding="utf-8"))
            has_layer = bool(ref["words"])
            if got.get("textLayer") != has_layer:
                expected = "expected" if has_layer else "not expected"
                print(f"FAIL {file.stem}: text layer {expected}, got {got.get('textLayer')}")
                failed = True
                continue
            if not has_layer:
                print(f"ok   {file.stem}: no text layer, left to the reading step")
                continue
            texts = [e for e in got["elements"] if e["type"] == "text" and e.get("content")]
            inside = 0
            for w in ref["words"]:
                cx = w["x"] + w["w"] / 2
                cy = w["y"] + w["h"] / 2
                if any(e["x"] <= cx <= e["x"] + e["width"] and e["y"] <= cy <= e["y"] + e["height"] for e in texts):
                    inside += 1
            with_font = sum(1 for e in texts if e.get("font"))
            ocr = sum(1 for e in texts if e.get("isOCR"))
            share = inside / len(ref["words"])
            pages += 1
            total_words += len(ref["words"])
            total_in += inside
            state = "ok  " if share >= 0.9 else "FAIL"
            failed = failed or share < 0.9
            print(
                f"{state} {file.stem}: {inside} of {len(ref['words'])} words in a text element ({100 * share:.1f} %), "
                f"{len(texts)} text elements, {with_font} with a font from the PDF, {ocr} from OCR"
            )
    share_all = 100 * total_in / max(1, total_words)
    print(f"{pages} pages with a text layer: {total_in} of {total_words} words in a text element ({share_all:.1f} %)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
