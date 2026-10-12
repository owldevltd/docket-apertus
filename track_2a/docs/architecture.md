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
| Fields | `fields/` (`fields`, `filler`, `placer`) | the fields file asks the model up to six questions per call over the first pages and over the whole document; fields that belong together (who submitted, their party, in whose name, who co-signed) share a call of their own, and every call starts with one line that is no field, because the model tends to give the first line a value whatever the document holds; code takes an answer only with a place: literal in a block, derived from the named block, or cited with a word in it; composed values and cited ones carry `approve` | yes |
| Kind | `document/kind.py` | the document's role in the affair from the words of its first page, by the list in `data/knowledge/kinds.json` | no |
| Answer | `document/response.py` | where a heading announces the answer to a submission within the same document, what stands from there on becomes the `response` of the document beside its body, every block with its id and place; the words that announce an answer are prior knowledge for all parliaments alike, in German, French and Italian (`data/knowledge/sections.json`) | no |
| Key | `affair/identity.py` | the parliament and the affair number: the part of the printed number that has one of the number forms of the parliament, searched on the page by form where the read one has none, or a weak key from place, date and title; the parliament as told with the document, else from the read names of polity and parliament, in any language | no |
| Affair | `affair/merge.py`, `affair/types.py`, `affair/validator.py` | the documents of one key become one affair; the harmonised type comes from the label, through the names of the parliament in the vocabulary and else through the table of the export; the persons named are looked up in the register of the parliament (`affair/persons.py`); the record is checked against the contract by an own validator | no |
| Store | `store/` (`files`, `postgres`, `rows`, `review`, `rules`, `vocabulary`, `register`) | the affair with its documents, the fields reports, the rows of the documents, the decisions, the vocabulary, the register of persons; reviews survive a new run over the same document | no |

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
number forms per parliament, the names of the parliaments in every language OpenParlData holds them in, the
kinds of documents with their words.
`tools/knowledge.py` rebuilds the three tables from the export and the API. The values the model placed are
kept per run (`values.json`) for a person to look at and are never offered to the model: measured, that
brought more values that are not on the page.

`vocabulary.json` is the stem of the vocabulary, as OpenParlData keeps it in its admin panel
(`tools/vocabulary.py`): per parliament the names of its affair types with the harmonised type each stands
for, the harmonised names of the events, the kinds of groups. It is only where the vocabulary starts; what
is used lies in the store.

## The store and the review

A store holds affairs by key, each with its record and its documents, the fields reports and the rows of the
documents, the decisions, the rules and the vocabulary. Files under `storage/store/` serve a single machine
and the tests; Postgres (`DATABASE_URL`) serves the container, with the records as JSONB and the rows, the
decisions and the vocabulary as tables. Page images stay on disk in both.

The rows (`store/rows.py`) say what was found in a document in terms that do not depend on the target JSON.
A record places a value under the key its JSON happens to use; a row says what the value is: its entity
(body, identifier, category, person, group, place, date, event, or text for what is none of these; the fields
file names it per field), the role under it, the field that asked, the value as read, and where it stands,
the page and the box of its block. The block's id is a reference into that document's blocks and means
nothing in another document; over documents a value is asked for by entity and value, in Postgres through
columns with an index. An answer that did not hold gets a row as well, without a place, and so does what
the run found the document itself to be, its kind, which the affair's record then holds with its place. The blocks stay in
the record, to show and to rebuild the document; the rows point into them. A run writes the rows with the
fields report, and `make rows` writes them for a store filled earlier. The way back is exact: the values
taken from the rows are the ones the answers held, and the affair built from them is the same record
(`tests/rows.py`).

A decision is written at the value's source: confirmed; changed, with the old value kept in `before`;
rejected, with the value left in place and marked, so an export can leave it out. `approve` stays as the
machine's signal; open means approve without review.

What was decided is kept at the row of the value, and the record follows the rows. The row keeps the value as
it was read; the decision stands beside it with the review and, after a change, the value that counts now.
When an affair is built, each row is told where its value sits in that record, and this is written anew with
every build. So a new run over a document that is already stored finds the rows of the earlier run again, by
field, value and block, takes their decisions over and puts each at the place its value has now; the path in
the record plays no part in it. One read value can sit in several entries, a party named once for three
persons: a decision then belongs to the entry it was made on. A review a record held before the rows did is
taken into them; the earlier way of carrying a review, by document, block and path, serves only an affair that
was stored before its documents had rows.

