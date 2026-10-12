# Result: how the fields are asked

Measured on 12 October 2026 on the 60 documents of the reference set (`python3 -m docket affairs --model`, the PDFs as the only input, Apertus 8B at temperature 0), each field of each document held against the draft reference: 60 documents, 21 fields, 1 260 fields. The reference is a draft read by the assistant and not checked; the equalities are those of `docs/evidence.md`, section 6. A field counts as right when it holds the values of the reference (also in another spelling) or is empty where the reference is.

Between two runs of the same build 8 of the 1 260 fields changed between right and not right that day.

## Three runs through the whole pipeline

| | calls | tokens in a document | fields right | filled where nothing belongs | missing | partly or wrong |
|---|---:|---:|---:|---:|---:|---:|
| before | 583 | 14627 | 707 (56.1 %) | 179 | 189 | 185 |
| contributors together | 655 | 17946 | 730 (57.9 %) | 143 | 195 | 192 |
| together, leading line, keywords on condition | 646 | 17406 | 793 (62.9 %) | 119 | 163 | 185 |

| field | before | contributors together | together, leading line, keywords on condition | filled where nothing belongs: before | contributors together | together, leading line, keywords on condition |
|---|---:|---:|---:|---:|---:|---:|
| number | 40 | 38 | 43 | 2 | 2 | 3 |
| title | 33 | 36 | 41 | 0 | 1 | 1 |
| type as printed | 47 | 47 | 50 | 0 | 1 | 2 |
| date of submission | 37 | 37 | 40 | 5 | 5 | 5 |
| authors | 38 | 33 | 42 | 0 | 1 | 1 |
| party | 33 | 36 | 31 | 21 | 21 | 24 |
| on behalf of | 25 | 45 | 41 | 33 | 11 | 14 |
| co-signers | 15 | 44 | 42 | 37 | 6 | 8 |
| addressee | 25 | 19 | 24 | 5 | 6 | 7 |
| place | 33 | 34 | 30 | 22 | 22 | 26 |
| parliament | 41 | 39 | 42 | 9 | 9 | 8 |
| polity | 43 | 42 | 45 | 2 | 2 | 2 |
| department | 51 | 50 | 50 | 2 | 3 | 3 |
| related affairs | 45 | 35 | 47 | 6 | 17 | 3 |
| acts and references | 17 | 12 | 14 | 2 | 5 | 4 |
| keywords | 33 | 36 | 60 | 27 | 24 | 0 |
| events (name) | 1 | 2 | 3 | 1 | 0 | 0 |
| events (date) | 14 | 11 | 15 | 0 | 0 | 0 |
| version | 58 | 57 | 56 | 0 | 1 | 2 |
| session | 42 | 41 | 41 | 5 | 6 | 6 |
| kind of document | 36 | 36 | 36 | 0 | 0 | 0 |

Before: authors and party were asked in the first call over the first pages, in whose name in the second, the co-signers in the third over the whole document. Contributors together: the four in one call over the whole document (`together` in `data/schema/fields.json`); the other fields keep the calls they had. The third run adds the line before the first field of every call (`$task.lead`) and asks for printed keywords only where a word for them stands on the pages (`when`).

## What led there, on the answers of the model

The trials below compare what the model answers, cut into entries as the pipeline does, with the reference; the search for a place on the page is left out, alike for every way. The text of each document is the one of the stored call, character for character.

### One value in two fields: can code decide?

Counted on the stored answers of the run before, no call. The same value stood in two fields of a document 328 times, in 48 of 60 documents; by the reference 109 belong to the field asked earlier only, 138 to the later one only, 19 to both, 62 to neither. Keeping the value in the earlier field removes 160 wrong and 120 right values: 671 fields right before, 672 after (of 1 200, without the kind of document). With the direction set per pair of fields on this very sample: 701. Marking both places instead: 274 wrong and 236 right values would be marked, 54 % wrong; among all values without a mark 56 % are wrong.

### The four contributor fields in one call

| | fields right of 240 | the same entry in more than one of the four | filled where nothing belongs |
|---|---:|---:|---:|
| as before, three calls | 95 | 169 | 102 |
| one call, the questions as they are | 153 | 43 | 45 |
| one call, questions worded so that a name can stand in one field only | 159 | 16 | 30 |

120 calls. With the second wording no right value of "on behalf of" is left (5 with the first), and it was not taken. In documents with one author and many co-signers (1 and 22, 1 and 15, 1 and 33) the model puts every name under the authors with either wording.

### Does the first field of a call draw a value?

Three calls a document as built in the second run, 60 documents; the order turned (the first field last, the second first), and with a line before the first field whose answer is not used (the language of the document). 360 calls.

| call | field | place as built | right as built | order turned | with the leading line | filled where nothing belongs as built | turned | leading line |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| contributors | authors | 1 | 33 | 42 | 41 | 1 | 0 | 1 |
| contributors | party | 2 | 36 | 17 | 30 | 21 | 38 | 25 |
| contributors | on behalf of | 3 | 42 | 22 | 39 | 14 | 33 | 16 |
| contributors | co-signers | 4 | 43 | 40 | 43 | 7 | 12 | 7 |
| bodies | addressee | 1 | 21 | 22 | 25 | 5 | 7 | 7 |
| bodies | place | 2 | 31 | 25 | 30 | 24 | 32 | 26 |
| bodies | parliament | 3 | 35 | 33 | 38 | 14 | 15 | 12 |
| bodies | polity | 4 | 45 | 43 | 47 | 4 | 6 | 4 |
| references | related affairs | 1 | 32 | 39 | 47 | 20 | 14 | 4 |
| references | acts and references | 2 | 11 | 2 | 13 | 6 | 15 | 5 |
| references | keywords | 3 | 29 | 17 | 2 | 31 | 43 | 58 |
| references | events (name) | 4 | 3 | 5 | 3 | 0 | 0 | 0 |
| references | events (date) | 5 | 13 | 22 | 19 | 0 | 0 | 0 |
| all 13 fields, of 780 | | | 374 | 329 | 377 | 147 | 215 | 165 |

Whichever field stands first is filled more often where nothing belongs, and the field moved away from the first place gains. With the leading line the model fills the keywords in 58 of 60 documents.

### Keywords

By the reference none of the 60 documents prints keywords; the pipeline set some in 27 documents in the first run and in 24 in the second. On none of the 60 documents one of the words for keywords of the list in `data/schema/fields.json` stands (the third run asked for keywords in none). The call for related affairs, references and events once more without the line for the keywords, 120 calls: 62 of 240 fields right (59 with the line for the keywords); with the leading line in front as well 83 of 240, related affairs filled where nothing belongs twice instead of 20 times.

## Values without a mark

Values the pipeline sets without a mark for a person: 1 207 before, 873 in the third run; of these not in the reference 674 and 385.

Each state was run once. At temperature 0 the model does not always answer alike: sent twice, the calls of the contributor fields gave the same field in 95 % of the cases.
