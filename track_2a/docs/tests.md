# Tests

What was tested, what was expected, what came out and what was decided: one entry per test, each with the same five
lines. **Run** names the folder that holds the run itself: the prompt, the answers of the model and the evaluation.
Where no run is kept, the line says so, and what the test can be repeated with. Where no expectation was written down
before a run, the entry states the question it was run for instead.

A test without a call to the model has no prompt to show; its run is the table of what was counted. The documents the
tests ran on are not in the repository (`data/documents/README.md` says where each comes from); in the logs of the
runs the names of people are replaced by made-up ones.

The long record of the measurements behind the decisions is `docs/evidence.md`.

## Reading

### Does the model read a page as its text layer has it?

- **Question:** How close does the model's reading of a page come to the text the PDF carries, when the page is treated
  as if it had no text layer?
- **Test:** The first pages of two shipped documents (`nidau-m185`, `zuerich-219587`), 50 text elements set back to
  unknown and read by Apertus 8B at temperature 0: three elements per strip, then every multi-line element alone; 35
  calls a run, two runs 19 minutes apart on 8 October. The reference is the text layer. The first run also read the
  shipped page without a text layer (13 calls).
- **Result:** Run 1: identical 35, near 12, other 3, empty 0; 8.3 % character errors; the image check flags all 15 that
  are not identical and 26 of the 35 identical. Run 2: 34, 13, 3, 0; 8.4 %; all 16 and 25 of 34. The prompts are the
  same in 35 of 35 calls and 4 answers differ, one of them from a strip whose image has the same size in both runs;
  4 elements are read differently, 1 changes its state. On the page without a text layer 16 elements were read and 11
  flagged; this run has no reference for it.
- **Finding:** The threshold of the image check stays at 0.01, although it flags more right readings here than on the
  ten pages of 6 October. `results/read.md` shows run 2, `docs/evidence.md` quotes run 1.
- **Run:** `results/read-against-text-layer/`

### Can the model say what a page contains?

- **Expectation:** Estimated before the run: the model can probably name the kind of a page, and the same page may get
  another answer in a second run.
- **Test:** 20 first pages of parliamentary documents scaled to 620 pixels in width, one closed question a page: the
  kind of page (one of seven) and yes or no for paragraphs, list, table, photo, plan, logo, signature. Apertus 8B and
  70B at temperature 0, two runs each, 80 calls. Then ten pages of forms, one run per model, 20 calls. The reference
  was set by the assistant from the pages before the answers were read and is open to correction.
- **Result:** Kind of page as the reference: 8B 14 of 20, 70B 17 of 20 (70B answers "text" 18 times). Found, and wrongly
  said yes, by 8B: paragraphs 11 of 13 and 0, list 10 of 10 and 0, logo 10 of 11 and 0, table 0 of 1; by 70B: 13 of
  13 and 1, 8 of 10 and 1, 9 of 11 and 0, 0 of 1. The second run gives the same answer on 19 of 20 pages (8B) and 20
  of 20 (70B). Forms: "form" for 8 of 10 (8B) and 7 of 10 (70B); on the 20 parliamentary pages 8B never says "form",
  70B once. Photo, plan, signature and table occur once each in the reference.
- **Finding:** None taken. The pipeline does not ask the model what a page is; the geometry measures the page itself,
  as decided before this run.
- **Run:** not kept in the repository. Repeatable with 20 first pages of parliamentary documents and ten pages of forms
  at 620 pixels in width and the one closed question named above.

## Geometry

### What does a first cut of a page into objects find on form pages?

- **Question:** With no type, no text and no field named: where do the edges of the objects of a form page run?
- **Test:** No model, no reference. Ten form pages rendered at 300 dpi: the five on which an earlier build of the
  geometry had hit the most text fields and the five on which it had hit the fewest. Ink is smeared across gaps
  of 1.2 character heights horizontally and 0.7 vertically, and what then hangs together is an object; long thin
  runs of ink are taken out as lines beforehand. The character height of a page is the median height of its ink
  blobs. Counted per page and looked at as a picture.
- **Result:** At the first look three things were wrong: frames were drawn filled; dark title bars gave sham
  lines, because light type cuts a bar into long thin strips; grey fields and light lines were not seen, because
  only ink counted (half a page on one form). After that: 3 to 123 lines, 0 to 118 tinted areas and 23 to 151
  objects a page, 1.2 to 1.9 s a page. Still not right on the four pages looked at: an option list with narrow
  line spacing becomes one object per column (seven rows of tick boxes in one box); dotted writing lines come
  out as long thin objects and not as lines; a grey area with light lines in it stays one area; very light or
  coloured parts of a picture are not part of its object; the pages are rendered PDFs, nothing is cropped or
  deskewed.
- **Finding:** Built after the first look: a second mask for everything that is not paper, from which light
  lines and tinted areas are taken; a run of ink with ink above and below along more than half its length is
  part of an area and no line. The five further points were listed for a decision.
- **Run:** not kept in the repository. Repeatable without a model on rendered form pages: lines, tinted areas
  and objects counted per page and drawn into the page image.

### Can size, weight and slant of type be measured on the image, without the model?

- **Question:** Can font size, bold and italic be taken from the ink of a text block before the model has read
  anything?
- **Test:** No model. The first pages of two forms at 300 dpi, 74 text blocks (24 and 50). Per text line: the
  x-height is the band of pixel rows with at least half the ink of the fullest row, and the size is that height
  over 0.52 em; bold from the median horizontal run of ink in that band over the x-height (from 0.23); italic
  from the shear angle at which the columns of ink are sharpest (from 8°). Reference: size and style of each
  block as the PDF names them; a size counts within 1 pt.
- **Result:** Size within 1 pt: 23 of 24 and 48 of 50 blocks. Bold: 24 of 24 and 49 of 50. Italic: 24 of 24 and
  47 of 50. The misses are blocks with two styles in one line, and one short word. Two forms, rendered pages.
- **Finding:** The size is measured on the image, from the profile of the text lines and without the model:
  rendering the text back would need the reading and the typeface, the ink is there before both. Weight and
  slant are not measured in the code as it stands.
- **Run:** not kept in the repository. Repeatable without a model on rendered pages whose PDF names size and
  style of each text: the measured values against the PDF's, block by block.

### How close do font size and colour per element come to what the PDF states?

- **Question:** Measured on the page image for every element with text: how often is the font size within one
  point of the PDF's, and the colour within a small distance?
- **Test:** No model. Every element with text of three sets: form pages and two sets of parliamentary pages
  (2 903, 251 and 265 elements in the result file as kept); an earlier build of the geometry. Size from the
  profile of the text lines, converted to points over the width of the page, which is taken to be A4; text
  colour as what stands out from the most frequent colour in the box. Reference: the size (whole points) and the
  colour the PDF names; a colour counts within 32 of 255 on its furthest channel. Two versions.
- **Result:** Size within 1 pt / colour within 32. Version 1 (the x-height alone, colours on the reduced page):
  forms 83.5 % / 77.2 %, the document sets 57.8 % / 78.9 % and 66.0 % / 96.6 %. Version 2 (the largest measure
  a line yields, tick marks in the line left out, light type on a dark bar measured on the paper, colours at
  full resolution): 84.7 % / 96.8 %, 72.9 % / 94.8 % and 71.3 % / 99.2 %. On the reduced page a thin stroke
  mixes with the paper: #505152 measured for #231f20. More than 2 pt off: 282, 51 and 64 elements, among them a
  plan that is not A4 (27 elements) and a page in A5 (19; 12.4 pt for 9). The result file as kept, written about
  an hour and a half later after further changes to the code, reads 84.7 %, 72.1 % and 74.3 % within 1 pt and
  281, 53 and 57 elements more than 2 pt off.
- **Finding:** Version 2 was kept. The A4 assumption is recorded as a known source of error: on a photograph the
  size of the paper is not known.
- **Run:** not kept in the repository. Repeatable without a model on rendered pages with a text layer: per
  element the measured size and colour against those the PDF names.

## Blocks

### Do the ported rules build the blocks of the shipped documents, with and without the model?

- **Question:** How many blocks does the bridge build from the eight shipped documents without the model and with it,
  and are the records valid against the contract?
- **Test:** Eight shipped documents, 15 pages. Without the model (`tests/blocks.py` in `make test`) the leftover
  elements become paragraphs. With the model (`make bench`, 8 October) the page without a text layer is read and the
  leftover elements of the first pages are sorted, six per call. Compared with the blocks of the Nidau motion in the
  reference run of 6 October, made with an earlier build.
- **Result:** Without the model 275 blocks on 8 October, all eight records valid; the same test counts 272 on
  12 October, after the columns of labels and values came to be paired. With the model 273 blocks in the run of midday
  (56 calls, 21 of them for the chain; not kept) and 273 in the last run of the day: 128 paragraphs, 107 graphics, 16
  sections, 14 lists, 6 label lists, 2 signature blocks, one sorting call a document. Nidau: 14 paragraphs, 5
  sections, 2 label lists, 2 graphics, as in the reference run. 103 of the graphics are inkless fragments of the Basel
  page.
- **Finding:** The ported bridge is the one in use (`src/docket/document/bridge.py`). The fragments are recorded as a
  limit of the geometry on dense pages.
- **Run:** `results/shipped-documents/` (the last run of 8 October; the run of midday is not kept).

### Are the blocks of a run without the model the blocks of a run with it?

- **Question:** Can the affairs of the shipped documents be formed again from the blocks `make test` builds, or do
  they need the blocks of the run with the model?
- **Test:** The blocks `make test` builds for the eight shipped documents against the blocks of the run with the model
  of 10 October.
- **Result:** The same for none of the eight: the run with the model holds blocks sorted as label list, section or
  signature block that the run without it holds as paragraphs.
- **Finding:** The blocks of the run with the model are stored with its answers (`run.json` beside each document, kept
  local); `tests/baseline.py` forms the affairs from them.
- **Run:** not kept in the repository. Repeatable with `make test` and one run of `make bench`, comparing the blocks
  per document.

### How much do pairs of elements side by side take out of the rest?

- **Question:** How many list items and labelled values does code find from two elements standing side by side, and
  what is left over?
- **Test:** 72 documents of the working set in an earlier build, no model. A counter or bullet standing alone with
  text to its right becomes a list item, a label ending in a colon with a value to its right an entry of a label
  list; items following each other become one list. Held against the state before.
