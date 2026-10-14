# Docket

**From the PDFs of Swiss parliaments to one structure for parliamentary affairs, with Apertus.**
Hack Apertus 2026 · Track 2A · OpenParlData challenge.

Docket turns the PDF of a parliamentary document – born digital or scanned, German, French or Italian, from a canton
or a municipality – into an affair record, and every value in it carries the place on the page it came from. Code
finds where things stand on the page without a model; Apertus reads what it is shown and answers the questions of a
fields file; code then decides what counts: a value is taken only where it stands on the page. Where the model
guesses or a reading does not fit the image, Docket marks the value for a person, and what a person corrects
becomes a rule for every value of the same kind.

## Results

Measured on 300 documents of 62 parliaments, in a shuffled order (`results/three-hundred/`):

- **209 of 299 documents run through without a single mark for a person** (69.9 %, 95 % interval 64.5–74.8 %), steady
  from 50 documents on, similar in German (71.6 %), French (71.1 %) and Italian (66.7 %).
- Against a reference of 60 documents (20 per language, cantons and municipalities, read value by value with page and
  place; 60 values drawn at random checked by hand, all hold): 940 of 1 200 fields as in the reference (78 %). On the
  other 239 of the 300, read the same way, 3 512 of 4 780 (73.5 %, 95 % interval 72.1–74.8 %), on the 179 never seen
  during development 73.3 % (`results/reference/`).
- The model answered 5 144 fields with 6 500 values: 4 650 stand on the page literally or derived from the block it
  named, 211 only at the named block (marked for a person), 185 are worded by the model, and 1 454 have no place on the
  page and are not taken.
- A question across the parliaments: how many members back an affair? The documents name more than one person in 153 of
  299; per parliament the backing differs in kind, from one person in most municipalities to 33 in the median in
  Graubünden.

The technical report (`technical_report.md`) gives the design and the evaluation; `docs/appendix.md` the tests the
design rests on.

## What you need

- **Runtime:** Docker with Compose 2.24 or newer (Docker Desktop, or Docker Engine with the compose plugin). Nothing
  else: the image brings Python and poppler, and Postgres runs as a second container. The first build needs the network.
- **Hardware:** no GPU. Tested on a laptop with four cores (eight threads) and 8 GB of memory (6.9 GB usable); the
  pipeline computes on one core. Port 8080 must be free.
- **API key:** a key for an OpenAI-compatible endpoint that serves Apertus v1.5 8B. The defaults point at the CSCS
  endpoint of Hack Apertus; `LLM_BASE_URL` and `LLM_NAME` point it at another one.
- **Model weights:** none to download; the model is reached over the endpoint.

## Run it

From the folder `track_2a/`:

1. `cp .env.example .env` and put your key after `LLM_API_KEY=`. If other people can reach the machine, set
   `ADMIN_PASSWORD` as well (and `ADMIN_USER`, default `admin`); without a password the administration is open.
2. `make run` (on Linux possibly `sudo make run`). The first build takes a few minutes; then Postgres and the server
   run in Docker, and the log stays in the terminal.
3. Open **http://localhost:8080/en/** – the app in English; `/de/`, `/fr/` and `/it/` are the same app in German,
   French and Italian. A clean checkout starts with an empty store, so the list is empty.
4. Take a PDF of a Swiss parliament: any motion, postulate, interpellation or report works, born digital or scanned.
   The kickoff document of the challenge, a two-page motion of the municipality of Nidau, is at
   https://files.openparldata.ch/doc/743/3a1a2c1505729311da61b5e1afbb5b25b01803147d0f2aad6061f4f6c8e0a301.
5. Open the administration, **http://localhost:8080/en/admin** (sign in if you set a password), go to **Process**,
   choose the PDF, leave the parliament at *read from the document* and *with the model* ticked, and press
   **Upload**. The run shows under **Runs**; a short document with a text layer takes about half a minute, a scan
   longer (28 calls to the model in the median instead of 6).
6. The affair is now in the visitor's list at `/en/`, with its persons, groups and meetings. Under **Review** in the
   administration every value stands at its place on the page; a value marked for a person waits there for a yes, a
   no or a correction.
