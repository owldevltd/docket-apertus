"""The whole run for one document: pages, text, blocks, and the affair record it becomes."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from docket.affair.identity import Identity, make_key
from docket.affair.merge import SCHEMA
from docket.affair.validator import Contract
from docket.config import Config
from docket.document.bridge import Knowledge, add_blocks, build_blocks
from docket.document.sorter import sort_rest
from docket.fields.fields import Fields, load_fields
from docket.fields.filler import fill_document
from docket.model.client import Client
from docket.page.analyze import analyze_page
from docket.page.painter import draw_elements
from docket.page.raster import write_png
from docket.page.render import render_pdf
from docket.read.reader import read_page
from docket.text.layer import fill_text_layer

# the first pages: page 1, or 1 and 2 when page 1 has less than this share of the text of page 2 (a cover sheet)
COVER = 0.1


def load_knowledge(config: Config) -> Knowledge:
    """The section names, and what tools/knowledge.py built from the export where it lies."""
    folder = config.data_dir / "knowledge"
    sections = json.loads((folder / "sections.json").read_text(encoding="utf-8"))["sections"]

    def part(name: str, key: str) -> dict:
        path = folder / name
        return json.loads(path.read_text(encoding="utf-8"))[key] if path.is_file() else {}

    types = part("types.json", "types")
    forms = part("number-forms.json", "forms")
    bodies = part("bodies.json", "bodies")
    return Knowledge(sections, types=types, forms=forms, bodies=bodies)


def identify(report: dict[str, dict], fields: Fields, pages: list[dict], name: str, knowledge: Knowledge) -> Identity:
    """The key of a document from its placed values: per role (number, place, parliament, date, title) the
    first value with a place; the text of the first page for the search by form."""
    values: dict[str, str] = {}
    for role, field_name in fields.by_role().items():
        items = [i for i in report.get(field_name, {}).get("items", []) if i.get("block") is not None]
        if items:
            values[role] = items[0]["value"]
    text = " ".join(e.get("content") or "" for e in pages[0]["elements"]) if pages else ""
    return make_key(values, name, text, knowledge.forms, knowledge.bodies)


def load_contract(config: Config) -> Contract:
    return Contract.load(config.data_dir / "schema" / "docket.json")


def load_field_file(config: Config, contract: Contract) -> Fields:
    return load_fields(config.data_dir / "schema" / "fields.json", contract)


def process_pages(pdf: Path, out: Path, client: Client | None, keep: dict | None = None) -> list[dict]:
    """Every page of the PDF: geometry, text layer, reading with the model where there is none. Writes the page
    files into `out` and returns the pages in order; `keep` receives the images of the first two pages by
    page number, for the control image of the fields."""
    pages = []
    with tempfile.TemporaryDirectory() as tmp:
        for n, image in render_pdf(pdf, tmp, pdf.stem):
            name = f"{pdf.stem}-s{n}"
            page, result = analyze_page(image)
            result["textLayer"] = fill_text_layer(pdf, n, result)
            if client is not None and not result["textLayer"]:
                read_page(client, page.rgb, page.gray, result, log=out / f"{name}.read")
            (out / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            draw_elements(page.rgb, out / f"{name}-elements.png", result["elements"])
            write_png(out / f"{name}.png", page.rgb)
            if keep is not None and n <= 2:
                keep[n] = page.rgb
            pages.append(result)
    return pages


def fill_fields(record: dict, pages: list[dict], fields: Fields, contract: Contract, client: Client | None,
                knowledge: Knowledge, log: Path | None = None) -> tuple[dict, dict]:
    """The fields over the document into the record; without a client the record stays as it is."""
    return fill_document(record, pages, first_pages(pages), fields, contract, client, knowledge, log)


def first_pages(pages: list[dict]) -> list[int]:
    """Page 1, or 1 and 2 when page 1 is a cover sheet with little text."""
    if len(pages) < 2:
        return [1]
    chars = [sum(len(e.get("content") or "") for e in p["elements"]) for p in pages[:2]]
    return [1, 2] if chars[0] < COVER * chars[1] else [1]


def build_document(
    name: str, pages: list[dict], knowledge: Knowledge, client: Client | None = None, log: Path | None = None
) -> tuple[dict, dict]:
    """The affair record with this one document: its blocks from the bridge, the rest sorted by the model
    (without a client, as paragraphs). Returns the record and a report of the run."""
    body, rest = build_blocks(pages, knowledge)
    kinds, count = sort_rest(client, pages, rest, first_pages(pages), log)
    body, left = add_blocks(body, rest, kinds, knowledge)
    record = {
        "schema": SCHEMA,
        "docs": {"data": [{"id": 1, "name": name, "page-count": len(pages), "body": body}]},
    }
    blocks = _count(body)
    return record, {"blocks": blocks, "rest": len(left), "sorted": count}


def _count(body: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for b in body:
        out[b["type"]] = out.get(b["type"], 0) + 1
        for c in b.get("content", []) if b["type"] == "sec" else []:
            out[c["type"]] = out.get(c["type"], 0) + 1
    return out