- **Result:** 72 of 72 records valid. 42 lists with 96 items, 9 label lists with 13 entries, 23 numbered headings.
  Sections 80 (before 86), paragraphs 398 (435), tables 26, images 187; leftover elements 583 (before 761). In the
  first pass a bullet of a text layer ("://:") counted as a label.
- **Finding:** Built into the bridge (`src/docket/document/bridge.py`); a label has to hold a letter. The distances
  that make a pair and a list were set by the assistant, open.
- **Run:** not kept in the repository. Repeatable with the working set (72 documents, not redistributed) and the
  bridge with and without the pairing.

### Does the model sort the rest better with three kinds than with eight?

- **Question:** What does the model make of the elements code cannot place when it is offered three kinds instead of
  eight?
- **Test:** 338 leftover elements of the 72 first pages of the working set, six per call, Apertus 8B. Variant "eight":
  heading, paragraph, list item, label, entry, signature, margin, footnote. Variant "three": heading, paragraph, list
  item. 86 calls each, 172 calls.
- **Result:** No answer for 12 and 8 elements. Eight: list item 89, label 62, paragraph 47, entry 46, heading 39,
  signature 27, margin 9, footnote 7. Three: list item 123, paragraph 112, heading 90, signature 5 although not
  offered. Against what code sees in the text: short and ending in a colon, answered as label 3 of 17; a page mark as
  margin 3 of 6; over 60 characters as paragraph 3 of 36 (eight) and 8 of 36 (three). A heading set larger than the
  body font: 7 of 38 and 12 of 89. Both variants answered 318 elements, with the same block for 167.
- **Finding:** None taken; whether to keep the sorting or switch it off stayed open. The sorting with eight kinds is
  in the pipeline (`src/docket/document/sorter.py`).
- **Run:** not kept in the repository. Repeatable with the leftover elements of the working set's first pages and the
  two lists of kinds.

### Does a field stand in the same block from document to document?

- **Question:** Can the id of a block say where a field stands, across documents?
- **Test:** 141 documents run on 10 October; per field, the id of the block its value was found in. No model.
- **Result:** The number stands in 96 documents under 10 different block ids (b2 31 times, b1 25, b3 13, b4 10); the
  title under 20, the submitters under 22, the polity under 18.
- **Finding:** A block id is an address within one document only. Across documents a value is asked for by what it is
  and by its value, and its place is the page and the box of its block (`src/docket/store/rows.py`).
- **Run:** not kept in the repository. Repeatable by counting the block ids per field over the stored field reports
  of a run.

### Does a block carry the values of one field only?

- **Question:** Can what a value is be noted at the block it stands in?
- **Test:** The 60 documents of the reference sample in the run of 10 October: the values with a place, per block.
  No model.
- **Result:** 1 202 values with a place in 433 blocks. 166 blocks carry values of more than one field; they hold 846
  of the values (70 %). 212 parts of answers have no block.
- **Finding:** What a value is, is noted at the value, one row per value (`src/docket/store/rows.py`), not at the
  block.
- **Run:** not kept in the repository. Repeatable by counting values per block over the stored field reports of a
  run.

### Does pairing a column of labels with the column of values repair the kickoff example?

- **Question:** Do the values of the kickoff example come out as printed once its header is built as lists of label
  and value?
- **Test:** `nidau-m185` with one change in the working tree: the text layer keeps the lines of an element, and a
  column of labels and the column beside it become one list, line by line. `make test`, then one run with the model,
  6 calls.
- **Result:** `make test`: 330 ok, none failed. The record holds three lists of label and value (four, two and four
  pairs) and 20 blocks instead of 23. The answers: number "/ 2", type "Motion", a surname as the place,
  "Parlamentarischer Vorstoss" as the parliament. Against the four values OpenParlData holds for the affair, 2 of 4
  are the same, as in the run before the change; the two runs give two different wrong readings.
- **Finding:** The pairing was taken out again and built in later that night together with a rule that learns which
  label a field is read from (`src/docket/text/layer.py`, `src/docket/document/bridge.py`, `src/docket/store/rules.py`).
  A number printed as two words, a prefix and a figure, is found on the page by the parliament's form
  (`src/docket/affair/identity.py`).
- **Run:** `results/kickoff-example/` (`calls/run-2-columns-paired/`)

## Document kinds

### Is the kind of a document told from its first page?

- **Question:** Does a rule over the words of the first page give a shipped document the kind noted for it?
- **Test:** Eight shipped documents. Without the model `tests/kinds.py`: the three largest texts of page 1, the section
  names, the type labels and a signature block, the first kind of the list that fits. With the model the run of
  `make bench` of 8 October, where the kind is set after the fields. The reference is the kind in each
  `document.json`, set by the assistant on 8 October.
- **Result:** Without the model 6 of 8, on 8 October and again on 12 October: the page without a text layer has no
  words before it is read, and Lugano's agenda has no word of the list in its headline. With the model 7 of 8: the
  scan gets its kind after the reading, from the section "Text"; Lugano stays without one.
- **Finding:** Seven kinds with their words in `data/knowledge/kinds.json`; the order of the list is the rule
  (`src/docket/document/kind.py`). Without a word a document gets no kind, and a kind is marked for a person.
- **Run:** `results/shipped-documents/`

### How often does a heading announce the answer of the executive?

- **Question:** Where in a document does the answer of the executive begin, and how many documents say so in a
  heading?
- **Test:** The 211 records stored from the runs of 10 October, no model: headings that announce an answer, and
  sentences that hold a request or a decision of the executive, each found with a list of words set by the assistant
  for the count.
- **Result:** Kinds in the run: submission 113, none 45, answer 26, minutes 15, bill 5, committee report 4, act 3. 169
  documents have at least one heading, 497 headings. A heading announces an answer in 11 documents (German 2, French
  7, Italian 2); the run holds 5 of them as an answer, 2 as a submission, 4 without a kind, and the German section
  names of the prior knowledge hit 2 of the 11. Of the 26 answers, 5 have such a heading and 11 no heading at all. A
  request or decision: the list hits a sentence in 10 of 32 answer documents, 6 of them are one. After the build 10
  of the 211 documents get their answer as a part of its own.
- **Finding:** From such a heading on, the document's text is kept as its answer (`src/docket/document/response.py`,
  `tests/response.py`); the announcing words are prior knowledge for all parliaments (`data/knowledge/sections.json`),
  set by the assistant, open. Nothing in it names a parliament or a kind of document. A field for the request or
  decision was not built.
- **Run:** not kept in the repository. Repeatable with the stored records of a run and the two lists of words.

## Fields

### Do the answers of the model land in the fields of the shipped documents?

- **Expectation:** A run with the model over the eight documents stays under five minutes, the limit set for checks
  with the model before the filling was ported. For the values no target was written down; the Nidau affair of the
  reference run of 6 October served as comparison.
- **Test:** Eight shipped documents, 23 fields, `make bench` with Apertus 8B at temperature 0: the fields asked in
  bundles of up to six, every answer placed by code. Three runs on 8 October in the afternoon with two additions to
  the reading of an answer between them, and the last run of the day.
- **Result:** Runs 1 to 3: 61, 61 and 60 calls, 4.5 minutes each, all records valid. Run 3: 184 cells, on the page 89,
  block from the model 6, not on the page 17, empty 71, too short 1; 123 places, 113 literal, 2 derived, 3 cited,
  5 composed; 23 marked for a person. Three cells changed their state between the runs. Runs 1 and 2 left remains of
  block ids in list values, once "[b" as a keyword. Nidau: 43 of 48 values as the reference run. The last run, 60
  calls: on the page 86, block from the model 6, not on the page 20, empty 70, missing 1, too short 1; 132 places,
  115 literal, 9 derived, 3 cited, 5 composed; 29 marked. The files of runs 1 to 3 are lost.
- **Finding:** A bracket with several block ids and a list of ids left open at the end of a line come off the value
  (`src/docket/fields/filler.py`), the one change against the rules of the earlier build.
- **Run:** `results/shipped-documents/` (the last run of 8 October; runs 1 to 3 are not kept).

### Which values of the kickoff example come out as the page prints them?

- **Question:** What does the code of 11 October read from the example of the challenge, and what is wrong in it?
- **Test:** `nidau-m185`, two pages, one run with Apertus 8B at temperature 0, 6 calls: one sorting call, five for the
  fields. Held against what the first page prints under its labels and against the four values OpenParlData holds for
  the affair (number, title, type, begin date), fetched once for the tests.
- **Result:** Against OpenParlData 2 of 4: title and date. As printed: title, date, the ten co-signers, addressee,
  parliament and department. Not as printed: the number (the file reference instead of "M 185"), the type ("Motion",
  the page ticks "Richtlinienmotion"), the two authors (one value holds a name, a party and the surname of the other
  author, the other a first name and a party), the party with a surname in it, a part of a name as "on behalf of",
  the title as a keyword, two dates in one value. The header of the page is a column of labels and a column of
  values, each one element; such a first page was counted in 3 of 204 stored documents beside this one.
- **Finding:** Where a document prints a label, the value can be taken from the label; which label belongs to which
  field is learnt from what people change, not written into the code (`src/docket/store/rules.py`). No rule for a
  single parliament or kind of document is built (decided on 11 October).
- **Run:** `results/kickoff-example/` (`calls/run-1/`)

### Can a label before the value, or the place on the page, say where a field stands?

- **Question:** Without the model, what tells code where the value of a field stands: the label printed before it, or
  where on the page it usually is?
- **Test:** 141 documents run on 10 October, no model. First the label in the same block, in the block before or to
  the left. Then the place: page 1 or later, a tenth of the height, a quarter of the width. For each document the
  usual place is taken from the other documents of its parliament, where it holds for half of them, and what stands
  there is held against the model's value, which is no reference.
- **Result:** A label in the same block: number 12 of 96 values, title 14 of 115, type 28 of 115, date 8 of 70. Learnt
  from the other documents of the parliament, no label fits in 282 cases where the model has a value, and the same
  value comes out twice. The place, for the number: the same value as the model 38, nothing at the place 18, another
  value 4, a value where the model has none 12. Title: no place holds for half in 40, the same value 21, nothing 16,
  another 5. Date: no place 43, another value 15. Submitters: no place holds for half in 63.
- **Finding:** A label in or beside the block was not taken as the anchor of a field. The place went on to the trial
  of the usual place per parliament and from there into the second opinion (`src/docket/fields/second.py`).
- **Run:** not kept in the repository. Repeatable with the stored field reports and blocks of a run.

### Is the usual place of a field in a parliament's documents worth a second look at the model's value?

- **Question:** How often is what stands at the usual place of a field the value OpenParlData holds, and from which
  share of documents on does a place count as usual?