7. The record as JSON: **http://localhost:8080/api/records** lists the affairs, `/api/records/<key>` gives one whole.

`Ctrl+C` stops the app; `docker compose down` removes the containers and keeps the store, `docker compose down -v`
empties it.

### From the command line

While `make run` is up, a PDF laid into `track_2a/storage/` goes through the same chain in the container:

```
docker compose exec docket python3 -m docket affairs --model --out storage/out storage/motion.pdf
```

`storage/out/affairs/<key>.json` is the affair record; `storage/out/motion-fields.json` says per field what became of
the model's answer; `storage/out/motion-s1-check.png` shows the first page with the blocks that hold a value (green:
found by code, red: a person has to look). The affair goes into the store as well and shows in the app.

## Input and output

- **In:** a PDF of a parliamentary document, with or without a text layer, in German, French or Italian; optionally
  the parliament it comes from.
- **Out:** the affair record in JSON, checked against the contract `data/schema/docket.json` (JSON Schema, versioned
  in `data/schema/DEFINITION.md`): OpenParlData's affair record with its field names, plus keys from JATS for what it
  does not hold. Every value carries its `source`: the document, the block on the page, and how it was found.

A value as it lands in the record (values made up): the addressee printed on the page, found literally in block
`b11` of document 1, and a co-signer the model named a block for without the name standing there – marked for a
person:

```json
{
  "custom-meta": [
    { "meta-name": "addressee", "meta-value": "Gemeinderat",
      "source": { "doc": 1, "block": "b11", "how": "literal" } }
  ],
  "contributors": { "data": [
    { "fullname": "Hans Muster", "role": { "de": "Mitunterzeichner/in" },
      "source": { "doc": 1, "block": "b9", "how": "cited", "approve": true } }
  ] }
}
```

`how` is `literal` (the value stands in the block; a day in any spelling of the same day), `derived` (every word of
it stands in the block, put together differently), `cited` (only the block the model named; marked) or `composed` (a
text the model wrote, such as the summary; marked where it leaves its document).
The whole record of the kickoff document, as the pipeline built it, is `data/schema/example-nidau-m185.json`.

## How it works

1. **First recognise, then read.** Every page goes as an image through the same geometry, without a model: lines,
   areas, ticks, cells and text lines become elements, the elements become blocks named as in JATS. The text comes
   from the PDF's text layer; where there is none, Apertus reads the elements, and every reading is checked against
   the image.
2. **A value counts only with its place.** Apertus answers the fields file, up to six questions a call; every answer
   has to find its place on the page. Rules in code decide afterwards: a day only where it stands, a value that is
   another field's value is left out, co-signers only from the submission itself.
3. **A model that grows.** The record is OpenParlData's affair record unchanged, plus keys from JATS for what it does
   not hold; a JSON Schema contract checks every record. The store keeps one row per value; the record is laid from
   the rows, so a field added later is asked only of the documents that lack it, and another contract – another
   standard – gets the same affairs without reading again.
4. **It learns.** Two corrections of the same kind propose a rule; a person's yes applies it to every fitting value.
   A second opinion on where a field stands is learnt from the store; names are looked up in the register of persons
   of their parliament.

More in `docs/architecture.md` (the chain, the record, the store and the review, the app), `docs/concept.md`,
`data/schema/DEFINITION.md` (the schema) and `docs/mapping.md` (the schema against OpenParlData and five standards).

## Where data goes

Docket sends page text and, for pages without a text layer, image cuts of the page to the model endpoint, and nothing
anywhere else. In operation it fetches nothing from OpenParlData or any other source; its only input is the PDF it is
given. Only the register of persons is loaded once, by hand, when an installation is set up (`tools/register.py`);
without it Docket runs as well. The app loads no fonts or scripts from outside.

## If something does not work

- **Runs end without values:** the key is missing or wrong. http://localhost:8080/api/health says `"model": true` once a
  key is set; after changing `.env`, stop and start `make run` again.
- **The model refuses or limits the calls (403, 429):** after a 4xx the client sends the call once more, and a second
  403 or 429 stops the run; wait and upload again. It sends ten calls one after the other, then pauses half a second.
