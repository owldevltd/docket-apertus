# Affair schema 0.8: definition

Contract: `docket.json` (JSON Schema 2020-12). Beside it the example `example-nidau-m185.json`, what the pipeline produced for the kickoff document, and the fields file `fields.json`, built like the data: wherever a value from the document belongs, it holds the question for that value.

## In one sentence

The JSON is the OpenParlData API's answer for an affair, unchanged, plus keys from JATS for everything OpenParlData does not carry: further header entries and the build-up of the document.

No XML, no XSD. The aim is a clear, traceable, reusable, extensible schema.

## The two rules of the mix

1. **If OpenParlData already has a place for it, it stays there.** A further date goes into `events`, a further person into `contributors`, each as an additional entry with `source`.
2. **Otherwise a key is added, and it is named like the element in JATS.** So every new key can be looked up in JATS.

## Fixed and dynamic

- **Fixed (14):** what the first documents demanded. On the affair `schema`, `custom-meta`, `related-article`; on the document `page-count`, `body`, `response`; `source` on an added event; the seven blocks `sec`, `p`, `list`, `def-list`, `table-wrap`, `graphic`, `sig-block`.
- **Dynamic (22):** what was added later because it may be needed. In the contract it carries `dynamic: true`. It is foreseen and named, but used only once a document demands it.

The rule behind it stays: a new key or block is added only when a document demands it.

## The contract

`docket.json` is this definition as a **JSON Schema** (draft 2020-12). Described is only what is added; the fields of OpenParlData stay free. Blocks are strict: a field that is not in the schema fails. What was added later carries `dynamic: true` there as well; for JSON Schema that is a mere annotation and changes nothing in the check.

Enumerations are English in this repository: `how` is `literal`, `derived`, `cited` or `composed`; `decision` is `confirmed`, `changed` or `rejected`. Content, the text of the documents and the values taken from them, stays in the language of the document.

## Why this way

| Reason | What supports it | What is not shown |
| --- | --- | --- |
| It covers everything in our sample. | 72 first pages looked through: whatever occurred has a block or key below. One document (Nidau M 185, two pages) is written out in full. | The other documents are looked through, not written out. There is nothing for stamps and redactions. |
| It extends without a new model. | Three fields have no fixed list of values. Further keys and blocks come from JATS and are marked dynamic. | – |
| It respects the client's wish. | The client wants an existing standard as guide and no new model to learn; the missing layer is, in the client's own words, "like JATS"; XML is not asked for. The API's answer stays as it is. | Whether JATS as the template is approved by the client is still to be confirmed. |
| With Akoma Ntoso the small model does not get through the door; the performance drops too far. | The more structure in the task, the worse the 8B: full element JSON 34 of 72 right, lean JSON 39; five excerpts instead of one 52 instead of 67 %. Akoma Ntoso demands 17 identification elements per document and marks values in the middle of the text. | Apertus with Akoma Ntoso against JATS directly is not measured. |

## The header

Everything from OpenParlData stays with its name and form: the affair with `docs`, `contributors`, `events`, `texts`. These keys are added. All but `schema` are optional: they are there only when the document yields something for them.

**On the affair**

| Key | Content |
| --- | --- |
| `schema` | version of this definition, here `"0.8"` |
| `id` | what the affair is called here: the key Docket forms for it from its parliament and its number (`nr-743-m185`), under the name OpenParlData has for an affair's id. A record names itself, so nothing beside it is needed to find or to link it |
| `body_key` | the parliament the affair belongs to, by OpenParlData's key for it (`743`, `ZH`); told with the document or read from it, absent when neither |
| `sources` | places for values whose own place carries no `source` (`number`, `title.de`, `type_name.de`, `begin_date`, `article-version`, `article-type`, `abstract.de`, `kwd-group.<n>`): per entry `path` (the way to the value, with dots), `doc`, `block`, `how`, `approve` |
| `custom-meta` | printed header entries without a place of their own (file reference, department): `meta-name`, `meta-value` |
| `related-article` | related affairs: `affair_id` or `number` |
| `related-object` (dynamic) | a reference to something that is not an affair (an act, a plan, a report): `text`, `uri` when there is one |
| `kwd-group` (dynamic) | keywords, a list |

