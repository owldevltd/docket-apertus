# Documents

The documents the demo and the tests run on. Each folder holds the PDF, a `document.json` with name, body,
language, origin and, where known, the affair it belongs to at OpenParlData, and one JSON per page with the
reference the tests measure against.

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
