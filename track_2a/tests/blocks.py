"""The blocks of the shipped documents against the contract, without a model: the bridge runs over the analyzed
pages of every document, the rest becomes paragraphs, and the record must validate.

    python3 tests/blocks.py --pages=<analyzed dir> --out=<dir> <document dir> [<document dir> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from docket.config import load_config  # noqa: E402
from docket.pipeline import build_document, load_contract, load_knowledge  # noqa: E402


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith("--")]
    pages_dir = next((Path(a[8:]) for a in argv if a.startswith("--pages=")), None)
    out_dir = next((Path(a[6:]) for a in argv if a.startswith("--out=")), None)
    if not dirs or pages_dir is None:
        print("usage: python3 tests/blocks.py --pages=<analyzed dir> [--out=<dir>] <document dir> ...")
        return 1
    config = load_config()
    contract = load_contract(config)
    knowledge = load_knowledge(config)
    failed = False
    total: dict[str, int] = {}
    rest_total = 0
    documents = 0
    for d in dirs:
        pdf = next(d.glob("*.pdf"), None) if d.is_dir() else None
        if pdf is None:
            continue
        documents += 1
        pages = []
        n = 1
        while (pages_dir / f"{pdf.stem}-s{n}.json").is_file():
            pages.append(json.loads((pages_dir / f"{pdf.stem}-s{n}.json").read_text(encoding="utf-8")))
            n += 1
        if not pages:
            print(f"FAIL {pdf.stem}: no analyzed pages in {pages_dir}")
            failed = True
            continue
        record, report = build_document(pdf.stem, pages, knowledge)
        errors = contract.check(record)
        if out_dir is not None:
            out_dir.mkdir(parents=True, exist_ok=True)
            text = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
            (out_dir / f"{pdf.stem}.json").write_text(text, encoding="utf-8")
        for k, v in report["blocks"].items():
            total[k] = total.get(k, 0) + v
        rest_total += report["rest"]
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(report["blocks"].items(), key=lambda item: -item[1]))
        if errors:
            failed = True
            print(f"FAIL {pdf.stem}: {len(errors)} violations, first: {errors[0]}")
        else:
            blocks = sum(report["blocks"].values())
            print(f"ok   {pdf.stem}: {len(pages)} pages, {blocks} blocks ({kinds}), valid against the contract")
    kinds = ", ".join(f"{k} {v}" for k, v in sorted(total.items(), key=lambda item: -item[1]))
    print(f"{documents} documents: {sum(total.values())} blocks ({kinds}); without the model leftovers are paragraphs")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