- **Test:** 151 documents of Basel-Stadt, Vaud and Ticino run on 10 October, no model. Per parliament and field the
  most frequent place in the other documents (a grid of 10 by 4, at least 3 documents), tried from a share of 30, 50
  and 70 %. The reference is number, title, harmonised type and date as OpenParlData holds them, fetched for the test:
  604 cases.
- **Result:** The model alone is right in 278 of the 604 and has no value in 234. From 30 %: the place gives a value
  in 225 cases, 161 right; where the model has none, 53 right and 12 wrong. From 50 %: 159 values, 114 right; 19 and
  5. From 70 %: 48 values, 42 right; 10 and 0. For the date in Ticino the place gives 29 values and none is right;
  the model has 45 of 60. The figures for "both agree" in this trial counted a case as agreeing when both were right,
  which a run cannot see; they are not quoted.
- **Finding:** Built as one of two ways of the second opinion (`src/docket/fields/second.py`, `tests/second.py`). No
  share is set as a constant: each way is tried on documents held back and kept where agreeing outweighs disagreeing
  (decided on 10 October). Grid and minimum of documents were set by the assistant, open.
- **Run:** not kept in the repository. Repeatable with the stored runs of a parliament's documents and the values
  OpenParlData holds for the same affairs.

### What do the points left open still change?

- **Question:** Which of the open points on parliament, number, events, summary, keywords and names still change a
  value with the code of 11 October?
- **Test:** The 211 documents of the runs of 10 October counted again with the code of 11 October, no model. For a
  year taken as the number two attempts: skip figures that look like a year when searching the page, or do not search
  the page at all for forms of digits only.
- **Result:** The run finds the parliament itself for 120 of 211 documents, right for 114. Skipping years changes 1 of
  203 documents, which then takes the next wrong figure; not searching turns 3 wrong numbers into weak keys and loses
  1 right one (83 to 82 the same as OpenParlData). Events: 137 documents with an event or a date, as many names as
  dates in 82, more names in 54. Summary: answered for all 211, a place for 84. Keywords: 250 in 79 documents, where
  none of the 60 documents of the reference sample prints any. 18 of 1 646 names hold a comma or a bracket; of 172
  documents with submitters 54 name a party, 19 of them with unlike numbers of parties and names.
- **Finding:** A summary keeps the block the model names, else the head of the document, marked as composed and for a
  person (`src/docket/fields/filler.py`; decided on 11 October). Neither attempt on the year was built.
- **Run:** not kept in the repository. Repeatable with the stored field reports and records of a run.

### Can code decide where a value belongs that the run set in two fields?

- **Question:** When the run sets one value in two fields of a document, can a rule in the code tell which of the two
  it belongs to?
- **Test:** The stored field reports of a run of 12 October over the 60 documents of the reference set, against the
  draft reference; no call. Three rules: the value stays in the field asked earlier; the direction is set per pair of
  fields on these same documents; nothing is removed and both places get a mark for a person.
- **Result:** The same value stood in two fields 328 times, in 48 of 60 documents; by the reference 109 belong to the
  earlier field only, 138 to the later one only, 19 to both, 62 to neither. Authors and co-signers share 155 values:
  75 belong to the authors, 74 to the co-signers. Kept in the earlier field: 160 wrong and 120 right values go, 671
  of 1 200 fields right before and 672 after (without the kind of document). The direction per pair, set on these
  documents: 701. Marked: 274 wrong and 236 right values get a mark; of the 1 207 values without a mark 674 are
  wrong.
- **Finding:** None built: no rule in the code. The fields are asked differently instead, see the next entry.
- **Run:** `results/asking/result.md`

### Do the contributor fields come out right when they are asked in one call?

- **Question:** Authors, party, in whose name and co-signers were asked in three calls, two on the first pages and one
  on the whole document. Does the model keep a name to one of them when it sees the four together?
- **Test:** The 60 documents of the reference set. First the answers alone: the four fields in one call over the whole
  document, with the questions as they are and with questions worded so that a name can stand in one field only, 120
  calls. Then the pipeline with such fields in a call of their own, 655 calls, against the run before with 583.
- **Result:** Answers, fields right of 240 / the same entry in more than one of the four / filled where nothing
  belongs: three calls 95 / 169 / 102; one call 153 / 43 / 45; one call with the other wording 159 / 16 / 30, with no
  right value of "on behalf of" left. Through the pipeline: 728 of 1 260 fields right, 704 before; co-signers 44
  against 15, on behalf of 45 against 25; authors 33 against 38, related affairs 35 against 45, addressee 19 against
  25. 10.9 calls a document against 9.7, 17 946 tokens in against 14 627. In documents with one author and many
  co-signers the model puts every name under the authors, with either wording. Between two runs of one build 8 of
  the 1 260 fields changed that day.
- **Finding:** A field names under `together` the group it is asked with (`data/schema/fields.json`); the fields of a
  group share a call of their own (`bundles` in `src/docket/fields/filler.py`, `tests/bundles.py`). The questions
  keep their wording. The three fields that got worse each stand first in their call since the change: next entry.
- **Run:** `results/asking/`

### Does the first field of a call draw a value?

- **Question:** Is the field that stands first in a call filled more often than the document gives reason for, and
  does a line before it that is no field take that away?
- **Test:** Three calls of each of the 60 documents, answers alone: as built, with the order turned (the first field
  last), and with one line in front that asks for the language of the document; 360 calls. Then the pipeline with
  that line before the first field of every call and with the keywords asked on a condition (next entry), 646 calls.
- **Result:** Order turned: the party, now first, right in 17 of 60 against 36 and filled where nothing belongs 38
  times against 21; acts and references 2 against 11; place 25 against 31; the authors, no longer first, 42 against
  33, related affairs 39 against 32. With the leading line: authors 41, addressee 25 against 21, related affairs 47,
  dates of events 19 against 13; keywords 2 against 29, filled in 58 of 60 documents; all 13 fields 377 of 780
  against 374. Through the pipeline with both changes: 788 of 1 260 fields right (62.5 %), against 704 (55.9 %)
  before the three changes and 728 with the calls alone. Filled where nothing belongs 119 against 179, missing 173
  against 198, partly or wrong 180 against 179. Co-signers 42 against 15, on behalf of 41 against 25, title 41
  against 33, authors 42 against 38; place 30 against 33, acts and references 14 against 17, party 31 against 33,
  version 56 against 58. Values without a mark 866 against 1 205, of these not in the reference 386 against 671.
  10.8 calls a document. The days of events are counted as they stand in the record. The reference is a draft, and
  each state was run once.
- **Finding:** Every call starts with a line that is no field and whose answer is read past; it is kept in the fields
  file (`$task.lead` in `data/schema/fields.json`, `prompt` in `src/docket/fields/filler.py`, `tests/bundles.py`).
  Which question stands there was not varied: the language of the document, set by the assistant, open.
- **Run:** `results/asking/`

### Are keywords set where the document prints none?

- **Question:** How often does the run set keywords for a document that prints none, and does asking only where a
  word for keywords stands on the pages take them away?
- **Test:** The 60 documents of the reference set, none of which prints keywords by the draft reference: two runs of
  12 October counted, no call; the call for related affairs, references and events once more without the line for
  the keywords, 120 calls; then the pipeline as in the entry before.
- **Result:** The runs set keywords in 27 and in 24 of the 60 documents; on none of the 60 one of the words for
  keywords stands. The call without the line for the keywords: 62 of 240 fields right against 59; with the leading
  line as well 83. Through the pipeline: the keywords are asked in none of the 60 documents and are rightly empty in
  60 of 60, against 33. A document that prints keywords, under a word of the list or under another one, is not in
  the sample; that case was not measured.
- **Finding:** The keywords are asked only where one of eleven words for them stands on the pages (`when` in
  `data/schema/fields.json`; the list, in German, French, Italian and English, set by the assistant, open).
- **Run:** `results/asking/`

### Does the model tell the bodies of a document apart when each is asked by its role?

- **Question:** Addressee, place, parliament and polity were asked in a few words each ("to whom it is addressed",
  "place where it was submitted"). Does a question that says what the body is keep the values in their fields?
- **Test:** The 60 documents of the reference set. First the answers alone: the stored call with the four questions
  in two other wordings, one that says what is not meant and one that describes the role of each body with examples
  in three languages, 120 calls. Then the pipeline with the second wording, in the run of the next entry.
- **Result:** Answers, fields right of 240: as built 140, with exclusions 149, by role 163; addressee 26, 35 and 44;
  place 30, 36 and 33; parliament 37, 38 and 42; polity 47, 40 and 44. Through the pipeline: addressee 47 of 60
  against 24, parliament 50 against 42, place 34 against 30, polity 44 against 45. A place is still set in 22
  documents where none belongs, 26 before. Each wording was run once.
- **Finding:** The four questions describe the role of the body, with examples (`data/schema/fields.json`); the
  wordings were set by the assistant, open.
- **Run:** `results/asking/`

### Does every event keep its own day?

- **Question:** Events were asked as two lists, the names and the days, to be kept in the same order. Do name and
  day stay together when they are asked in one line, entry by entry?
- **Test:** The 60 documents of the reference set. The answers alone, with the two lists reworded and with one line
  of pairs, 120 calls; the pipeline with the pairs, 656 calls; the stored answers of that run through the changed
  code, no call; the pipeline once more, 643 calls.
- **Result:** Answers: of the 106 days of events in the reference the model names 54 as built, 64 with the lists
  reworded, 81 with pairs; names of more than four words 63 of 92, 37 of 108, 40 of 118. In the records of the run
  before, every event of a document with several days carried the first of them, in 9 of 9 such documents. First
  run with pairs: of 102 days 47 found no place on the page, 37 of them written out there with a French or Italian
  name of the month; of 112 names 65 found no place. After the changes below: the days of events right in 20 of 60
  documents against 10, the names in 9 against 3; 841 of 1 260 fields right (66.7 %) against 788 (62.5 %); fewer
  fields to set right in 37 documents, more in 8. With French and Italian words in its condition the session was
  asked in 23 documents instead of 11 and came out right in 38 instead of 41. The name of an event is the one of the
  reference in 9 of 60 documents; the reference is a draft.
- **Finding:** A list field names under `paired` the field whose value starts each of its entries; an entry stands
  only with both placed (`src/docket/fields/filler.py`, `tests/settle.py`). A day written out is read and found in
  German, French, Italian and English (`src/docket/fields/placer.py`). What happened takes the block of its day as
  the block named for it, marked for a person. The words for the session stay German; the department is asked also
  where a French or Italian word for it stands (the lists set by the assistant, open).