What a value can be is a list in the data (`data/knowledge/entities.json`), not in the code: body, identifier,
category, person, group, place, date, event, and text for what is none of these, each with what stands behind
it to hold a value against, the list of the parliaments, a list of the vocabulary, or the register. A new
entity is a new entry, with a list behind it or without.

A lookup goes by what stands behind the entity of a value, and the fields file says where its result goes. A field that is a category
names the place of its standard name (`standard`), and the vocabulary is asked; a field that is a person names
the key of the id beside the name (`id`), and the register is asked; no key of the record is written into the
code for it. What the lookup found stands at the row of the value: the standard name, the person a name was
told as, the parliament of a body. The id the record got for a name is a part of that name's row, and a
decision on it is kept there like any other.

The same change twice on the same field proposes a rule (`store/rules.py`): prefix or suffix off or on, a
letter read for a digit, the spelling, or the same value becoming the same value. The field is the one of the
fields file, taken from the row of the value that was changed, so a rule does not hang on a key of the record
and counts for the right field where an entry holds several values, a name and its party. Nothing is applied
by itself. The answer to the second decision carries the proposal with its reach, how many values in how many
affairs it would change and what they would become, and the app asks. A yes makes the rule active: it changes
every fitting value of that field in the store, each with a review that names the rule, so every application
can be seen and taken back. A no keeps the rule from being proposed again. A rule a decision by hand speaks
against is not proposed: a person confirmed a value it would change, or changed it into something else. A
person can switch an accepted rule off and on, and what people confirm or withdraw is counted on it. Which
affairs a rule can reach is asked of the rows, by field and value; only those records are read and counted,
not every record in the store.

The vocabulary (`store/vocabulary.py`) is a stem that can be changed. When the store is opened it is brought
up to the stem of the checkout: an empty store is filled, a newer stem replaces every row nobody changed.
A row says what a name of a parliament stands for ("Anzug" in Basel-Stadt is a postulate), or lists a name
without a standard. A person can set another standard for a name or add a name the stem does not have; that
row carries who and when and keeps what the stem said beside it, a newer stem leaves it alone, and it can be
taken back. The type of an affair is looked up in the names of its parliament first: the same label stands
for another type elsewhere, so the table of all parliaments is asked only where the parliament is not known
or does not list the label. OpenParlData calls its harmonised types provisional; that is why the stem is a
list in the store and neither code nor a fixed file.

The roles of those who take part in an affair are a list of the vocabulary as well: the 21 standard roles
OpenParlData knows (author, cosign, speaker …) and, per parliament, the names it uses for them, read from
OpenParlData's export of the contributors (`tools/vocabulary.py --roles`). A field of the fields file names its
role by the standard role's word, so the role of a value is a row of that list and a role that is new is a
row a person adds, as with the types. The role itself still comes from the fields file, the field a name was
asked under; reading the document's own word for it is tried and measured, not built.

The register (`store/register.py`) holds the persons of the parliaments. `tools/register.py` loads them from
OpenParlData's exports into the store: id, name, parliament and party, nothing private, and nothing of it
into the repository. It is the one list that is not shipped, because it holds people; the tool fetches it
once, by hand, when an installation is set up. In operation Docket fetches nothing. A contributor a document names is looked up among the persons of that document's
parliament only: exactly, in either order of first and last name and without a title, a party or a place
behind it; by the last name alone; or with one character off. It counts as found when exactly one person
fits. Then the entry gets that person's id, with a place in `sources`, and a person is asked to look where
the name was not found exactly. The printed name is never changed. A name nobody carries, standing literally
in the document and looking like a name, is kept as a candidate with the documents it was seen in, and from
the third document on the register takes it in as learnt; a newer export replaces what came from OpenParlData
and leaves what was learnt. Without a parliament nothing is looked up: over all parliaments one wrong
character leaves too many candidates.

