"""Reading with the model, measured against the text layer: the pages given are read as if they had no text
layer, and every reading is held against the text the PDF carries for the same element.

    python3 tests/read.py [--out=<file.md>] <document dir> [<document dir> ...]

Needs API_KEY in .env. One strip call per three elements plus one call per multi-line element; the raw exchange
lands in storage/bench/read/. Judgements: identical, near (edit distance at most 10 % of the reference), other,
empty; character errors over all elements with a reference.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.config import load_config  # noqa: E402
from docket.fluffy import levenshtein  # noqa: E402
from docket.model.client import Client  # noqa: E402
from docket.page.analyze import analyze_page  # noqa: E402
from docket.page.render import render_pdf  # noqa: E402
from docket.read.reader import read_page  # noqa: E402
from docket.text.layer import fill_text_layer  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith("--")]
    out_file = next((Path(a[6:]) for a in argv if a.startswith("--out=")), None)
    client = Client(load_config())
    if not client.config.api_key:
        print("no API_KEY in .env")
        return 1
    rows = []
    started = time.time()
    for d in dirs:
        pdf = next(d.glob("*.pdf"))
        with tempfile.TemporaryDirectory() as tmp:
            for n, image in render_pdf(pdf, tmp, pdf.stem):
                if n > 1:
                    break
                page, result = analyze_page(image)
                if not fill_text_layer(pdf, n, result):
                    continue
                elements = result["elements"]
                reference = {i: e["content"] for i, e in enumerate(elements) if e["type"] == "text" and e["content"]}
                # read as if there were no text layer: the text elements back to unknown
                for i in reference:
                    result["elements"][i]["type"] = "unknown"
                    result["elements"][i]["content"] = ""
                before = client.calls
                read_page(client, page.rgb, page.gray, result, log=ROOT / "storage" / "bench" / "read")
                calls = client.calls - before
                for i, want in reference.items():
                    got = result["elements"][i].get("content", "")
                    rows.append(_judge(f"{pdf.stem}-s{n}", want, got, result["elements"][i].get("approve", False)))
                print(f"{pdf.stem}-s{n}: {len(reference)} elements, {calls} calls")
                if client.halted:
                    print(f"halted after HTTP {client.halted}")
                    break
    md = _report(rows, client.calls, time.time() - started)
    if out_file:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(md, encoding="utf-8")
    print(md)
    return 0


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("ß", "ss")).strip().lower()


def _judge(page: str, want: str, got: str, approve: bool) -> dict:
    a, b = _norm(want), _norm(got)
    distance = levenshtein(a, b)
    if not b:
        state = "empty"
    elif a == b:
        state = "identical"
    elif distance <= 0.1 * len(a):
        state = "near"
    else:
        state = "other"
    return {
        "page": page,
        "state": state,
        "distance": distance,
        "length": len(a),
        "approve": approve,
        "want": want,
        "got": got,
    }


def _report(rows: list[dict], calls: int, seconds: float) -> str:
    count = {s: sum(1 for r in rows if r["state"] == s) for s in ("identical", "near", "other", "empty")}
    chars = sum(r["length"] for r in rows)
    errors = sum(r["distance"] for r in rows)
    flagged = {s: sum(1 for r in rows if r["state"] == s and r["approve"]) for s in count}
    md = (
        f"# Reading against the text layer\n\nProduced by `tests/read.py`: {len(rows)} elements, {calls} calls, "
        f"{seconds / 60:.1f} minutes. Reading in strips of three, then multi-line blocks alone.\n\n"
        "| identical | near | other | empty | character errors |\n|---:|---:|---:|---:|---:|\n"
        f"| {count['identical']} | {count['near']} | {count['other']} | {count['empty']} "
        f"| {100 * errors / max(1, chars):.1f} % |\n\n"
    )
    flags = ", ".join(f"{s} {flagged[s]} of {count[s]}" for s in count)
    md += f"Flagged by the image check (approve): {flags}.\n\n"
    md += "## Not identical\n\n| page | state | reference | reading |\n|---|---|---|---|\n"
    for r in rows:
        if r["state"] != "identical":
            want = r["want"][:60].replace("|", "/")
            got = r["got"][:60].replace("|", "/")
            md += f"| {r['page']} | {r['state']}{' !' if r['approve'] else ''} | {want} | {got} |\n"
    return md


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