- **Run:** `results/asking/`

### Does a document come through with every field right?

- **Question:** How many documents have every field right, so that nobody has to set anything right in them, and
  what keeps the others back?
- **Test:** The 60 documents of the reference set, counted per document instead of per field, no call. Three ways
  for the pipeline to tell by itself which fields are right: the mark it sets for a person, the same value in a
  second run, and the model asked to check the values set, 60 calls. The place read by code from a line of a place
  and a day, no call. Then the pipeline with that and with a party kept apart from the submitters and the bodies,
  643 calls.
- **Result:** Before: no document with all 21 fields right; 3 to 14 fields a document are not, 7 in the middle. The
  model sets a value where the document prints nothing in 111 fields of 49 documents (party 24, place 22, on behalf
  of 14); the names of events, their days and the acts and references differ from the reference in 51, 40 and 46
  documents. Fields without a mark are right in 69 %, the same value in a second run in 70 %, a value the model
  confirms in 64 %: none of the three separates. The place by code is the one of the reference in 56 of 60 documents,
  the model's in 34. Through the pipeline: 883 of 1 260 fields right (70.1 %) against 841; the place 56 against 34,
  the party 41 against 31; filled where nothing belongs 75 against 111. All 21 fields right: still no document.
  Leaving aside the three lists from the running text: 2 documents with every field right against none, 9 against 4
  with at most one field not right, 17 against 10 with at most two. A person has fewer fields to set right in 38
  documents, more in 6. The reference is a draft.
- **Finding:** A field with `reader` is read by code and not asked: the place is what stands before the day in a line
  of a place and a day, with no list of places behind it (`before_day` in `src/docket/fields/rules.py`). A field with
  `apart` leaves out a value that already stands under one of the fields named there (`keep_apart`). A bare no and a
  lone bracket are no value (`tests/settle.py`). The three lists were left aside by the assistant, open.
- **Run:** `results/asking/`

### Does the model know what a document is where the words of the first page do not?

- **Question:** The kind of a document, its role in the affair, was set by code from the words of the first page.
  Does the model name it more often as in the reference, and does it help to hold the two against each other?
- **Test:** The 60 documents of the reference set. First the answers alone: the model asked over the first pages
  for one kind out of the list of the knowledge file, with a sentence for each, 60 calls. Then the pipeline with
  that question and the words held against it, 703 calls.
- **Result:** Answers: the model right in 51 of 60 documents, the words in 36; both the same in 33, right in 31 of
  these. The words mostly take an answer for the submission it answers. Through the pipeline: the kind right in 56
  of 60 documents against 36; it stands without a mark in 35, right in 34 of them, and with a mark in 25, right in
  22. 903 of 1 260 fields right (71.7 %) against 883. Leaving aside the three lists from the running text: 3
  documents with every field right against 2, 10 against 9 with at most one field not right, 21 against 17 with at
  most two. One call more a document. The reference is a draft, each state was run once.
- **Finding:** The task holds questions about the document itself beside the fields (`$task.ask` in
  `data/schema/fields.json`): the answer is one word of a closed list, no value of the record, and stands on no page
  (`src/docket/fields/filler.py`). The same kind from the words and from the model stands without a mark; where
  they differ or only one says anything, a person looks, and the model's kind stands (`add_kind` in
  `src/docket/pipeline.py`, `tests/settle.py`).
- **Run:** `results/asking/`

### Does the model give the subject of an affair as its title when asked for it?

- **Question:** Asked for "the title of the affair", the model mostly gave the line that names the kind of affair.
  Does it give the subject when the question says so, and is a date found that is written with slashes or stands
  on a later page only?
- **Test:** The 60 documents of the reference set. Three wordings of the title question on the stored first call of
  each document, 180 calls, answers alone. Then the pipeline with the third wording, the day with slashes, the date
  from the line of a place and a day where the model gives none, and names set apart by a dash with spaces, 696
  calls.
- **Result:** Answers: the title right in 37 of 60 as built, in 45, 51 and 49 with the three wordings; the four
  fields of that call together 172 of 240 as built, 189, 185 and 190. Through the pipeline: the title right in 49
  of 60 documents against 40, the date of submission in 45 against 40, the type as printed in 53 against 50; 922 of
  1 260 fields right (73.2 %) against 903. Leaving aside the three lists from the running text: 3 documents with
  every field right as before, 12 against 10 with at most one field not right, 21 as before with at most two. A
  person has fewer fields to set right in 19 documents, more in 6. The reference is a draft, each state was run once.
- **Finding:** The title is asked as the subject of the affair as printed, the line that says what it is about,
  without the kind, the number and the date (`data/schema/fields.json`; the wording set by the assistant, open). A day
  with slashes is read and found (`src/docket/fields/placer.py`). Names set apart by a dash with spaces are taken
  one by one (`tests/settle.py`). The date from the line the document is dated with, where the model gives none,
  was built with this step and taken out again the same day: on other documents the day of that line is not the
  date of submission (next entry).
- **Run:** `results/asking/`

### Do the changes hold on documents they were not made on?

- **Question:** Every change of 12 and 13 October was made and measured on the same 60 documents. Do they help on
  documents they never saw, and does a rule of code made on the 60 read other documents rightly?
- **Test:** 60 other documents, 20 each in German, French and Italian, from 40 parliaments, 26 of them from 23
  parliaments of which the reference set holds no document, chosen by a rule fixed before any result. Through the
  pipeline as it was before the changes and as it is after them, 1 642 and 1 755 calls. The reference is what
  OpenParlData holds for the affair: number, title, type and date. Before the second run, the rules that need no
  model on the stored blocks of 151 further documents of three parliaments, no call.
- **Result:** As OpenParlData, of 240 values: 107 before, 138 after; the title 27 and 41, the type 35 and 43, the
  date 26 and 33, the number 19 and 21. On the 26 documents of parliaments the reference set does not hold: 60 and
  68 of 104. More of the four fields right in 23 documents, fewer in 2. All four as OpenParlData in 7 documents
  before and after: the number OpenParlData holds stands in the text of 21 of the 60 documents (the pipeline has it
  in 17 of these), its date in 36 (30). On the 151 documents the date taken from the line of a place and a day is
  the date of OpenParlData in 2 of 26 lines, and 5 of the 26 places read from that line were none (an abbreviation,
  a file reference, the end of the sentence before); on the documents of the run, a day of the week.
- **Finding:** The date from that line was taken out again. The place from it now asks for the form of a name
  (small letters, no digits) and for a line that stands by itself, and leaves the days of the week aside
  (`src/docket/fields/rules.py`, `src/docket/fields/placer.py`, `tests/settle.py`): 59 lines on the three sets
  after that, each a place. On the 60 documents of the reference set the two corrections give the place right in 57
  instead of 56 and the date in 41 instead of 45, counted on the stored run.
- **Run:** `results/unseen/`

### How many documents run through without a mark for a person?

- **Question:** A value carries a mark where a person should look. How many documents carry none, what do the
  marks hang on, and can a text the model worded be held against its document instead of being marked every time?
- **Test:** The 60 documents of the reference set and the 60 other documents of the entry before, counted per
  document. The check of a worded text on the stored summaries of both sets, with the summary of another document
  put in its place, no call. Then the pipeline, 697 calls.
- **Result:** Before: no document without a mark; the summary marked in 60 of 60, an event in 28, the kind in 25. A
  summary shares 0.39 to 0.93 of its words with its document, 0.71 in the middle; the summary of another document
  0.18 in the middle. Held against its document, no summary of the reference set is marked and 1 of the other 60; a
  summary put in the place of another is marked in 114 of 119. Through the pipeline: 13 of 60 documents without a
  mark. With the kind marked only where the words of the page say another kind, and the name of an event held
  against the document, counted on the stored runs: 30 of 60, and 19 of the 60 other documents. Of the 30, 3 hold no
  value that the draft reference does not hold under its field; 11 hold one such field. In the same run the day an
  affair was submitted became its first event: the days of events right in 33 of 60 documents against 20, 939 of
  1 260 fields against 922.
- **Finding:** A text the model worded is marked only where it leaves its document: less than 0.4 of its words
  stand there (set by the assistant, open), another language, or a number the document does not hold (`unsound` in
  `src/docket/fields/rules.py`). The kind was marked where the words of the page say another kind, or stand alone
  (`add_kind` in `src/docket/pipeline.py`); the first of the two was dropped the same day, see the next
  entry. The date of submission gives the first event of the affair (`entry` in
  `data/schema/fields.json`, `add_entries`; `tests/settle.py`).
- **Run:** `results/unattended/`

### Does a value inside a longer word count as found, and do the rules of code hold on other documents?

- **Question:** Is a value placed as literal that only stands inside a longer word of the page? Do the rules that
  leave a value out where it stands under another field hold on documents they were not made on? And is a mark on
  the kind worth what it holds back?
- **Test:** The stored runs of the reference set and of the 60 other documents put through the code again with the
  answers as stored, no call; the replay gives a stored run back in 1 440 of 1 440 fields where the code is unchanged.
- **Result:** 58 of 1 451 values placed as literal on the 120 documents stood inside a longer word or across the
  ends of words ("Parlament" in "Parlamentarischer Vorstoss", "1" in "12"). On the other documents the rules leave
  out 9 places of a session that are the polity or the place again, 5 names of a session that are the parliament or
  the addressee, 4 days and places without a session, 5 parties and 8 values under on behalf of that are the
  submitter or a body of the document; a first form of the rule took "CVP Glarus" for the polity Glarus. The mark on
  the kind against the words of the page held 14 documents of the reference set to find 2 wrong kinds. Documents
  without a mark after all of it: 38 of 60 on the reference set, 30 of 60 on the other documents (30 and 19 before).
  On the reference set 266 fields not as in the reference against 273; of the 38 documents, 5 hold no value the
  reference does not hold. On the other documents, 17 of the 30 hold none of the four fields of OpenParlData in
  another value.
- **Finding:** A value stands on the page as whole words, a word may go on with an ending of its own (`whole` in
  `src/docket/fields/placer.py`). A value is left out where it is the value of a field named under `apart` or a part
  of it, not where it holds that value and more; a field with `needs` has no value without the field named
  (`keep_apart` in `src/docket/fields/rules.py`, `data/schema/fields.json`). The model's kind stands without a mark;
  a mark only where the model names none (`add_kind` in `src/docket/pipeline.py`).
- **Run:** `results/unattended/result.md`