Beside the model stands a second opinion on where the value of a field is, learnt from the rows without the
model (`fields/second.py`, `make learn`). Two ways name a block for a field: the place where the value usually
stood in the documents of a parliament, and a small network that tells a block that holds a field by its
look, its page and box, its kind, its font, its length, its digits, never by a word of its text. The teacher
is what the model read and what people decided. No cut for either is chosen by hand: when they are learnt
they are tried on documents held back, the cut is taken where agreeing outweighs disagreeing by most, and a
way is kept for a parliament and a field only where it outweighs at all. In a run after that, a value that
does not stand in the block the opinion names is marked for a person; where the model found nothing, what has
the form of the field in the named block is taken and marked; where the two agree, nothing changes, and a
mark the model's reading set stays. For a
list of names a network of its own names every block it takes to hold some of them, and a name placed
elsewhere is marked; tried the same way it is kept for few such fields. A store that has learnt nothing runs
as before.

With that, the record is one way of laying out what the rows hold, not the place where it is kept.
`affair/view.py` lays a stored affair into the shape of any fields file and contract: the values where that
file places them, the standard name and the id where it names a place for them, a changed value changed.
`data/schema/plain/` is a second contract of another build, kept to show it: `python3 -m docket view` writes
the stored affairs in that shape, and `tests/views.py` holds the two shapes against each other field by field.
What the main contract adds of its own, the blocks of the documents, the places and the reviews, is left out
where the other has no room and stays in the store. The store and the app work on the contract that is
configured; the app reads the places of the values from that record, so a contract without room for them can
be written to, not yet worked on in the app.

## The server and the app

`server.py` is the standard library's HTTP server with a small router; `api.py` is what it answers with:
the affairs with every value that has a place, the decisions, the rules, the vocabulary, the register, the runs of the admin, and for every
open value the count of documents with the same pattern. Number, title, date and type for the list and the
head of an affair are found by their role in the fields file and sent as such; the app does not read them
from keys of the record. The review goes by the rows, not by the record (`store/entries.py`): the values it
shows, how each got its place, whether a person should look and what a person decided are built from the rows
of the affair's documents, and every value carries the id of its row. A decision names the value by that id;
it is written at the row first, and the record that is stored is the one from before with the decisions of
the rows laid onto it. The blocks of a document lie in the store on their own and are served per document.
So the review does not hang on the shape of the output: with the stored record replaced by the same affair in
the second contract, which has no room for places or blocks, it still shows every value and takes a decision
(`tests/entries.py`). The affair schema stays the format a run writes. Every document keeps with its answers what it was asked, the names of the fields and
a mark of the questions; the admin's area for the definition lists the fields with their entity, their role
and what stands behind them, and counts over the store in how many documents a field was asked and in how
many never, because the document was read before the field existed. That is told apart from a field that was
asked and found nothing. Such documents can be asked afterwards (`python3 -m docket ask`, or from that area):
only the missing questions go to the model, over the pages the store kept, the answers join the document's
report, and its affair is formed anew from the reports with every decision kept. A role or a kind of value
that is new therefore comes in as a field of the fields file with its entity and role, and the documents
already read are asked for it; reading the role of a person freely from the document was tried three ways and
did worse than the field a name is asked under. One lock per affair guards the decisions; the
contract is checked before anything is saved. The admin's runs (`jobs.py`) take an uploaded PDF, with the
parliament it comes from where the person handing it in tells it, run one after the other, and stay on disk
under `storage/runs/`. Nothing is fetched: what comes in is the PDF. The administration has an account, see
below.

