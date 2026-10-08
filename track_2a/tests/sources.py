"""Error sources: every difference between the object layer and the reference gets a cause, per set and per
document. Two levels: blocks against objects, lines against text lines (strips). No model call.

    python3 tests/sources.py --got=<analyzed dir> [--out=<file.md>] <reference dir> [<reference dir> ...]

The reference dir holds <name>.json per page (words and images from the PDF, tools/reference.py); the analyzed
dir holds <name>.json as written by `docket analyze`.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from compare import compare  # noqa: E402

# an object from this share of the page on is background or frame, not a neighbour
PAGE_SIZED = 0.25

CAUSES = [
    "single", "page-sized", "merged below/above", "merged beside", "cut between lines", "number cut off",
    "cut at wide gap", "as line", "missed",
]
MARKER = re.compile(r"^(\(?\d{1,3}[.)]?|\(?[a-zA-Z][.)]|[IVXivx]{1,5}[.)]|[^\w\s]{1,2})$")


def marker(text: str) -> bool:
    """Only a number, a letter with a bracket or a bullet before the cut?"""
    parts = text.split(" ¦ ")
    return len(parts) == 2 and bool(MARKER.match(parts[0].strip()))


def causes(res: dict, got: dict, page: int) -> dict:
    """Cause per block from the result of compare()."""
    n = {c: 0 for c in CAUSES}
    in_object: dict[int, list] = {}
    for i, b in res["blocks"].items():
        for o in b["objs"]:
            in_object.setdefault(o, []).append(i)
    for i, b in res["blocks"].items():
        cause = b["state"]
        if cause == "merged":
            o = got["objects"][b["objs"][0]]
            cause = "merged beside"
            if o["w"] * o["h"] >= PAGE_SIZED * page:
                cause = "page-sized"
            else:
                for j in in_object[b["objs"][0]]:
                    c = res["blocks"][j]
                    if j != i and min(b["x"] + b["w"], c["x"] + c["w"]) > max(b["x"], c["x"]):
                        cause = "merged below/above"
        elif cause == "cut inside a line":
            cut = [line for line in b["lines"] if res["lines"][line]["state"] == "cut"]
            plain = [line for line in cut if not marker(res["lines"][line]["t"])]
            cause = "cut at wide gap" if plain else "number cut off"
        elif cause == "line":
            cause = "as line"
        n[cause] += 1
    return n


def pct(v: int, total: int) -> str:
    return f"{v} ({100 * v / total:.1f} %)" if total else str(v)


def row(label: str, n: dict) -> str:
    total = sum(n.values())
    return f"| {label} | {total} |" + "".join(f" {pct(n.get(c, 0), total)} |" for c in CAUSES) + "\n"


def add(total: dict, n: dict) -> dict:
    for k, v in n.items():
        total[k] = total.get(k, 0) + v
    return total


def main(argv: list[str]) -> int:
    ref_dirs = [Path(a) for a in argv if not a.startswith("--")]
    got_dir = next((Path(a[6:]) for a in argv if a.startswith("--got=")), None)
    out_file = next((Path(a[6:]) for a in argv if a.startswith("--out=")), None)
    if not ref_dirs or got_dir is None:
        print("usage: python3 tests/sources.py --got=<analyzed dir> [--out=<file.md>] <reference dir> ...")
        return 1

    head = "| all | " + " | ".join(CAUSES) + " |\n|---|---:|" + "---:|" * len(CAUSES) + "\n"
    md = (
        "# Error sources\n\nProduced by `tests/sources.py`. Reference is the text layer of the PDFs (words, lines, "
        "blocks by poppler). Every block and line of the reference stands in exactly one column.\n"
    )
    by_doc: dict[str, dict] = {}
    words = {"all": 0, "object": 0, "line": 0, "missed": 0}
    levels: dict[str, dict] = {"blocks": {}, "lines": {}}
    files = []
    for d in ref_dirs:
        if d.is_dir():
            files.extend(sorted(f for f in d.iterdir() if f.suffix == ".json" and f.name != "document.json"))
    for file in files:
        name = file.stem
        got_file = got_dir / f"{name}.json"
        if not got_file.is_file():
            continue
        got = json.loads(got_file.read_text(encoding="utf-8"))
        ref = json.loads(file.read_text(encoding="utf-8"))
        page = ref["width"] * ref["height"]
        doc = file.parent.name
        if not ref["words"]:
            continue
        res = compare(ref, got)
        b = causes(res, got, page)
        levels["blocks"] = add(levels["blocks"], b)
        entry = by_doc.setdefault(doc, {"blocks": {}, "lines": {}})
        entry["blocks"] = add(entry["blocks"], b)
        add(words, res["count"]["words"])

        # lines against text lines: the same count, block = line, object = strip
        if got.get("strips"):
            flat = dict(ref, words=[dict(w, block=w["line"]) for w in ref["words"]])
            thin = dict(got, objects=got["strips"])
            lines = causes(compare(flat, thin), thin, page)
            levels["lines"] = add(levels["lines"], lines)
            entry["lines"] = add(entry["lines"], lines)

    titles = (
        ("blocks", "Blocks of the reference against objects"),
        ("lines", "Lines of the reference against text lines (strips)"),
    )
    for level, title in titles:
        md += f"\n## {title}\n\n| Set {head}" + row("**all**", levels[level])
        docs = [(doc, n) for doc, n in by_doc.items() if n[level]]
        docs.sort(key=lambda item: item[1][level].get("single", 0) / max(1, sum(item[1][level].values())))
        md += f"\n### Per document (worst first)\n\n| Document {head}"
        for doc, n in docs:
            md += row(doc, n[level])
    md += ("\n## Words\n\n| all | in an object | as line | in no object |\n|---:|---:|---:|---:|\n"
           f"| {words['all']} | {pct(words['object'], words['all'])} | {words['line']} | {words['missed']} |\n")
    if out_file:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(md, encoding="utf-8")
    print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