### Is the date of submission read rightly from a document that is no submission?

- **Question:** Asked for the day an affair was submitted, which day does the model give in an answer, a report or
  minutes?
- **Test:** The stored runs of the reference set and of the 60 other documents, the date by the kind the model
  names for the document, against the draft reference and against the date OpenParlData holds; then the replay
  with the date read from submissions only. No call.
- **Result:** Reference set: the date right in 31 of 33 submissions where one is set, in 10 of 19 documents of
  another kind; in 6 of these the reference holds no date of submission. Other documents: as OpenParlData in 26 of
  32 submissions, in 7 of 18 documents of another kind. With the date read from the submission only: on the other
  documents 32 values that differ from OpenParlData against 42, 131 as OpenParlData against 138; 30 documents
  without a mark as before, 19 of them with none of the four fields in another value against 17. On the reference
  set 40 documents without a mark against 38, 124 fields with a value the reference does not hold against 136, 270
  fields not as in the reference against 266. In the same replay a word that stands for further co-signers
  ("cofirmatari", "und Mit.") was an entry among the submitters in 3 and 5 documents.
- **Finding:** A field with `kinds` is read from documents of these kinds only: the date of submission from the
  submission itself; where the model names no kind the value stays (`keep_kinds` in
  `src/docket/fields/rules.py`, `data/schema/fields.json`). A word that stands for further co-signers is no entry
  of a list of persons and is left off behind a name (`items` in `src/docket/fields/filler.py`, `tests/settle.py`).
- **Run:** `results/unattended/result.md`

### Who signs an answer: are co-signers and "on behalf of" read rightly from a document that is no submission?

- **Question:** Do the co-signers and the group in whose name an affair was submitted hold when they are read from
  an answer, a report or minutes? Does the model keep the submitters out of the co-signers, and what does it give
  for the affairs a text refers to?
- **Test:** The stored runs of the reference set and of the 60 other documents, by the kind the model names for
  the document; then the replay with the two fields read from submissions only, the submitters kept out of the
  co-signers, and a number of an affair that holds a digit and is more than one digit. No call.
- **Result:** Reference set, documents of another kind than a submission: co-signers set in 4, none holds; on
  behalf of set in 9, 2 hold; the reference holds neither for any such document. The submitters stood among the
  co-signers once more in 3 documents. One document lists the numbers 1 to 9 of its points as affairs referred to.
  On the other documents the rules leave out 22 co-signers that stand under the submitters, 5 co-signers and 6
  values under on behalf of in answers and reports, 9 single digits, and 2 numbers of affairs without a digit.
  After that, reference set: co-signers as in the reference in 51 of 60 documents against 45, on behalf of in 49
  against 46, 101 fields with a value the reference does not hold against 116, 8 of the 40 documents without a
  mark with no such value against 6; no field right in fewer documents than before. Other documents: 31 without a
  mark against 30, 21 of them with none of the four fields in another value against 19. A rule that a submitter is
  not the polity itself left out 2 values on the reference set and none on the other documents.
- **Finding:** Co-signers and on behalf of are read from the submission only (`kinds`), and who submitted is no
  co-signer again (`apart`), both in `data/schema/fields.json`. The number of an affair holds a digit and is more
  than one digit by itself (`items` in `src/docket/fields/filler.py`, `tests/settle.py`). The rule on the polity
  was not built.
- **Run:** `results/unattended/result.md`

### Does code find the place of every value the model names?

- **Question:** For every value the model reads off a first page: does code find where it stands on the page,
  and do the filled results fit the data contract?
- **Test:** 72 parliamentary documents, the first page as a picture of text; the small model (8B) asked for
  number, title, type and date among 4, 8, 16 and 32 fields per call. Then, without a further call, code looks
  for each named value on the page: word for word in one block, only in a single line outside the blocks, spread
  over several elements, or not on the page; a date counts in any notation of the same day. A value goes into
  the result only with a block as its place.
- **Result:** At 4 fields per call, of 251 named values: 121 in a block, 102 only in a line outside the blocks,
  4 over several elements, 24 not on the page. At 8, 16 and 32 fields: 126 / 101 / 4 / 26, 122 / 93 / 4 / 27 and
  121 / 90 / 3 / 27. All 72 results fit the contract at every bundle size. A first count was wrong and is
  replaced by these numbers: the pages of the 5 documents with several pages had been sorted so that page 1 came
  last. A value that stands on the page word for word is not thereby in the right field; that was not measured.
- **Finding:** In that build a value is written only with the place it was found at; what stands in no block is
  not written. The single lines left outside the blocks were given to the model to sort as the next step.
- **Run:** not kept in the repository. Repeatable with first pages of documents as a picture of text with their
  blocks, the answers of the model for the four fields, and the search for each value on the page.

## Identity and persons

### Do the shipped documents get the key of their affair?

- **Question:** Does the key formed from the read number equal the key of the number OpenParlData holds for the
  affair?
- **Test:** Eight shipped documents, five of them with a known affair, `python3 -m docket affairs --model` on
  8 October: the read number with the parliament from the read names of place and parliament, 97 named bodies, 88
  with number forms; where the read number does not fit the form, the first page is searched. The numbers of
  OpenParlData were fetched once for the tests.
- **Result:** 4 of 5 in the run of 14:52 (61 calls, not kept) and in the last run of the day: Basel, Wettingen and
  Zürich from the read number, Aargau from the page. Nidau gets a key from its file reference, since the page prints
  "M 185" as two words. Of the three without a known affair one gets a year as its key and two a weak key from place
  and date. Eight documents give eight affairs. Since 11 October a key also names the parliament, and the keys in
  `results/documents.md` are no longer those the code forms.
- **Finding:** The ported identity is the one in use (`src/docket/affair/identity.py`). That a place name alone does
  not tell a canton from its capital among 97 bodies was left open on that day.
- **Run:** `results/shipped-documents/` (the last run of 8 October; the run of 14:52 is not kept).

### What kind of names does the register not find?

- **Question:** From how many documents on should a printed name nobody carries be taken into the register?
- **Test:** The read names without a person in the register of their parliament, counted on 10 October: 150 finds,
  147 distinct per parliament. No model.
- **Result:** 144 occur in one affair, 3 in two, none in three. Many are not clean names: a name with a place behind a
  comma, a name with a party in brackets, an office, a block id. With the bracket taken off and the text cut after
  the comma, 23 find their person.
- **Finding:** A name is learnt only when it stands literally in the document, has at least two words and names no
  body; it is kept as a candidate and taken in from the third document on
  (`src/docket/store/register.py`).
- **Run:** not kept in the repository. Repeatable with the read names of a run and the persons of the parliaments.

### How many read names get a person, and how many are learnt?

- **Question:** What does looking up and learning give over all documents of the large run, without the model?
- **Test:** The affairs formed again from the 151 stored documents of Basel-Stadt, Vaud and Ticino, the parliament
  taken from the file name, the register loaded from OpenParlData's export of persons for the test.
- **Result:** 1 120 read names of contributors: exact 670, by the last name 173, one character off 7, several persons
  fit 36, no person 234; 845 carry the id of a person. The register holds 72 candidates, 6 of them seen in two
  documents, and 5 learnt names, each from three documents. The parliament read from the document agrees with the
  file name for 68 of 151.
- **Finding:** None taken.
- **Run:** not kept in the repository. Repeatable with the stored field reports of a run and the persons of the
  parliaments.

### Are the persons of a document found again in its stored blocks?

- **Question:** When a kind of value is added later, can documents read before be searched for it without the model?
- **Test:** The person as the stand-in for such a kind: the stored blocks of 125 documents searched for the names of
  the register of their parliament, no model. The reference is the authors OpenParlData holds for the same affair,
  fetched for the test.
- **Result:** 108 documents with authors in the register, 217 authors. As the run does it (names from the model, then
  the register) 110 are found; searching the blocks for full names 112; with last names only one person of the
  parliament carries 191; by no way 26. Ticino: 42, 42 and 118 of 140. 7 milliseconds a document. The search finds
  1 104 further persons of the register, 917 of them in 27 documents of Vaud.
- **Finding:** None taken. Whether the place separates author from co-signer could not be counted: OpenParlData holds
  no co-signers for the affairs of these three parliaments.
- **Run:** not kept in the repository. Repeatable with the stored blocks of a run, the persons of the parliaments and
  the authors OpenParlData holds.

### Can a person named as author and as co-signer be put in one place only?

- **Question:** Which rule puts a name the run holds under both fields where the document has it?
- **Test:** Stored answers, no model. Nine ways, among them: as today; a double name is an author; a word for the role
  before the name; the block of the first author is the block of the authors. On the 60 documents of the reference
  sample, 163 double names in 25 documents, against the draft of the reference; then on 60 documents of Ticino not
  seen before, 43 double names, against the role names OpenParlData holds (70 authors, 193 co-signers).
- **Result:** Reference sample, both fields, exact / too many / missing: as today 194 / 275 / 43; double is author
  127 / 185 / 116; role word 150 / 162 / 93; by the block 191 / 116 / 46; the bound, every double name where the
  reference has it, 194 / 118 / 49. A role word stands before 24 of the 163 names. Ticino: by the four ways that take
  a double name for an author the authors stay as today (51 right, 31 in the other role, 19 missing) and the
  co-signers right fall from 89 to 69. There author and co-signers stand in one line and one block.
- **Finding:** None taken. The rule by the block was found on the 60 documents it was counted on and does not hold on
  the unseen ones; the trial was stopped.
- **Run:** not kept in the repository. Repeatable with the stored answers of a run, a reference for both fields and
  the role names of OpenParlData.

## Vocabulary and mapping

### Does the model notice that the right category is missing?

- **Expectation:** Noted before the run as an objection: the small model does not say by itself that nothing fits;
  the run was to show whether it does when the answer "none fits" is offered.
- **Test:** 150 type labels with a reference, Apertus 8B, one call each, 150 calls; the list of categories holds the
  right one for 75 and lacks it for 75; "none fits" is allowed and a confidence is demanded.
- **Result:** Right category in the list: 32 right, 19 "none fits", 24 another category. Right category missing: 16
  "none fits", 59 another category. Every "none fits" carries the confidence 0; where the category is missing and
  another one is chosen, the confidence is 1 in 21, 0.9 in 18 and 0 in 10 of the 59. 14 answers lie outside the list.
- **Finding:** None taken from this run alone. The type is not decided by the model: code maps the printed label
  through the names of the parliament and the table (`src/docket/affair/types.py`).