**On the document** (per entry in `docs`)

| Key | Content |
| --- | --- |
| `page-count` | number of pages |
| `language` | the language the document is written in (`de`, `fr`, `it`, `rm`, `en`), under the name OpenParlData has for it; told by code from the document's own words, absent when none leads clearly |
| `article-version` (dynamic) | the version as printed ("Fassung nach 2. Lesung") |
| `article-type` (dynamic) | the kind of the document in the affair, its role rather than the affair's type: `submission` (the text handed in), `answer`, `bill`, `minutes`, `committee-report`, `act`, `attachment`. Named by the model as one word of this list and found by code from the words of the first page (`data/knowledge/kinds.json`, the list grows with the knowledge): the same kind from both stands without `approve`; where they differ, the model's kind stands and a person confirms it in the review; absent when neither says anything. A run carries it into the affair's record with its place, like a value read from the document |
| `abstract` (dynamic) | a summary, per language as OpenParlData has it (`{ "de": …, "fr": … }`); this covers `trans-abstract` too. The pipeline asks for it in the language of the document and lays it under that language |
| `conference` (dynamic) | the session or meeting the document names: `conf-name`, `conf-date`, `conf-loc`. Only when the document is not already attached to an OpenParlData meeting (`meeting_id`) |
| `journal-meta` (dynamic) | press and periodicals only: `journal-title`, `publisher-name`, `issn` |
| `volume`, `issue`, `fpage`, `lpage` (dynamic) | periodicals only: volume, issue, first and last page |
| `body` | the build-up of the document as a list of blocks |
| `back` (dynamic) | what follows the text: appendices, footnotes, references |
| `response` | an answer within the same document: `response-type`, `title`, `body`. Set by code where a heading announces the answer ("Antwort des Gemeinderates", "Réponse du Conseil d'Etat", "Risposta del …"): what stands from that heading on, up to the next section with a known name or to the end, with the heading as `title`. The words that announce an answer are the same for every parliament (`data/knowledge/sections.json`, `response`) |

**On a contributor** (per entry in `contributors`, in addition to the fields of OpenParlData)

| Key | Content |
| --- | --- |
| `degrees` (dynamic) | title ("Dr.") |
| `aff` (dynamic) | affiliation other than the party: function, place, committee |
| `on-behalf-of` (dynamic) | on behalf of (parliamentary group, committee) |
| `address`, `email` (dynamic) | as printed |
| `author-comment` (dynamic) | an addition about the person |
| `etal` (dynamic) | `true` when further persons are named without names ("und Mitunterzeichnende") |

When the person is known to OpenParlData (`person_id`), title, address and email are already in `persons` there. For a contributor read from a document, `person_id` is set when the printed name is found as exactly one person of that document's parliament; its place stands in `sources` (`how: derived`), with `approve` when the name was found by the last name alone or with one character off. The printed name stays as it stands.

## The blocks

In `body`, `back` and in the `body` of a `response`. Names as in JATS (Archiving 1.3).

| `type` | For | Own fields | Where it comes from today |
| --- | --- | --- | --- |
| `sec` | a section with a heading | `sec-type`, `title`, `content` (blocks) | the bridge: text from 1.3 times the base font size, or a section name from the project's prior knowledge (begründung, antrag, ausgangslage, …) → `sec-type` |
| `p` | a paragraph | `text` | the bridge: a text element of the geometry step, taller than one line |
| `list` | a list, numbered questions | `items` (texts) | the bridge: a counter or a mark on the left, text on the right; else the classification of the rest by the model |
| `def-list` | label and value, as on a cover sheet | `items` with `term` and `def` | the bridge: a label with a colon on the left, the value on the right; else the model |
| `table-wrap` | a table | `rows` (rows of cells) | the bridge: lines of the geometry step with enough text in enough columns |
| `graphic` | an image, a coat of arms, a plan | – | the bridge: elements without text |
| `sig-block` | a signature | `text`, when legible | the classification of the rest by the model |
| `app` (dynamic) | an appendix (only in `back`) | `title`, `content` (blocks) | not built |
| `fn` (dynamic) | a footnote (only in `back`) | `label`, `text` | not built |
| `ref-list` (dynamic) | a list of references (only in `back`) | `items` (texts) | not built |
| `notes` (dynamic) | a note outside the text flow (only in `back`) | `text` | not built |

