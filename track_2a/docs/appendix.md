# Appendix: the tests behind the decisions

The technical report states what Docket does and what it reaches; this appendix shows what each decision rests on.
Every row is a test that was run, with its numbers and what was decided after it. The full record is `docs/tests.md`
(76 entries, each with question, test, result, finding and the run that was logged) and `docs/evidence.md` (the
series of measurements by date). Numbers marked "against the reference" are counted against the draft reference of
the 60 reference documents.

## 1 The automated checks

`make test` runs 509 checks in 28 files without a model and without the network. With the shipped documents in
place (`data/documents/README.md`) all of them run; without them, the checks that need no document.

| What is checked | Files (checks) |
|---|---|
| The page without a model: text layer in the elements, blocks against the contract, language, the answer within a document, the kind of a document | `text` (15), `blocks` (8), `language` (6), `response` (13), `kinds` (7); `compare` and `sources` measure the geometry against the text layer of the PDF and give every difference a cause |
| Asking and placing: which fields share a call, what code decides after the model, the same answers give the same record | `bundles` (13), `settle` (35), `fields` (10), `baseline` (9) |
| The dynamic model: rows to record and back without loss, the same affair in two contracts, asking stored documents only what they lack, decisions kept | `rows` (42), `views` (12), `ask` (12), `decisions` (23), `entries` (11), `store` (22) |
| Learning: rules from corrections, the second opinion, the register of persons, the vocabulary | `rules` (36), `second` (12), `register` (53), `vocabulary` (52) |
| The affair: key, type and merging, questions across the parliaments, the mapping onto the standards | `affairs` (21), `questions` (7), `mapping` (8) |
| Operation: server, administration with an account, the pace towards the model, a clean checkout, four languages of the app | `server` (31), `admin` (23), `client` (4), `shipped` (16), `translations` (8) |

## 2 The experiments behind the design

| Question | What was measured | Decided |
|---|---|---|
| Does the page split into the blocks of its text without a model? | 7 243 of 7 272 words of the text layer lie in an object the geometry found (99.6 %), on 40 first pages; the port of the geometry gives the same lists as the original on 482 pages | geometry first, the model never locates anything (`docs/evidence.md` 2) |
| Can the model say where a value stands? | it named a block that held not one word of the value in 142 of 204 cases | code places every value; a value without a place is not taken (`docs/evidence.md` 8) |
| How does the 8B read a page without a text layer? | one element per call: 101 of 180 identical; three marked elements in one image: 22.7 % character errors, ids swapped; a strip of three cut out: 111 identical; strip, then long blocks singly: 116 identical, 1.9 % errors, 126 calls | strips, then long blocks singly (`docs/evidence.md` 3) |
| Does a threshold of the image check separate right readings from wrong ones? | on 12 pages, 203 elements: at 0.01 98 of 102 wrong readings marked, and 56 of 92 right ones; at 0.02 86 and 49; at 0.05 40 and 30 | the threshold stays; the mark is informative, not decisive (`results/reading-threshold/`) |
| Does more structure in the prompt help the 8B? | the type of 72 documents (17 types), named from the bare label: 48 right; from the first page as full element JSON 34, as lean JSON 39, as text 35 | the model is shown text, not the structure of the elements; the type comes from a table of the printed labels (`docs/evidence.md` 4) |
| Which existing schema covers the brief and the documents? | 20 requirements against six schemas, yes / partly / no: Akoma Ntoso 16 of 20, JATS 12, Parla-CLARIN 12, OpenParlData 8.5, OParl 8.5, Popolo 6; Akoma Ntoso takes a document with its general elements but demands 17 identification elements with nothing from the document; JATS 1.3 Archiving validates; 72 of 72 answers of the API fit the contract unchanged | OpenParlData's record unchanged plus the names of JATS, in JSON; every term mapped onto five standards (`docs/mapping.md`) |
| Does the first field of a call draw a value? | the order turned: the party, now first, filled where nothing belongs 38 times against 21; with a line before the first field that is no field: 788 of 1 260 fields right against 704, against the reference | every call starts with a line that is no field (`docs/tests.md`, Fields) |
| Does a value inside a longer word count as found? | 58 of 1 451 values placed as literal stood inside a longer word or across word ends ("Parlament" in "Parlamentarischer Vorstoss") | whole words only (`results/unattended/`) |
| Do the rules after the model hold on documents they were not made on? | every rule tried on documents outside the set it was found on; on a third set of 151 documents a first form of a rule built a person out of the last name of one row of a table and the first name of the next | the rule asks that a value starts where a block starts (`results/unattended/`) |
| Is a day the model names at a block, without the day standing there, a day? | on the same 151 documents 19 of 20 such days stood nowhere: the block held a month and a year | a day has a place only where it stands (`results/unattended/`) |
| Can a summary the model wrote be held against its document? | its own summary shares 0.39 to 0.93 of its words with the document (0.71 in the middle), the summary of another document 0.18; of 119 swapped summaries 114 marked | a worded text is marked only where it leaves its document (`results/unattended/`) |
| Does a person's correction carry over? | 200 corrections on 60 documents played through: 50 right proposals and 3 wrong, against 54 and 44 without the check for a decision that speaks against a rule; an accepted rule reaches values without a mark as well | rules are proposed, a person accepts them, every application can be taken back (`src/docket/store/rules.py`, `tests/rules.py`) |
| Where does a field usually stand? | the second opinion learnt from 151 documents keeps 23 ways (12 of 34 places per parliament and field, 11 of 22 fields of the small network), each tried on documents held back | a way is used only where it agrees more often than not (`docs/tests.md`, Learning) |
| Is a person found by the last name alone the right one? | 147 of 148, where the same last name is held for the same affair | no mark on a unique last name; one character off keeps it (`results/unattended/`) |
| Does a field added later reach the documents already read? | the stored documents are asked only that field, one call each, over the stored pages; a decision taken before stays; a second asking sends nothing | the store is asked by the definition, not read again (`tests/ask.py`) |
| How many of 300 documents need no person? | 209 of 299 (69.9 %, 95 % interval 64.5–74.8 %), steady from 50 documents on in a shuffled order; similar in German, French and Italian | – (`results/three-hundred/`) |
| What does a document cost? | with a text layer 6 calls in the median, 7 507 tokens in and 436 out; without one 28 calls; 24.8 s a document on one stream; 179 documents in 133 minutes with about 5 000 calls | one stream with a set pace; more streams for the corpus (`docs/evidence.md` 10, `results/runtime/`) |

## 3 How to repeat them

The tests without a model run with `make test`. The ones with the model need the documents (`data/documents/README.md`)
and a key; `make bench` reads pages as if they had no text layer, `python3 -m docket affairs --model` runs the chain.
Where a run is kept, `docs/tests.md` names its folder under `results/`; where it is not, the entry says what the test
can be repeated with.