- **Run:** not kept in the repository. Repeatable with 150 type labels of OpenParlData's export, half of them asked
  without their category.

### How far does the list of type names per parliament carry?

- **Question:** For how many affairs does the list OpenParlData keeps per parliament know the type the affair
  carries?
- **Test:** The 1 352 rows "type name per parliament" of OpenParlData's admin panel (87 parliaments, 1 211 with a
  harmonised type), fetched for the test, against the 325 600 affairs of its export. No model.
- **Result:** 270 327 affairs (83.0 %) carry a name of the list with the harmonised type the export holds; 22 168
  (6.8 %) a name the list keeps without a harmonised type; 12 536 (3.9 %) a name the list harmonises otherwise than
  the export; 20 569 (6.3 %) have no type. No affair carries a type missing from the list of its parliament.
- **Finding:** The lists are the stem of the vocabulary; it lies in the store and can be changed there
  (`src/docket/store/vocabulary.py`, `data/knowledge/vocabulary.json`), decided on 10 October.
- **Run:** not kept in the repository. Repeatable with the list of type names per parliament and the export of the
  affairs.

### Do the events read from documents carry a standard name?

- **Question:** Can a read event be given one of OpenParlData's standard names by comparing the names?
- **Test:** The 96 events read in the runs of 10 October against the 106 standard names of events in the vocabulary.
  No model. Beside it, what the eight shipped affairs hold for the visitor's tables.
- **Result:** None of the 96 is called like a standard name; 25 contain one as a part. The eight shipped affairs hold
  43 contributors (6 with a party, 14 with "on behalf of"), 12 events and 2 meetings.
- **Finding:** No standard name is given to an event: matching by parts of words would be guessing.
- **Run:** not kept in the repository. Repeatable with the events of the stored records and the list of standard
  names in `data/knowledge/vocabulary.json`.

## Schema

### Which existing schema covers what the brief and the documents ask for?

- **Question:** How much of 20 requirements do OpenParlData, JATS, Akoma Ntoso, Parla-CLARIN, Popolo and OParl meet?
- **Test:** 15 requirements from the brief and 5 from the documents, each judged yes, partly or no against the schema
  files of the six, with the ground noted per line; the judgements are the assistant's. Beside it a count over the 79
  documents drawn and the 72 with elements.
- **Result:** Yes / partly / no: OpenParlData 7 / 3 / 10, JATS 9 / 6 / 5, Akoma Ntoso 12 / 8 / 0, Parla-CLARIN
  7 / 10 / 3, Popolo 2 / 8 / 9, OParl 5 / 7 / 7. In points, every line weighted alike: 8.5 of 20, 12 of 20, 16 of
  20, 12 of 20, 6 of 19, 8.5 of 19. The documents: 52 of 79 affairs have more than one PDF; 40 of one page, the
  longest 153 pages; a label with a colon on 56 of 72 first pages, 118 different labels, 102 of them once.
- **Finding:** The record keeps OpenParlData's shape and adds the description of the document with the names of JATS,
  as JSON (`data/schema/DEFINITION.md`); the weighting of the lines stayed open. What the terms are called in the
  other standards is in `docs/mapping.md`.
- **Run:** not kept in the repository. Repeatable with the published schema files of the six and the list of
  requirements.

### Can Akoma Ntoso take a document it has no type for, without changing its schema?

- **Expectation:** A document written with the general elements of Akoma Ntoso validates against its XSD, and one
  with an invented element does not.
- **Test:** Page 1 of the kickoff example written as an Akoma Ntoso `doc` with the general elements and their `name`
  attribute, 85 elements, checked with `xmllint` against `akomantoso30.xsd`; then the same with one invented element.
- **Result:** The probe validates, at the first attempt and again on 12 October. The one with the invented element
  failed to validate; that file is not kept. The XSD does not check the values of `name`, nor whether a reference
  points to a known term. 17 elements are the obligatory identification, with nothing from the document.
- **Finding:** Akoma Ntoso was not taken as the shape of the record; its names stand beside the terms in
  `docs/mapping.md`.
- **Run:** not kept in the repository. Repeatable with a page written as Akoma Ntoso 3.0 and the published XSD.

### Does the description of a document validate as JATS?

- **Expectation:** The kickoff example written as JATS validates against the XSD of JATS 1.3.
- **Test:** `nidau-m185` written as a JATS article in three forms: with a journal block without an ISSN, with a
  placeholder ISSN, and without a journal block; each checked with `xmllint` against the Publishing and the Archiving
  XSD of JATS 1.3. Then one invented element.
- **Result:** Publishing: the first and the third form fail, the one with an ISSN validates. Archiving: all three
  validate; checked again on 12 October with the same six outcomes. The form with the invented element failed; that
  file is not kept.
- **Finding:** The names of the record are those of JATS 1.3 Archiving, in JSON; no XML and no XSD in the product
  (decided on 5 October; `data/schema/DEFINITION.md`).
- **Run:** not kept in the repository. Repeatable with the document written as JATS and the two published XSD
  packages.

### Does the checker of the contract report a block that does not exist and a source that points nowhere?

- **Expectation:** Both planted errors are reported.
- **Test:** The first checker of the contract on the example record, then on the example with an invented block and a
  `source` that points to no block.
- **Result:** The example fits. Both planted errors are reported, 2 of 2; a dynamic key is shown as such.
- **Finding:** The contract became a JSON Schema the same evening and the checker was replaced; today
  `src/docket/affair/validator.py` checks every record. The script of this test no longer exists.
- **Run:** not kept in the repository. Repeatable with a record, an invented block and a source without a block
  against `data/schema/docket.json`.

### Does the contract accept what OpenParlData's API returns, unchanged?

- **Expectation:** 72 of 72 unchanged answers of the API fit the contract; the first rule of the definition is that
  what OpenParlData returns stays as it is.
- **Test:** The API's answers for the 72 affairs of the working set, fetched for the tests, against the contract in
  an earlier build.
- **Result:** 65 of 72 fit. The 7 others hold `contributors: null`, for an affair without contributors, where the
  contract demanded an object. After the correction 72 of 72.
- **Finding:** `docs`, `contributors` and `events` may be `null` (`data/schema/docket.json`).
- **Run:** not kept in the repository. Repeatable with unchanged affair records of the API and the contract.

## Reference set

### What does a reading of 60 documents in three languages give as a reference?

- **Question:** Can a reference for the fields be read from a sample of documents in German, French and Italian?
- **Test:** 60 documents: the eight shipped and 52 drawn from OpenParlData for the test, 20 per language, from 34
  bodies (cantons and municipalities 12 and 8, 12 and 8, 11 and 9); 8 without a text layer. Read by the assistant: 22
  fields per document, every value with its page and passage.
- **Result:** 1 087 values, 562 empty fields. 20 of the 60 documents are read in part only, from page 2 on as an
  excerpt. Kinds as read: 35 submissions, 17 answers of the executive, 3 committee reports, 4 extracts of minutes, 1
  agenda. The number often does not stand on the document as OpenParlData holds it.
- **Finding:** The reading is a draft: it was not checked and no reference set was frozen. Where
  `docs/evidence.md` says "gold draft", it is this reading with the judgements of the entry "Which value holds where
  pipeline and reading differ?".
- **Run:** not kept in the repository; the documents name people. Repeatable with a sample drawn the same way and a
  reading of the 22 fields.

### Do the passages the reading cites stand on the pages it names?

- **Question:** Is every cited passage of the reading found on its page by code?
- **Test:** The citations of the reading split into pieces of at least 12 characters and searched in the text of the
  page named, white space and hyphens at line ends evened out; documents without a text layer are left out. No model.
- **Result:** 762 pieces checked, 718 found on the page named, 44 not, on 10 October and again on 12 October. The 44:
  text set in columns and headers, descriptions of stamps and logos, text layers from character recognition. Two
  wrong page numbers were found and corrected.
- **Finding:** The two page numbers were corrected in the reading; nothing else was decided.
- **Run:** not kept in the repository. Repeatable with the reading and the PDFs.

### How much of the reading is copied from the page, and how much is set?

- **Question:** Per field, does the value stand literally in the passage cited for it?
- **Test:** The 1 087 values of the reading, each searched in its own citation. No model.
- **Result:** Literal: number 43 of 43, title 57 of 58, type 58 of 58, addressee 52 of 53, place 21 of 21, parliament
  40 of 45, polity 52 of 57, submitters 105 of 132, co-signers 75 of 137. Rewritten or set: date 10 of 52 literal,
  events 3 of 109, references 48 of 102, session 5 of 14, decision 4 of 20, kind of document 0 of 60. Mixed: 44 of
  132 submitters with a party or place in brackets, 42 of 53 addressees taken from a sentence, 9 co-signer entries a
  number instead of names. No keywords in 60 documents. Counted again on 12 October with the same figures.
- **Finding:** None taken.
- **Run:** not kept in the repository. Repeatable with the reading.

### Where do pipeline and reading differ?

- **Question:** For which fields of the 60 documents does the run of the pipeline give another value than the
  reading?
- **Test:** The 52 drawn documents run with Apertus 8B on 10 October (536 calls, 40.5 minutes, no halt, every record
  valid), the eight shipped from their stored run; per document 21 fields held against the reading. Equal means: case
  and punctuation ignored, numbers in normal form, dates as a day, names in any order, set by the assistant.
- **Result:** 1 260 comparisons: the same 298, both empty 353, to decide 609 (different 223, only the pipeline 172,
  only the reading 214). By language, of 420 each: German 195 to decide, French 196, Italian 218.
- **Finding:** None taken; the 609 lines went into the judgements of the next entry.
- **Run:** not kept in the repository. Repeatable with a run over the sample and the reading.

### Which value holds where pipeline and reading differ?

- **Question:** Can the 609 open lines be given a judgement from the material, so that a person only has to check
  them?
- **Test:** Per line the evidence at hand: the value OpenParlData holds for the affair, the lists of the parliament,
  the same value under another field, two spellings of one value, the form of the field. Where no evidence decides,
  the passage was read again by the assistant. No model.
- **Result:** 609 lines: 151 decided by evidence, 185 where only the reading has a value, 139 by a rule, 134 read
  again, none open. What holds: the reading 427 times, the pipeline 6, the field stays empty 170, a mix 6. The
  reading is corrected in 14 lines. Eight rules, each with its lines: two spellings 56, the field a value belongs to
  28, the place only from a line of place and date 25, a party only beside a name 12, "on behalf of" only when stated
  10, the addressee 8, a reference only with title or number 4, co-signers as printed 4.
