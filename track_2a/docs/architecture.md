# Architecture

Docket turns the PDF of a parliamentary document into an affair record with the place every value came from,
keeps the records in a store, and lets a person check what the machine was not sure about. The whole chain
is Python; the browser app is Angular, built once with Node and served as static files; the language model
is reached over the network and is never trusted with a value that does not stand on the page.

## The chain, one document at a time

```
PDF ──pdftoppm──▶ page images ──▶ geometry ──▶ elements ──▶ blocks ──▶ fields ──▶ key ──▶ affair ──▶ store
                                   │             ▲            │           │
                                   │   text layer (pdftotext) │           │
                                   │   or reading (model)     │           │
                                   └─────────────────────────┘           │
                                                  sorting (model) ───────┘  asking (model)
```

| Step | Module | What it does | Model |
|---|---|---|---|
| Pages | `page/render.py` | renders every page at 300 dpi with poppler; the pixel sizes of everything below refer to these images | no |
| Geometry | `page/` (`mask`, `lines`, `slicer`, `joiner`, `marks`, `elements`, `styler`, `analyze`) | finds ink, rules, areas, marks and cells, joins glyphs to lines and lines to objects, types and styles them; numpy holds the pixel fields, every rule is own code | no |
| Text | `text/layer.py` | puts the words of the PDF's text layer into the elements that hold them; a page with fewer than 20 words or a large image is a scan | no |
| Reading | `read/reader.py`, `fluffy.py` | reads the elements of a scan with the model, in strips of three with red ids, then long blocks singly; every reading is held against the shape of the ink and marked for a person where it does not match | yes |
| Blocks | `document/bridge.py`, `fluffy.py` | elements become JATS blocks: sections by size and known names, paragraphs by joined lines, tables, lists, labelled lists, images, signature blocks; everything else is the rest | no |
| Sorting | `document/sorter.py`, `document/picture.py` | the rest of the first pages goes to the model as a text image, six elements per call, to be named one of eight kinds | yes |
| Fields | `fields/` (`fields`, `filler`, `placer`) | the fields file asks the model six questions per call over the first pages and over the whole document; code takes an answer only with a place: literal in a block, derived from the named block, or cited with a word in it; composed values and cited ones carry `approve` | yes |
| Kind | `document/kind.py` | the document's role in the affair from the words of its first page, by the list in `data/knowledge/kinds.json` | no |
| Key | `affair/identity.py` | the affair number, normalised; checked against the number forms of the parliament, searched on the page by form, or a weak key from place, date and title | no |
| Affair | `affair/merge.py`, `affair/types.py`, `affair/validator.py` | the documents of one key become one affair; the harmonised type comes from the label through the table of the export; the record is checked against the contract by an own validator | no |
| Store | `store/` (`files`, `postgres`, `review`, `rules`) | the affair with its documents, the fields reports, the decisions; reviews survive a new run over the same document | no |

The command line runs the chain (`cli.py`, `runner.py`); the server runs the same function from its queue
(`jobs.py`). `pipeline.py` holds the pieces every caller shares.

## The record

The contract (`data/schema/docket.json`, version 0.8) is OpenParlData's affair record with JATS keys added:
blocks with their page and pixel box, `source` beside every value that has a place of its own, `sources` at
the root for the values that have none, `review` wherever a person decided. `data/schema/DEFINITION.md` says
what every key means. The example record is a real run.

Enumerations are English in the record and translated on the screen: `how` is literal, derived, cited or
composed; a decision is confirmed, changed or rejected; a document kind is one of the seven in the knowledge.

## The knowledge

`data/knowledge/` holds what earlier documents and OpenParlData's export taught, all derived, none written by
hand into the code: the section names with their counts, the harmonised type per label with its share, the
number forms per parliament, the names of the parliaments, the kinds of documents with their words.
`tools/knowledge.py` rebuilds the three tables from the export and the API. The values the model placed are
kept per run (`values.json`) for a person to look at and are never offered to the model: measured, that
brought more values that are not on the page.

## The store and the review

A store holds affairs by key, each with its record and its documents, the fields reports of the documents,
the decisions and the rules. Files under `storage/store/` serve a single machine and the tests; Postgres
(`DATABASE_URL`) serves the container, with the records as JSONB and the decisions as rows. Page images stay
on disk in both.

A decision is written at the value's source: confirmed; changed, with the old value kept in `before`;
rejected, with the value left in place and marked, so an export can leave it out. `approve` stays as the
machine's signal; open means approve without review. A new run over a document that is already stored keeps
every review, matched by document name, block and path.

The same change three times on the same field becomes a rule (`store/rules.py`): prefix or suffix off or on,
a letter read for a digit, the spelling. An active rule changes every fitting value of that field in the
store, each with a review that names the rule, so every application can be seen and taken back; a person can
switch a rule off and on, and what people confirm or withdraw is counted on it.

## The server and the app

`server.py` is the standard library's HTTP server with a small router; `api.py` is what it answers with:
the affairs with every value that has a place, the decisions, the rules, the runs of the admin, and for every
open value the count of documents with the same pattern. One lock per affair guards the decisions; the
contract is checked before anything is saved. The admin's runs (`jobs.py`) take an uploaded PDF or a document
of OpenParlData by its id, run one after the other, and stay on disk under `storage/runs/`. An optional token
guards the admin.

The app (`app/`, Angular with Angular Material) is built into `src/docket/app/` and served as static files.
It shows the affairs as result cards, one affair with its page and every block framed, red where a person has
to look, the values beside it with the three decisions, every decision taken, and the admin with the runs,
the rules and the upload. Node is needed for the build only: locally through `make app`, in the container in
the first stage of the Docker image.

## Measuring

`make test` runs without a model and holds the chain against references that existed before any run: the
text layer of the PDFs for the geometry and the text, the affairs of the API for the fields and the identity,
a reading by hand for the kinds, and the contract for every record; it also runs the server, the decisions,
the rules and the admin's queue on a file store. `make bench` runs the whole chain with the model over the
eight shipped documents, about sixty calls, under five minutes, and keeps the raw exchange of every call.
`docs/evidence.md` holds every number behind a decision, `results/` the committed runs.

## Running it

`make run` starts Postgres and the server in Docker; the app is at port 8080. The server needs one CPU: the
geometry takes about three seconds per page, the model is called over the network one call at a time with a
pause, so a digital document of two pages takes about half a minute and a scanned page about one minute more
for the reading. Memory peaked at 0.6 GB with one document in flight (the run of 8 October over the eight
shipped documents). The model calls are the budget: four to six per document for the fields, one for the
sorting of the first pages, thirteen for a scanned page.
