# Documents

The documents the demo and the tests run on. Each folder holds the PDF, a `document.json` with name, body,
language, origin and, where known, the affair it belongs to at OpenParlData, one JSON per page with the
reference the tests measure against, and a stored run with the affair it became.

| Folder | Body | Language | Pages | Text layer | What it is |
|---|---|---|---:|---|---|
| `nidau-m185/` | Nidau, municipality (BE) | de | 2 | yes | the kickoff example: a motion with cover sheet, request and reasoning |
| `wettingen-115631/` | Wettingen, city (AG) | de | 2 | yes | a motion, running text under a two-line header |
| `basel-137584/` | Basel-Stadt, canton | de | 1 | yes | a request for a cantonal initiative, dense text |
| `zuerich-219587/` | Zürich, canton | de | 1 | yes | a parliamentary initiative, cantonal letterhead |
| `aargau-scan/` | Aargau, canton | de | 1 | no | the Aargau request rendered and saved without a text layer: the path for scans, on a page whose text is known |
| `neuchatel-grand-conseil/` | Neuchâtel, canton | fr | 1 | yes | a French document of the Grand Conseil, from the file server |
| `ayent-6082/` | Ayent, municipality (VS) | fr | 4 | yes | from one of the eight bodies that hold documents but no affairs |
| `lugano-5192/` | Lugano, city (TI) | it | 3 | yes | an Italian document of the city council, from the file server |

The documents are publications of the parliaments, taken from OpenParlData's API and file server
(files.openparldata.ch, data under CC BY 4.0, "Source: OpenParlData.ch"); they remain the property of their
publishers and are included as test material. The full set used for the measurements, 64 documents with 482
pages, is listed in the evidence document and not redistributed here.

## The reference JSON

Produced once from the PDF with poppler (`make reference`, `tools/reference.py`): `pdftotext -bbox-layout` for
words, lines and blocks, `pdftohtml -xml` for the raster images placed on the page, and the page rendered at
300 dpi for the ink box of every word. poppler is a preparation tool and the renderer of pages; the geometry
itself needs nothing but numpy.

```
source   path of the PDF
page     page number
kind     "document", or "scan" when the page has no text layer
lang     language of the document
dpi      300
width, height   pixels of the page image
words[]  { x, y, w, h, t, line, block, ink }   t = the word, line/block = poppler's grouping, ink = box of its ink
images[] { x, y, w, h, ink }                    raster images on the page
```

Coordinates are pixels at 300 dpi. A page without a text layer has no words; the tests skip it and the
reading step handles it.

## The stored run

`run.json` is what a run with the model left for the document on 10 October 2026: the blocks (`body`), the
number of pages, the identity of the document (`identity`), the kind the run took it for (`kind`) and, for
every field of the definition, the model's
answer with its state and the values taken from it (`fields`); the raw exchange of the calls is left out. The
fields were named in German when the run was made; they stand here under the English names the fields file
has since, the answers untouched. The identity was formed anew on 11 October 2026 from the same answers and
the first page, when the key came to name the parliament; the parliament is told with the document, as
`document.json` names it.
The place of the summary was told anew on the same day, when a summary came to keep the block the model
names; the summaries of the three documents that are not German were asked again, in their language.
`affair.json` is the affair the code makes of that run, as a run writes it. `tests/baseline.py` forms it again
without a model and compares the two character by character, so a change to the core that moves a value or
a place shows at once. After a change that is meant, `python3 tests/baseline.py --write data/documents/*`
replaces the stored affairs.