- **Finding:** A draft of the reference was written in the state "draft, not checked"; it was not approved line by
  line and nothing was frozen.
- **Run:** not kept in the repository. Repeatable with the comparison of the entry before and the material named.

### How many fields does the pipeline get right against the draft reference?

- **Question:** Per field, language, kind of document and text layer: how often does the run give what the draft
  reference holds?
- **Test:** The run of 10 October at midday, before the rebuild of that evening, against the draft of the reference:
  60 documents, 21 fields, 1 260 fields and the values in them. No fresh run was made.
- **Result:** Fields: right 303, right but for the spelling 65, rightly empty 355, partly 58, wrong 99, filled where
  nothing stands 168, missing 212. Values: 1 132 in the draft, 1 189 in the run; exactly the same 516, another
  spelling 90, too many 583, missing 526. Right and rightly empty: German 55 %, French 54 %, Italian 48 %;
  submissions 55 %, other kinds 48 %; with a text layer 53 %, scans 48 %. Per document 6 to 16 of 21 fields. Of the
  583 values too many, 163 are names the run holds as author and as co-signer and 45 are keywords.
- **Finding:** None taken; no reference was frozen that day. The figures say nothing about the code after the
  rebuild, and the reference is one reading with its own judgements, not a second reading independent of it.
- **Run:** not kept in the repository. Repeatable with a run over the sample and the draft reference.

### What passes without a mark for a person?

- **Question:** If the pipeline ran unattended, how many of the values it sets without a mark are in the draft
  reference?
- **Test:** The 1 181 values set by the run of 10 October at midday on the 60 documents, split by whether they carry a
  mark for a person, against the draft reference. No model.
- **Result:** Without a mark 1 116: in the draft 456, written differently 81, not in it 579. With a mark 65: 27, 9
  and 29.
- **Finding:** None taken.
- **Run:** not kept in the repository. Repeatable with a run over the sample and the draft reference.

## Learning

### What repeats in the answers of a run, before anyone has decided anything?

- **Question:** Which patterns would a correction fall into, counted on a stored run?
- **Test:** The run of 6 October: 64 documents of 19 bodies with their answers kept, 1 422 parts of answers, 1 181
  with a place, 241 without. A reference for 60 documents from OpenParlData's export. No model, and no decision of a
  person yet.
- **Result:** Against the reference: the title differs by an affix in 13 cases, the type in 6; the same affix at most
  twice. The same value in the same field in at least 3 documents: 46 values. 26 of 55 read titles begin with the
  read type. The number differs or is missing in 23 of 60. The date is another than the begin date of the export in
  31 of 60, and that date stands in the document in 3. 512 fields empty and 20 without an answer, of 1 450.
- **Finding:** None taken from the count. It went into a catalogue of what can be learnt, whose grouping into 20
  patterns was set by the assistant, open.
- **Run:** not kept in the repository. Repeatable with the stored answers of a run and the export of the affairs.

### How many ways of the second opinion are kept when it learns from all documents?

- **Question:** For how many fields does the usual place or the network agree with the model more often than not?
- **Test:** The second opinion learnt from the 151 stored documents of Basel-Stadt, Vaud and Ticino with the code as
  built, each way tried on documents held back. No model.
- **Result:** As stored on 10 October at 21:54: 23 ways kept, 12 of 34 places per parliament and field and 11 of 22
  fields of the network. Not kept, for example, the place of the type in Ticino (9 agreeing, 10 disagreeing). The
  work log of 19:55 counts 22 ways with 10 fields of the network; the lists of names got a network of their own after
  that, which adds the authors.
- **Finding:** None taken. A way is used only where agreeing outweighs disagreeing on the documents held back
  (`src/docket/fields/second.py`, `tools/learn.py`).
- **Run:** not kept in the repository. Repeatable with `make learn` on a store that holds the documents of a few
  parliaments.

### Does the rule that learns a label show on real documents?

- **Question:** With the label rule built, does a document's printed label give the value where the model reads it
  wrong, on the kickoff example and on documents of the same form?
- **Test:** With the model, 82 calls in the night of 11 October: the kickoff example three times at 6 calls (the first
  two are the runs of the two entries on the kickoff example, the third has the rule), three more documents of Nidau
  fetched from OpenParlData for the test (50 calls, 32 of them to read a scanned page), two documents of Bern from
  the reference sample (14 calls). Before that `make test` with the new rule.
- **Result:** `make test`: 342 ok, none failed. Kickoff example: every label of the header recognised, the key is the
  one of the number OpenParlData holds, whatever the model reads as the number ("/ 2" in this run). The three from
  Nidau are scans with a text layer from character recognition, number and tick written by pen: one label recognised
  in two of them, a misread tick once, no value beside the label of the number. The two from Bern: the model read
  number, type and date right and there was nothing to correct.
- **Finding:** The label rule is in the store's rules (`src/docket/store/rules.py`, `tests/rules.py`,
  `tests/decisions.py`). Its learning is shown on runs made up for the tests, not on pairs of real documents.
- **Run:** not kept in the repository; five of the six documents are not among the shipped ones. Repeatable with
  documents of one parliament that print a header of labels and values.

## Store

### How long does "how many further documents" take over the records?

- **Question:** What does asking every stored affair cost when a rule's reach is counted?
- **Test:** The store of the run over the reference sample: 51 affairs, 952 values, file store; the time per affair
  measured, then multiplied.
- **Result:** 0.8 milliseconds an affair. Multiplied to 300 000 affairs 252 seconds a question, to 900 000 affairs 756
  seconds; extrapolated, not measured.
- **Finding:** The reach of a rule is asked of the rows, by field and value, and only the records it names are read
  (`src/docket/store/rows.py`).
- **Run:** not kept in the repository. Repeatable by timing the question on a store and multiplying.

### Can every value be a row that says what it is, and how fast is a question over such rows?

- **Question:** Do the stored reports turn into rows of kind, field, value and place, and what does a question over
  them cost at the size of the corpus?
- **Test:** 141 documents run on 10 October turned into rows in an SQLite database, no model; then the rows
  multiplied and one question timed with an index on kind and value.
- **Result:** 3 321 rows: person 1 384, group 290, keyword 217, date 186, number 173, summary 141, type 133, event
  133, polity 132, parliament 132, title 130, place 107. 536 answers that did not hold have a row. 188 milliseconds at
  300 048 documents and 7.07 million rows, 1 064 milliseconds at 900 003 documents and 21.2 million. SQLite, not
  Postgres; multiplied rows, not real ones.
- **Finding:** The rows are kept in the store beside the record (`src/docket/store/rows.py`, `tests/rows.py`), decided
  on 10 October.
- **Run:** not kept in the repository. Repeatable with the stored field reports of a run and any SQL database.

### Does the store work on a real Postgres?

- **Question:** Do the operations of the Postgres store, written without a database at hand, hold against one?
- **Test:** PostgreSQL 16.2 started without Docker, the store's tests run in a schema of their own
  (`tests/store.py --postgres`), repeated after each extension of the store on 10 October; once the whole way from an
  empty database to an affair laid in by the pipeline without the model.
- **Result:** First run, before any change: 10 of 10 basic operations. Then 13 of 13; in the later runs of the day
  29, 17, 19, 20 and 22 checks ok, as the test changed with the store, none failed; 43 ok in the rehearsal on a clean
  checkout. The whole way 8 of 8: the first opening fills 1 488 rows of the vocabulary in 0.20 seconds, the second
  writes nothing. `tests/decisions.py` and `tests/rows.py` were not run against Postgres.
- **Finding:** None taken. The same test runs inside the container (`make test-store`) and passed there in the Docker
  rehearsal of 10 October.
- **Run:** not kept in the repository. Repeatable with `make run` and `make test-store`.

### Does the second opinion learn into Postgres?

- **Expectation:** Four checks hold: the store is the Postgres one; what was learnt lies in the database and the place
  of the number is used; a missing date comes from the block named and is marked; the counts of asked fields and of
  affairs without rows run on Postgres.
- **Test:** The learning run against PostgreSQL 16.2 started without Docker, on 10 October. No model.
- **Result:** 4 of 4.
- **Finding:** None taken.
- **Run:** not kept in the repository. Repeatable with `make learn` inside the running container.

## Operation

### How long does a document take, and what would the whole stock take?

- **Question:** How many seconds does a document take from the PDF to the record, how much of that is the model, the
  pauses of the client and the computing, and what does that make for the documents OpenParlData holds?
- **Test:** The 60 documents of the reference set through `python3 -m docket affairs --model` twice, with the client as
  it was (two seconds before every call, twenty before every fiftieth) and with the pace as built; then once without
  the model, to time the computing alone. 583 calls a run, all answered. One machine, one core, one stream.
- **Result:** With the pace before: 13.0 s at the model and 19.4 s of pauses a document; 57.5 s of wall clock on the
  27 documents measured on a free machine. With the pace as built: 24.8 s a document (26.4 s on the same 27), 9.8 s of
  them at the model; a document with a text layer 20.6 s, one without 48.7 s. Without the model 14.8 s a document,
  5.1 s a page; 44 % of that in one function that scales the page image, 32 % in writing the control image of every
  page. The 9 documents without a text layer take 283 of the 583 calls. Calculated from the second run, one document
  after the other: 93 days for 325 599 documents, 260 days for 907 472; with the pace before 167 and 465 days. The
  documents measured have 2.9 pages on average; how the time at the model grows with longer documents was not
  measured, nor whether the endpoint takes several streams at once.
- **Finding:** The client sends ten calls one after the other and then waits half a second; a call turned down with a
  4xx is sent once more after half a second, and a 403 or 429 on that one halts the client
  (`src/docket/model/client.py`, `tests/client.py`). The pace is set, not measured against a limit.
- **Run:** `results/runtime/`

### What does a run over the shipped documents cost?

- **Expectation:** A run with the model over the eight shipped documents stays under five minutes.
- **Test:** `make bench` on 8 October at the state of that evening: eight documents, 15 pages, one of them without a
  text layer, Apertus 8B, one call after the other with a pause of two seconds; the memory of the process read every
  five seconds.
- **Result:** 60 calls, all answered with status 200: 13 to read the page without a text layer, 8 to sort, 39 for the
  fields. 4.5 minutes; the logs span 264 seconds from the first call to the last answer, 63.8 of them at the model.
  80 402 tokens in, 5 028 out. Peak memory 0.6 GB with one document in flight. Eight of eight records valid.
- **Finding:** None taken. The calls are stated as the budget of a document in `docs/architecture.md`: four to six
  for the fields, one for the sorting, thirteen for a scanned page. No later run over the eight is kept.