- **Compose rejects `env_file`:** it is older than 2.24; update Docker.
- **Port 8080 is taken:** stop what uses it, or change the left side of `"8080:8080"` in `compose.yaml`.
- **The administration asks for no password:** `ADMIN_PASSWORD` is not set in `.env`; this is meant for a local run
  only.

## Limits

About three documents in ten still carry at least one mark for a person – mostly a scanned block whose reading the image
check doubts, or a value the model put at a block where it does not stand. Without a mark does not mean without error: a
value can stand on the page and still be in the wrong field; the technical report and `results/reference/` give the
accuracy per field. A document without a readable number gets a weaker key, from place, date and title. The documents of
the tests are not in this repository, because they name people; `data/documents/README.md` says where each comes from
and how to put it back.

## Tests

`make test` runs on the host, without Docker, without a model and without the network (Python 3.11 with numpy). On a
clean checkout it runs 231 checks in 9 files; with the documents put back (`data/documents/README.md`, and poppler
installed) 509 checks in 28 files. `docs/tests.md` writes up 76 tests with question, test, result, finding and the
logged run; `docs/evidence.md` holds the series of measurements; the runs are under `results/`.

## In this folder

| Path | What it is |
|---|---|
| `src/docket/` | the pipeline, the store, the server (Python) |
| `app/` | the browser app (Angular), built into `src/docket/app/` |
| `data/schema/` | the contract, its definition, the fields file, the example record, a second contract |
| `data/knowledge/` | prior knowledge as tables: number forms, names of parliaments, sections, types, vocabulary |
| `data/documents/` | where the documents of the tests come from (the documents themselves are not here) |
| `docs/` | architecture, concept, mapping, evidence, tests, appendix |
| `results/` | the logged runs behind the numbers |
| `tests/`, `tools/` | the checks; the tools that rebuild the knowledge and run the measurements |

Licensed under Apache 2.0 (`../LICENSE`).

---

*Below: the text of the challenge template, as the organisers wrote it.*

# Academia Challenges

Submissions must use the Apertus model family.
For Track 2 this means that submitted solutions must be built with Apertus. Other open-weights models can be used to support development, e.g. as automatic judges during evaluation. Their role must be clearly described in the submission report.

💬 In case you have questions, join the conversation on Discord or send an email to “hello@hackapertus.ch”

## How it works
Pick from 5 academia challenges provided by Swiss academic institutions:

- **FHGR:** AI-Powered Job Interview Coach
- **OpenParlData:** Extracting Parliamentary Affairs from PDFs into One Common Structure
- **OST:** Multilingual Natural Language Inference over Swiss Official Voting Booklets
- **UZH:** Detecting Cross-Lingual Semantic Differences in Swiss Government Websites
- **ZHAW:** See It, Say It, Pick It: Vision-Language Grounding for a Real Robot Arm

The challenges incl. submission and judging criteria are described in our **Getting Started guide**:
https://hackapertus.notion.site/getting-started-guide-onlinehack

## Run it

Keep `track_2a/` as it is: don't rename it or move its files, just delete the
other track directories.

From the root of the project:

```bash
make run
```

Fill in the [Makefile](Makefile) so that it works on a clean checkout. It is
expected to run the project in a Docker container, since that is how the judges
will run it, without relying on anything already installed on your machine.

Requirements: `runtime, hardware, API keys, model weights`

## Data
The `data/` directory must not exceed 100 MB.


## 📦 Submission Requirements & Deliverables
❗️ Submissions are not handled on Devpost. Submit through our website only:
http://hackapertus.ch/online-hack/submissions

Requirements differ by challenge. See the description of the challenge you are entering for the exact deliverables.


## ⚖️ Judging Criteria
Judging criteria also differ by challenge. See the respective challenge description.


## Support

**Licensing requirements**
Please check our Terms & Conditions (6. What you build is open source):
https://hackapertus.ch/terms-and-conditions

## FAQ
💡 https://hackapertus.ch/faq

## Contact
💬 In case you have questions, join the conversation on Discord or send an email to “hello@hackapertus.ch”
