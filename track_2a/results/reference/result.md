# Result: the 60 reference documents against the reference

Measured on 14 October 2026 at commit `f0df9ab`, without the model: the stored answers of the run of 12 October put
through the code of the commit, every document by the same code.

## The reference

60 documents, 20 each in German, French and Italian, 35 of cantons and 25 of municipalities, from 34 bodies; 8 of them
without a text layer. Eight are the shipped documents of `data/documents/`, 52 were drawn from OpenParlData's affairs
with seed 20261010, five kinds of affair in turn. The federal level is not in it: 16 of 16 federal submissions drawn
had no document, their text is held as text.

The AI assistant read every document field by field, each value with its page and the place it stands: 1 087 values, 562
empty fields. Code found 718 of 762 quoted pieces on the named page; the other 44 were looked at (text in columns,
headers, descriptions of stamps and logos, text layers from an earlier OCR), and two wrong page numbers were corrected.
A team member checked the tables of this reading and, on 14 October, 60 values of the reference drawn at random (seed
20261014, one per document) against the documents: all 60 hold. Where Docket's values and the reading disagreed, 609
places, each was judged: 151 by evidence from the material (OpenParlData's affair, the persons and parties of the body),
139 by one of eight rules (two spellings of one value, the field a value belongs to, the place only from the line of
place and date, the party only beside a name, on behalf of only where it is said, the addressee of the affair, a
reference only with a title or number, co-signers as printed), 134 by reading the place in the document again; 185 rest
on the reading alone. The rules were set by the assistant and are open to the team's correction. The reference names
people and is not in the repository.

## Fields as in the reference

A field of a document counts as right when it holds the values of the reference, complete, also in another spelling,
or stays empty where the reference is empty. 20 fields a document; events are counted by their dates.

| | documents | fields right | without a mark |
|---|---:|---:|---:|
| all | 60 | 940 of 1 200 (78.3 %) | 41 |
| German | 20 | 324 of 400 (81.0 %) | 13 |
| French | 20 | 320 of 400 (80.0 %) | 13 |
| Italian | 20 | 296 of 400 (74.0 %) | 15 |
| cantons | 35 | 546 of 700 (78.0 %) | 24 |
| municipalities | 25 | 394 of 500 (78.8 %) | 17 |

"Without a mark" is counted without the register of persons; with it, the run over 300 documents counts 38 of these
60 (`results/three-hundred/`).

## Per field

Right: in how many of the 60 documents the field is as in the reference. Without a mark: in how many of the 41
documents without a mark Docket set a value in the field, and in how many of them none of its values contradicts the
reference.

| Field | right of 60 | without a mark: set | of them without a wrong value |
|---|---:|---:|---:|
| place | 57 | 9 | 9 |
| meeting | 49 | 4 | 4 |
| body | 47 | 31 | 30 |
| title | 49 | 38 | 36 |
| type as printed | 53 | 37 | 35 |
| kind of document | 56 | 41 | 37 |
| submitted on | 39 | 20 | 18 |
| submitted by | 44 | 41 | 36 |
| parliament | 50 | 27 | 23 |
| events (dates) | 31 | 36 | 30 |
| addressee | 47 | 37 | 30 |
| number | 44 | 26 | 20 |
| co-signers | 51 | 8 | 6 |
| department | 54 | 11 | 7 |
| party | 41 | 14 | 8 |
| acts and references | 14 | 13 | 7 |
| related affairs | 49 | 4 | 2 |
| on behalf of | 49 | 3 | 1 |
| keywords | 60 | 0 | 0 |
| version | 56 | 0 | 0 |

## Repeatable

The reference and the stored answers stay local, beside the documents. The count puts every stored answer through the
code without the model, as `results/three-hundred/` does, and compares each of the 20 fields with the reference.

## The other 239 documents of the 300

The 240 drawn documents of `results/three-hundred/`, without the one scan that hit the time limit: 179 that were run for
the first time on 13 October and never used to set or try a rule, and 60 that were run before and served during
development as a check against the four fields OpenParlData holds. The AI assistant read them by the same fields and the
same eight rules as the reference above, without the judgement round: the reading itself is the reference. A team member
checked 60 values drawn at random (seed 20261015, one each from 60 of the 239 documents) against the documents: all 60
hold. Code found 2 681 of 2 807 quoted pieces on the named page (the others: lines joined in one quote, a logo
described). Counted the same way, on the stored answers of the 300-document run, without the model, without the
register's mark. The 95 % interval comes from drawing whole documents 10 000 times, because the fields of one document
are not independent.

| | documents | fields right | 95 % interval | without a mark |
|---|---:|---:|---|---:|
| the 60 reference documents above, developed on | 60 | 940 of 1 200 (78.3 %) | 75.6–80.9 % | 41 |
| never seen during development | 179 | 2 625 of 3 580 (73.3 %) | 71.7–74.9 % | 136 |
| checked against during development | 60 | 887 of 1 200 (73.9 %) | 71.2–76.7 % | 37 |
| all 239 | 239 | 3 512 of 4 780 (73.5 %) | 72.1–74.8 % | 173 |
| German | 80 | 1 165 of 1 600 (72.8 %) | | 60 |
| French | 79 | 1 154 of 1 580 (73.0 %) | | 60 |
| Italian | 80 | 1 193 of 1 600 (74.6 %) | | 53 |
| cantons | 139 | 2 044 of 2 780 (73.5 %) | | 113 |
| municipalities | 100 | 1 468 of 2 000 (73.4 %) | | 60 |

Per field over the 239: right, and in the 173 documents without a mark how often Docket set a value and how often
none of its values contradicts the reference.

| Field | right of 239 | without a mark: set | of them without a wrong value |
|---|---:|---:|---:|
| place | 219 | 59 | 58 |
| title | 211 | 160 | 155 |
| type as printed | 201 | 153 | 147 |
| kind of document | 203 | 173 | 146 |
| related affairs | 202 | 16 | 7 |
| department | 187 | 37 | 17 |
| on behalf of | 183 | 30 | 6 |
| meeting | 174 | 26 | 7 |
| parliament | 169 | 109 | 97 |
| addressee | 168 | 155 | 117 |
| body | 167 | 127 | 109 |
| co-signers | 167 | 40 | 26 |
| number | 162 | 106 | 83 |
| submitted on | 154 | 103 | 96 |
| submitted by | 146 | 168 | 118 |
| party | 144 | 70 | 28 |
| events (dates) | 115 | 140 | 110 |
| acts and references | 69 | 35 | 19 |
| keywords | 239 | 0 | 0 |
| version | 232 | 0 | 0 |