Every block also carries:

- `id`: id within the document, in reading order (`b1`, `b2`, …)
- `page`, `x`, `y`, `width`, `height`: page and box in the page image at 300 dpi, as the geometry step delivers them
- `approve`: only when the text was read by the model and a person should look; a block carries it as soon as one of its elements does
- `font`, `font-size`, `color`: the font as the PDF names it (with "fett" or "kursiv"), size in points, colour as `#rrggbb`; the font only with a text layer, size and colour estimated otherwise
- `isOCR`: `true` when the text of the block comes from text recognition (read by the model from the image, or from the OCR layer of a scan), `false` when it was taken from the PDF's text layer. The geometry step sets it; without it the field is absent.

## Filling from the document

The input is always the PDF alone; the affair arises from the document, in the form of the OpenParlData answer. Which values go where is in `fields.json`, built like this JSON: wherever a value belongs, it holds the question (`name`, `question`, `form`, `min-words`, `max-words`, `choice`, `dynamic`, `pages`, `when`, `together`, `paired`, `reader`, `apart`, `entry`, `free`, `block-text`) and says what the value is: its `entity` (`body`, `identifier`, `category`, `person`, `group`, `place`, `date`, `event`, or `text` for what is none of these; the list is `data/knowledge/entities.json`, with what stands behind each to hold a value against) and, where several fields share an entity, the `role` under it (the affair's own `number`; for a person the word of a standard role of the vocabulary, `author`, `cosign`). The entity belongs to the value, not to its place: the store keeps every value under it, whatever JSON the value is placed in. Where a lookup has something to add, the field says where it goes: `standard` is the path of the standard name of a category (the affair's type through the vocabulary, `type_harmonized`), `id` the key beside a person's name for the id the register holds (`person_id`). The pipeline asks the model with the text image of the first pages (page 1, with a cover sheet page 2 as well) and for some fields with the whole document, up to six fields per call. Fields that name the same word under `together` share a call of their own, since each needs to see what the others take: asked apart, the model gave the same names to the authors and to the co-signers. Every call starts with the line `$task.lead`, a question every document can answer and whose answer is not used: the model tends to give the first line of a call a value whether the document has one or not. A field with `when` is asked only where one of its words stands on the pages. A list field that names another field under `paired` is asked for both in one line, entry by entry (an event: first its day, then what happened); the field named has no line of its own, and an entry stands only with both parts placed, so that every entry keeps its own day. A field with `reader` is read by code and not asked: the place is what stands before the day in a line of a place and a day, and stays empty where the pages hold no such line. A field with `apart` leaves out a value that already stands under one of the fields named there. A field with `entry` gives its value to a list as well: the day an affair was submitted is its first event, as OpenParlData lists it. Beside the fields, `$task.ask` holds questions about the document itself: what the document is in its affair (`article-type`), one word out of the list of kinds. The answer stands on no page; it is held against the kind the code finds from the words of the first page, and only the same kind from both stands without `approve`. The pipeline builds the answers in like this:

- A field at a place that already has a value (from an earlier document of the same affair): if the value is the same, it stays; if it differs, the printed value goes beside it as `custom-meta` (`meta-name` = the field's name), with its place. Several documents belong to one affair when they carry the same affair number.
- A list (`contributors.data`, `custom-meta`, `related-article`, `related-object`): one entry per value with the fixed parts of the template (role, `meta-name`) and its place. A person already among the contributors is not created again.
- Entries about the document (`conference`, `article-version`, `abstract`) go into its existing entry; the place wherever the contract provides a `source`.
- A value counts when it stands literally on the page; otherwise with the block the model names (in the text image every block is preceded by its id). What has neither is dropped.
- What the model words itself (a field marked `free`, the summary) stands nowhere on the page and need not share a word with a block: it keeps the block the model names, else the head of the document, as `composed` and with `approve`.

## Provenance

Every value that comes from the document points at its block with `source`: `{ "doc": <document id>, "block": "<id>", "how": …, "approve": … }`. Through the block it leads back to page and box. Where the value's place carries no `source`, it stands in `sources` at the root with the path to the value.

`how` says how the value got its place: `literal` (found in the block), `derived` (every word of the value stands in the block, put together differently; not a case for a person), `cited` (named as a block by the model, not literal), `composed` (phrased by the model, such as the summary). `approve: true` means a person should look: a text the model worded (`composed`, the name of an event) carries it only where it leaves its document (few of its words stand there, another language, a number the document does not hold); otherwise set when the value was found neither literally nor derived, or when the block itself carries `approve` (read pages, the image check). Values without any place do not come from the document.

## The person's update

What a person does with a value stands at its place as `review`: `{ "at": <time>, "decision": "confirmed" | "changed" | "rejected", "before": <the value before>, "by": <who>, "rule": <rule> }`. The value itself is changed in place; `before` keeps the old one. `rule` names the general rule when the change came from one ("Kanton X" → "X") or founded one.

The review view shows, for a flagged value, how many further documents carry the same value with the same flag (same field, same `how`, same pattern), counted over the collected affairs. A change a person makes the same way twice proposes a general rule: the same replacement on every value with the same pattern. The proposal says how many values it would change; a person accepts or declines it, and only an accepted rule changes values, with `rule` at every place. A rule a decision by hand speaks against is not proposed. The store keeps the rules. The decisions are at the same time the teaching material for a small model that later learns which values a person has to see.

## Fields without a fixed list of values

- `sec-type`: what a section is (in the example: `deckblatt`, `antrag`, `begruendung`, `beschlussentwurf`)
- `response-type`: what kind of answer (the pipeline writes `answer`)
- `meta-name` in `custom-meta`: header entries as printed (in the example: `Aktenzeichen`, `Ressort`)

How the prior knowledge attaches here is not part of the contract. German first.

## Rules

1. Nothing on the fields of OpenParlData is changed, renamed or removed.
2. New things are only appended.
3. What comes from the document carries `source`.
4. Text stays unabridged and verbatim.
5. A new key or block is added only when a document demands it, and then with the name from JATS. What is added that way carries `dynamic: true` in the contract.

## What of JATS is in and what is not

Counted on the schema of JATS 1.3 Archiving.

| Part of JATS | Possible elements | OpenParlData already carries | Taken over as keys | Not taken over |
| --- | ---: | --- | --- | --- |
| Document header (`article-meta`) | 47 | 12: id, type, title, contributors with affiliation, date, course, addresses, further documents | 13: `custom-meta`, `related-article`, `related-object`, `kwd-group`, `page-count` (from `counts`), `article-version`, `abstract`, `trans-abstract` (in `abstract`), `conference`, `volume`, `issue`, `fpage`, `lpage` | 22: `permissions`, `author-notes`, `email`, `funding-group`, `support-group`, `product`, `isbn`, `supplement`, `page-range`, `elocation-id`, `pub-date-not-available`, `x`, and the variants and subdivisions of version, affiliation, volume and issue |
| Journal block (`journal-meta`) | 12 | for news items: `news` (title, date, place, address) | 3: `journal-title`, `publisher-name`, `issn` | 9 |
| A person (`contrib`) | 22 | 5: name, role, affiliation (party), id, person or group | 6: `degrees`, `on-behalf-of`, `address`, `email`, `author-comment`, `etal`; plus `aff` wider than the party alone | 11: name variants, biography, references, `anonymous` |
| Body (`body`) | 38 | – | 7 blocks | 31, among them formulas, code, verse, media |
| What follows the text (`back`) | 10 | – | 5: `app`, `fn`, `ref-list`, `notes`, plus `sec` | glossary, acknowledgements, biography |
| Answer (`response`) | – | – | yes | – |
| `sub-article`, `floats-group`, `processing-meta` | – | – | – | all three |

Why the journal block is in: the corpus also holds press and periodicals. The first sample had a saved newspaper page, a municipal magazine of 56 pages and two press releases; OpenParlData keeps its own table `news` with 338 667 entries that documents can be attached to.

## Deliberately not in

- Values in the middle of a sentence as a mark of their own ("ANFRAGE von … betreffend …"). The value stands in the header and points at the paragraph with `source`.
- Rights and licence (`permissions`), funding, product details.

## What the terms are called elsewhere

`docs/mapping.md` names, for every key and block of this definition and for the controlled lists, what holds the same thing in OpenParlData, JATS, Akoma Ntoso, Parla-CLARIN, Popolo and Docling, by the names of their own schemas, and says where nothing was found. It is written from `mapping.json` beside this definition (`python3 tools/mapping.py`). Which element answers a term is a reading of the schemas; that every name exists in its schema is checked against the schema files (`python3 tools/mapping.py --standards <folder>`), and a test holds the file against the contract, so a key added here without a row there fails.

## Other contracts

The validator has no schema built in; it takes the contract as input. A different kind of document can have its own contract beside this one.

The same holds for the shape of the affair itself. What the store knows of an affair does not hang on this contract: every value is kept as a row that says what it is (its entity), which field asked for it and where it stands in the document, and what a person decided is kept there too. A fields file says where each of it goes. `plain/` holds a second contract with its fields file, built unlike this one on purpose: other keys, other nesting, closed everywhere, no room for the documents' blocks or the places of the values.

```
reference                     the affair's number
subject.heading               the title
subject.form                  the type as the document names it
subject.form_standard         its standard name, from the vocabulary
received                      the day it was handed in
people[]  as, name, group     who submitted and who co-signed; person = the id from the register
where     polity, council, place
keywords[]
course[]  what, when
```

`python3 -m docket view --fields data/schema/plain/fields.json --contract data/schema/plain/contract.json --out <dir>` writes every stored affair in that shape, from the rows and without reading a document again. A second fields file names the fields by the names they were read under; it can leave fields out, and it cannot ask for what was never read. What this contract adds of its own (`docs` with the blocks, `sources`, `source`, `review`) is left out where the other has no room for it and stays in the store; a value a person rejected is left out of a record that cannot show the mark, and a second value for a field that already has one (from a further document) stays with its row where the record has no place beside its fields.

## Example (excerpt)

```json
{
  "schema": "0.8",
  "number": "nid 0.1.6.2",
  "title": {
    "de": "Aufnahme von Bootsflüchtlingen"
  },
  "type_name": {
    "de": "Motion"
  },
  "begin_date": "2018-11-22",
  "sources": [
    { "path": "number", "doc": 1, "block": "b12", "how": "literal" },
    { "path": "title.de", "doc": 1, "block": "b13", "how": "literal" },
    "… (5 entries)"
  ],
  "custom-meta": [
    { "meta-name": "addressee", "meta-value": "Gemeinderat", "source": { "doc": 1, "block": "b11", "how": "literal" } },
    { "meta-name": "place", "meta-value": "Nidau", "source": { "doc": 1, "block": "b15", "how": "literal" } },
    "… (5 entries)"
  ],
  "contributors": {
    "data": [
      {
        "role": { "de": "Urheber/in" },
        "fullname": "Lüthold Katrin, SP Kern",
        "source": { "doc": 1, "block": "b9", "how": "literal" },
        "party": { "de": "SP Kern" }
      }
    ]
  },
  "docs": {
    "data": [
      {
        "id": 1,
        "name": "nidau-m185",
        "page-count": 2,
        "body": [
          { "id": "b1", "type": "def-list", "items": [ { "term": "STADTRAT", "def": "" } ], "page": 1, "x": 136, "y": 124, "width": 188, "height": 24, "font": "Verdana fett", "font-size": 6.7, "color": "#000000", "isOCR": false },
          { "id": "b2", "type": "graphic", "page": 1, "x": 880, "y": 130, "width": 102, "height": 110, "font-size": 36.3, "color": "#000000" },
          "… (21 more blocks)"
        ]
      }
    ]
  }
}
```

The full example is what the pipeline delivered for the Nidau PDF on 6 October 2026, contract 0.8: two pages, 23 blocks (14 `p`, 5 `sec`, 2 `def-list`, 2 `graphic`). It holds the model's errors as they came; the affair identifier there was taken from the file reference "nid 0.1.6.2", not from "M 185". The example shows the form, not correctness.

## Changes

- **Under the language of the document; the standard role** (11 October 2026): what a document prints, its title, its type, a party, an event, stands under the language the document is written in (`title.fr`), as OpenParlData's own answers have it; until then everything stood under `de`. A contributor carries `role_harmonized`, the standard role in four languages as OpenParlData names it, in place of a fixed German word under `role`: the role as the document words it is not read. The standard name of an event is not written: of 96 events read in the runs of 10 October none is worded as one of OpenParlData's 106 standard names. The contract itself unchanged.
- **The record names itself and its parliament** (11 October 2026): `id` and `body_key`, two fields OpenParlData has, are filled in every record. Until then both stood beside the record, in the store; what a visitor reads is now made of the records alone (`docket.public`), the lists and the tables of those who take part, the groups, the meetings and the events included. The contract itself unchanged.
- **The language of a document, and its summary in it** (11 October 2026): every document entry says its `language`, told by code (210 of 211 documents of known language right, one too short to tell). The summary is asked for in that language, named in the question, and stands under its key (`abstract.fr`); a field of the fields file says so with `own-language`. Asked "in the language of the document" without naming it, the model summed up the French and Italian documents in German. The contract itself unchanged.
- **A summary keeps its place** (11 October 2026): a value the model words itself is no longer dropped when the block it names holds no word of it. Counted on 211 documents of the runs of 10 October: the model answered the summary for all, 84 had a place, 127 were dropped (it sums up French and Italian documents in German). The contract itself unchanged.
- **The answer under its heading; the mapping** (11 October 2026): `response` is filled where a heading announces the answer, with `response-type` `answer`. New: `mapping.json` beside this definition and `docs/mapping.md`, the terms of the schema against OpenParlData and five standards. The contract itself unchanged.
- **English field names** (10 October 2026): the fields of the fields file are named in English (`number`, `title`, `authors`, `polity` …) instead of German, and with them the `meta-name` of a value under `custom-meta` (`polity`, `place`, `parliament`, `department`, `addressee`). The questions put to the model stay German. The contract itself unchanged.
- **A second contract** (10 October 2026): `plain/`, another shape for the same affair, filled from the same rows. This contract unchanged.
- **Entity in the fields file** (10 October 2026): every field names what its value is (`entity`, with a `role` under it where needed), and where a lookup's result goes (`standard`, `id`). The contract itself unchanged.
- **Repository edition** (8 October 2026): descriptions and enumerations in English; the contract itself unchanged.
- **0.8** (6 October 2026): `how` knows `derived`. For the title the text of the named block counts when every word of the answer stands in it and the block is not much longer (fields file `block-text`).
- **0.7** (6 October 2026): `review` at every place (`source` and `sources`): `at`, `decision`, `before`, `by`, `rule`. Reason: the person's decision belongs in the data model, so that the review view shows it, the general repair uses it and the learning gets it.
- **0.6** (6 October 2026): `source` with `how` and `approve`; `sources` at the root for values without a place of their own; blocks with `font`, `font-size`, `color`. Reason: the front end must show where a person should look, and digital documents carry their font.
- **0.5, text added** (6 October 2026): section "Filling from the document" (fields file, rules for building in), column "Where it comes from today" at the state of the bridge, the example is now the pipeline's result for a real affair. Contract unchanged.
- **0.5, corrected** (5 October 2026): `docs`, `contributors` and `events` may also be `null` in the contract. The API delivers that when an affair has no contributors (7 of 72 affairs checked); the contract demanded an object and so rejected an unchanged API answer.
- **0.5** (5 October 2026): every block may carry `isOCR`. The column "Where it comes from today" names the rules of the bridge.
- **0.4** (5 October 2026): the contract is now a JSON Schema. The marker for the prior knowledge is removed. Checked with a validator.
- **0.3** (5 October 2026): contract as JSON beside the definition. Everything that came with 0.2 is `dynamic: true` there (22 parts); 14 are fixed. The rule "only when a document demands it" applies again.
- **0.2** (5 October 2026): keys are now named exactly as in JATS (`custom` → `custom-meta` with `meta-name` and `meta-value`, `related` → `related-article`, `pages` → `page-count`). New in the header: version, summary, keywords, related object, session or meeting, periodical details, further details about a person. New: `back` with appendix, footnote, reference list, note.
- **0.1** (5 October 2026): first version with six new keys and seven blocks.