- **Run:** `results/shipped-documents/`

### Does `make run` show the app on a clean checkout?

- **Expectation:** The template of the challenge: `make run` from the root of a clean checkout, with Docker, starts
  the project, and the model is set by `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`.
- **Test:** On 10 October. First without Docker, a clone into an empty folder and every step of the Dockerfile and of
  the compose file one by one. Then in Docker three runs: the commit as it was; a clone with two corrections; the
  working tree with a third part that fills an empty store.
- **Result:** Without Docker 18 steps ok and 1 failed: the built app lies one folder below where the server looks for
  it. Run 1 confirms it: `make run` builds and starts in about 2.5 minutes and shows the fallback page instead of the
  app; the store is empty. Run 2: the app loads, the three variables arrive from the shell and from `.env`. Run 3:
  the server answers at once with 0 affairs and one queued run, then 8 affairs, page image and affair open. In the
  container the eight PDFs take 79 seconds for the geometry and 61 seconds for the affairs without the model.
  `make test`: 323 ok.
- **Finding:** The Dockerfile copies the app from where the build puts it; the three variables carry the names of
  the template (`src/docket/config.py`, `compose.yaml`, `.env.example`); an empty store is filled at start from the
  stored runs of the shipped documents where they lie (`src/docket/runner.py`, `src/docket/jobs.py`,
  `tests/shipped.py`). The Docker build of the four language versions of 11 October was not tried.
- **Run:** not kept in the repository. Repeatable with a clean clone and `make run`.

### How long does an affair take through the whole chain?

- **Question:** What do time and calls per affair come to when every page is sorted by the model?
- **Test:** An earlier build that fetched an affair and its oldest German PDF from OpenParlData; three affairs as a
  probe, then the 72 affairs of the working set with all 455 pages, Apertus 8B.
- **Result:** Probes: 1 page 27 seconds and 6 calls, 17 pages 108 seconds and 25 calls, 1 page 22 seconds and 5
  calls. The run was stopped after 56 minutes: 25 affairs, 149 pages, 325 calls, about 2.2 minutes an affair, about
  two calls a page for sorting the rest. The files of that run were deleted later.
- **Finding:** The rest is sorted on the first pages only: page 1, or pages 1 and 2 where page 1 holds less than a
  tenth of the text of page 2 (`src/docket/pipeline.py`). The input is the PDF only, never the API (decided on
  6 October).
- **Run:** not kept in the repository. Repeatable with documents of several pages and the sorting on every page.

### Do two PDFs of one affair come together, and what do the pages cost after the change of input?

- **Question:** With the PDF as the only input: are documents of one number merged, and how long does a document
  take?
- **Test:** An earlier build after the change to PDF input: two PDFs and a copy of the first; a document of 17 pages
  given to the model as a whole; the times of a one-page and a 17-page document; one page saved without a text
  layer.
- **Result:** Two affairs, one of them with two documents, both valid. The 17 pages as a whole are 9 494 tokens,
  answered in 3.4 seconds. One page: 28 seconds with 8 calls; 17 pages: 78 seconds with 12 calls (before 108 seconds
  with 25). The page without a text layer: 16 elements read, 8 marked for a person, 89 seconds.
- **Finding:** Documents are grouped by the read number into one affair (`src/docket/affair/merge.py`); fields over
  the whole document see all pages up to 120 000 characters (`src/docket/fields/filler.py`).
- **Run:** not kept in the repository. Repeatable with two PDFs of one affair and a document of many pages.

### How many documents without a text layer were left unread, and what would reading them cost?

- **Question:** Is another run over the scans of the large draw worth its calls?
- **Test:** A count over the documents of the draw of 10 October that were not run, and over the run of the reference
  sample. No model.
- **Result:** 59 documents not run (Basel-Stadt 21, Vaud 28, Ticino 10), 137 pages, 113 of them without a text layer.
  By the calls used so far about 1 800 (6 a document, 13 a page read); by the rate of one mixed document of
  10 October, 479 calls for 7 pages, up to about 8 000. Estimated, not run. In the run over the 60 documents of the
  reference sample the text of 12 comes mostly from character recognition.
- **Finding:** The run was not made (decided on 11 October).
- **Run:** not kept in the repository. Repeatable by counting pages without a text layer in a set of PDFs.

### Does the solution deliver what the briefing and the template ask for?

- **Question:** Laid side by side: what do the briefing of the hackathon and its official template ask for that
  the solution does not deliver yet?
- **Test:** 10 October 2026, no model call, nothing changed: the briefing, the notes of the kickoff, the answers
  of the question session and the template read against the repository of the track for parliamentary documents
  as committed on 8 October; its test suite run; the example shown at the kickoff held against the track's own
  result for that document.
- **Result:** The test suite: 98 checks passed, none failed. Eight gaps. (1) Readme and technical report were
  the unfilled template, and the answer to the feasibility question stood nowhere as a reasoned conclusion.
  (2) No gold set with every value checked, and no question answered across parliaments; the briefing asks for
  both. (3) No federal document among the shipped ones; languages 5 German, 2 French, 1 Italian; the one "scan"
  a rendered page without a text layer. (4) The example of the kickoff in the track's own result: number and
  type wrong, the authors split wrongly, one event with a wrong date; title and date of submission right.
  (5) Vocabularies for roles, states and outcomes missing as lists. (6) A run on a CPU with 20 GB not measured.
  (7) The template asks for the settings `LLM_NAME`, `LLM_BASE_URL` and `LLM_API_KEY`; the code read other
  names, in both tracks, and the start in a container had never run. (8) Of the six measures of the track's core
  question only one measured over the corpus.
- **Finding:** The gaps were taken into the work list as eleven points, the gold set first. The same day the
  settings were renamed to the names of the template in both tracks and the start in a container was run.
- **Run:** not kept in the repository. Repeatable with the briefing, the template and the repository side by
  side, then `make test` and `make run` in a container.

## Interface

### Does the admin's view of the vocabulary do what it shows?

- **Expectation:** 13 checks hold in the browser, among them: 17 types, the names of one parliament, a name set and
  taken back, a name added and taken back, 106 events, an empty parliament reported, no error in the console.
- **Test:** The built app in a browser without a window against a server on a store made for the test, on 10 October.
- **Result:** 12 of 13 in the first pass, where the check itself looked for a text with a blank the page does not
  print; then 13 of 13. Seen on the way and repaired: at 390 pixels the table ran out of its card; a hanging
  separator after the name of a municipality; a chip without a gap. `make test`: 146 ok.
- **Finding:** The view is the admin's area for the vocabulary (`app/src/app/admin/vocabulary.ts`).
- **Run:** not kept in the repository. Repeatable with `make app`, a server on an empty store and the 13 checks.

### Does every page of the visitor's part hold what the store holds?

- **Expectation:** No check fails: every list, card and page shows what the API of the same store returns, and no
  link leads to "undefined".
- **Test:** The built app walked through in a browser without a window on 11 October, after every affair had linked
  to "undefined" on a store written before the records named themselves: the six lists, every card, every page of an
  affair, document, person, group and meeting, counts, search, the four filters, the JSON view, a copied address,
  paging, unknown addresses, the language switch, errors in the console; in the second round also every document
  page against the blocks of its record, the door of the administration, and one standard name added and taken back.
  Stores: one written before the records named themselves, the store of 8 October, and a fresh one.
- **Result:** First round: older store in German and French 1 540 ok, none failed; store of 8 October in German 709
  ok; fresh store in four languages 3 058 ok and 4 failed (the filter by type in French and Italian, a document page
  not loaded in time), then 3 055 and 7, all 7 from the walk looking before the page had arrived. Second round at the
  final state: fresh store with a password in German 791 ok; older store in four languages 3 069 ok; fresh store in
  German and French 1 552 ok; none failed. The kept reports hold the last walk of each store: 3 069, 709 and 1 552.
- **Finding:** At start the server gives every record stored without an `id` its key and its parliament
  (`src/docket/api.py`); addresses with round brackets are written as the router writes them; a type is found by any
  of its wordings (`src/docket/public.py`); a person, group or meeting is asked by its exact name. A check that ran
  on a store with no contributors now runs on full records (`tests/shipped.py`).
- **Run:** not kept in the repository; the script of the walk is not part of it. Repeatable with a server on a store
  of the shipped documents and a walk through every list and page against `/api/records`.

## Questions across the parliaments

### How many members back an affair?

- **Question:** Does the number of persons a document names for an affair differ from the number OpenParlData holds?
- **Test:** Distinct names under authors and co-signers together, from the runs of 10 October (208 documents, 32
  parliaments), against the persons in OpenParlData's export, fetched for the test, and for 57 documents of the
  reference sample against its draft. No model.
- **Result:** Pipeline the same as the draft for 31 of 57, at most one off for 45. OpenParlData the same as the draft
  for 33 of 57, fewer than printed 16, more 8, none 7. Names in sum: draft 254, pipeline 323, OpenParlData 191. Per
  parliament: Basel-Stadt, 50 documents, OpenParlData always one person, the pipeline more in 22; Vaud, 44
  documents, more in 38; Ticino, 69 documents, OpenParlData more than the pipeline in 26.
- **Finding:** Built as the first of three questions answered from the store without the model
  (`src/docket/questions.py`, `tools/questions.py`, `tests/questions.py`).
- **Run:** not kept in the repository. Repeatable with `make questions` on a store and the exports of OpenParlData.

### Which kinds of documents hang on the affairs, and which details does a parliament print?

- **Question:** What do the kinds the pipeline gives and the fields the documents print say per parliament?
- **Test:** The kinds in the runs of 10 October per parliament, and on the 60 documents of the reference sample
  against its draft; from the draft, per field, in how many documents and bodies it is printed. No model.
- **Result:** Kinds on the reference sample: right 35, wrong 13, none chosen 12; most often an answer taken for a
  submission (6) or left without a kind (5). Per parliament, submission / answer / none: Basel-Stadt 27 / 14 / 3,
  Vaud 18 / 5 / 8, Ticino 34 / 2 / 22. Printed, of 60 documents and 34 bodies: authors 59 and 33, title and type 58
  and 33, addressee 53 and 32, date 52 and 30, number 43 and 28, place 23 and 18, party 15 and 11, co-signers 14 and
  10, department 8 and 5, keywords 0.
- **Finding:** Built as the second and third question of the same tool (`src/docket/questions.py`,
  `tools/questions.py`).
- **Run:** not kept in the repository. Repeatable with `make questions` on a store.