The app (`app/`, Angular with Angular Material) is built into `src/docket/app/` and served as static files.
It has two levels. What a visitor sees follows OpenParlData's public app and changes nothing, and it is made
of the affairs in the affair schema alone (`public.py`: `/api/records`, and the tables that follow from the
records, those who take part, the groups, the meetings, the events): the start with
the affairs as result cards, a search over title, number, type, parliament and document names, filters by
parliament, type, kind of document and language, the address of what is shown and its JSON; an affair with
its rows, those who take part by their role, its course and its documents, and the record itself in the
affair schema; a document with what the record says of it, and its pages set from the blocks of the record
(`public/sheet.ts`): every block with its text at its place on the page, in its font, size and colour, as the
schema holds them (`x`, `y`, `width`, `height` at 300 dpi, `font`, `font-size`, `color`); a picture or a line
is a grey field, since the record keeps its place and not the picture, and pointing at a block shows what
the record says about it. No image of a page is used there. The record holds no paper size: a page is drawn
as A4 upright at 300 dpi, larger where a block lies outside that. The entry of the document in the record is
the JSON beside it.
The administration holds everything that changes something: the review (the affairs with how many values
are open, one affair with its page, red where a person has to look, the values beside it with the three
decisions), every decision taken, the runs, the rules, the vocabulary, the definition, what the second
opinion learnt, and the upload. It stands under `/admin` and is not linked from what a visitor sees. It has
one account (`ADMIN_USER`, `ADMIN_PASSWORD`): with a password set, every route of the API that is not part of
what a visitor reads needs the session of that account, reading as well; the session is made at `/api/login`
and rides in a cookie the page cannot read; and every decision, every answer to a rule and every change of
the vocabulary is by the account, whatever a request names. Without a password the administration is open,
for a local run, and acts under the account's name. That one account and the open administration without a
password were set by the assistant and are open. The vocabulary shows one parliament at a time: its names,
what each stands for, and where a person changed the stem; and the standard names of a list, to which the
administration can add one of its own, with its wording in the four languages, for names of parliaments to
stand for. Node is needed for the build only: locally through `make app`, in the container in
the first stage of the Docker image.

Both levels come in German, French, Italian and English, by the localisation Angular brings itself: the app
is written in German, its texts are taken out into `app/src/locale/messages.xlf`, and the build makes one
bundle per language, each in a folder of its own (`/de/`, `/fr/`, `/it/`, `/en/`). The switch at the top
right is a link to the same screen under the other folder; an address without a language goes on to the
German one. The wordings stand side by side in `app/src/locale/words.json`, and `make translations` writes
the files the build reads from it; `tests/translations.py` holds that no text is without one. The French,
Italian and English wordings were set by the assistant and are open: no native speaker has read them yet.
What a document prints stays in the language of the document; a standard name the record holds in four
languages is shown in the language of the page.

Everything a visitor is shown hangs on the `id` a record names itself by. A store can be older than the code
that reads it, so the server gives every affair stored without its `id` the key it is stored under, and the
parliament the run of its document noted, once at the start. One person, one group or one meeting is asked
of the tables by its name (`/api/contributors?fullname=`, `/api/groups?name=`, `/api/meetings?conf-name=`)
and comes with its rows alone; a type is found by any of its wordings, so a page in French can ask by the
French standard name.

## Measuring

`make test` runs without a model and holds the chain against references that existed before any run: the
text layer of the PDFs for the geometry and the text, the affairs of the API for the fields and the identity,
a reading by hand for the kinds, and the contract for every record; it also runs the server, the decisions,
the rules, the vocabulary, the register and the admin's queue on a file store. It forms the affairs of the
eight documents again from a stored run with the model and compares them with the stored affairs character
by character, so that a change to the core cannot move a value unnoticed. The documents, their page references
and their stored runs are not in the repository, because they name people: `data/documents/README.md` says where
each comes from; without them `make test` runs the tests that need no document. `make test-store` runs the store's
operations over Postgres as well, inside the running container, in a schema of its own. `make bench` runs the whole chain with the model over the
eight documents, about seventy calls, about three minutes, and keeps the raw exchange of every call.
`docs/evidence.md` holds every number behind a decision, `results/` the committed runs.

## Running it

`make run` starts Postgres and the server in Docker; the app is at port 8080. The server needs one CPU: the
computing without the model takes about five seconds per page, the model is called over the network one call at a
time, ten calls and then half a second of pause, so a digital document of three pages takes about twenty seconds
and one without a text layer about fifty (measured 12 October 2026 on 60 documents, `results/runtime/`). Memory peaked at 0.6 GB with one document in flight (the run of 8 October over the eight
documents). The model calls are the budget: four to six per document for the fields, one for the
sorting of the first pages, thirteen for a scanned page.
