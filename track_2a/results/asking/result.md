# Result: how the fields are asked

Measured on 12 October 2026 on the 60 documents of the reference set (`python3 -m docket affairs --model`, the PDFs as the only input, Apertus 8B at temperature 0), each field of each document held against the draft reference: 60 documents, 21 fields, 1 260 fields. The reference is a draft read by the assistant and not checked; the equalities are those of `docs/evidence.md`, section 6. A field counts as right when it holds the values of the reference (also in another spelling) or is empty where the reference is.

Between two runs of the same build 8 of the 1 260 fields changed between right and not right that day.

The days of events are counted as they stand in the record. An earlier state of this file counted them from the report of the run, where one answer with several days stood as one entry, and gave 707, 730 and 793 fields right for the first three runs; in the record every event of such a document carried the first of the days (9 of 9 documents with several days in the third run).

## Five runs through the whole pipeline

| | calls | tokens in a document | fields right | filled where nothing belongs | missing | partly or wrong |
|---|---:|---:|---:|---:|---:|---:|
| before | 583 | 14627 | 704 (55.9 %) | 179 | 198 | 179 |
| contributors together | 655 | 17946 | 728 (57.8 %) | 143 | 203 | 186 |
| together, leading line, keywords on condition | 646 | 17406 | 788 (62.5 %) | 119 | 173 | 180 |
| bodies by their role, events as pairs | 643 | 17441 | 841 (66.7 %) | 111 | 147 | 161 |
| place read by code, party kept apart | 643 | 17395 | 883 (70.1 %) | 75 | 140 | 162 |

| field | before | contributors together | together, leading line, keywords on condition | bodies by their role, events as pairs | place read by code, party kept apart | filled where nothing belongs: before | contributors together | together, leading line, keywords on condition | bodies by their role, events as pairs | place read by code, party kept apart |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| number | 40 | 38 | 43 | 43 | 43 | 2 | 2 | 3 | 3 | 3 |
| title | 33 | 36 | 41 | 41 | 39 | 0 | 1 | 1 | 1 | 2 |
| type as printed | 47 | 47 | 50 | 50 | 50 | 0 | 1 | 2 | 2 | 2 |
| date of submission | 37 | 37 | 40 | 39 | 40 | 5 | 5 | 5 | 6 | 6 |
| authors | 38 | 33 | 42 | 42 | 43 | 0 | 1 | 1 | 1 | 1 |
| party | 33 | 36 | 31 | 31 | 41 | 21 | 21 | 24 | 24 | 14 |
| on behalf of | 25 | 45 | 41 | 41 | 46 | 33 | 11 | 14 | 14 | 9 |
| co-signers | 15 | 44 | 42 | 42 | 43 | 37 | 6 | 8 | 8 | 8 |
| addressee | 25 | 19 | 24 | 47 | 47 | 5 | 6 | 7 | 5 | 5 |
| place | 33 | 34 | 30 | 34 | 56 | 22 | 22 | 26 | 22 | 1 |
| parliament | 41 | 39 | 42 | 50 | 49 | 9 | 9 | 8 | 4 | 4 |
| polity | 43 | 42 | 45 | 44 | 48 | 2 | 2 | 2 | 2 | 2 |
| department | 51 | 50 | 50 | 52 | 54 | 2 | 3 | 3 | 6 | 5 |
| related affairs | 45 | 35 | 47 | 49 | 49 | 6 | 17 | 3 | 1 | 1 |
| acts and references | 17 | 12 | 14 | 14 | 14 | 2 | 5 | 4 | 4 | 4 |
| keywords | 33 | 36 | 60 | 60 | 60 | 27 | 24 | 0 | 0 | 0 |
| events (name) | 1 | 2 | 3 | 9 | 7 | 1 | 0 | 0 | 0 | 0 |
| events (date) | 11 | 9 | 10 | 20 | 21 | 0 | 0 | 0 | 0 | 0 |
| version | 58 | 57 | 56 | 56 | 56 | 0 | 1 | 2 | 2 | 2 |
| session | 42 | 41 | 41 | 41 | 41 | 5 | 6 | 6 | 6 | 6 |
| kind of document | 36 | 36 | 36 | 36 | 36 | 0 | 0 | 0 | 0 | 0 |

Before: authors and party were asked in the first call over the first pages, in whose name in the second, the co-signers in the third over the whole document. Contributors together: the four in one call over the whole document (`together` in `data/schema/fields.json`); the other fields keep the calls they had. The third run adds the line before the first field of every call (`$task.lead`) and asks for printed keywords only where a word for them stands on the pages (`when`). The fourth, of the night to 13 October, asks addressee, place, parliament and polity by the role of each, asks an event with its day in one line (`paired`), reads a day written out in French, Italian or English, lets what happened take the block of its day, and asks for the department also where a French or Italian word for it stands. The fifth, of 13 October, reads the place by code from a line of a place and a day instead of asking for it, leaves out a party or on-behalf-of that already stands under the submitters or as a body of the document, and takes a bare no as no value.

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

Values the pipeline sets without a mark for a person: 1 205 before, 866 in the third run, 913 in the fourth; of these not in the reference 671, 386 and 369.

Each state was run once. At temperature 0 the model does not always answer alike: sent twice, the calls of the contributor fields gave the same field in 95 % of the cases.

## Asking the bodies by their role, an event with its day

Measured in the night to 13 October 2026. First the answers alone, as in the trials above: the stored call of each of the 60 documents sent again with other lines for the fields, 240 calls; then the pipeline, 656 calls, and once more after the finds below, the fourth run of the table at the top. The wordings were set by the assistant, open.

### Addressee, place, parliament, polity: the answers

With exclusions: each question says what is not meant, without examples. By role: each question describes the role of the body, with examples in three languages.

| field | right: as built | right: with exclusions | right: by role | filled where nothing belongs: as built | filled where nothing belongs: with exclusions | filled where nothing belongs: by role | partly or wrong: as built | partly or wrong: with exclusions | partly or wrong: by role |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| addressee | 26 | 35 | 44 | 7 | 7 | 7 | 27 | 17 | 8 |
| place | 30 | 36 | 33 | 26 | 19 | 23 | 0 | 1 | 2 |
| parliament | 37 | 38 | 42 | 13 | 15 | 14 | 10 | 6 | 4 |
| polity | 47 | 40 | 44 | 4 | 4 | 6 | 8 | 16 | 9 |
| all four, of 240 | 140 | 149 | 163 | 50 | 45 | 50 | 45 | 40 | 23 |

### Events: the answers

Two lists, short: the names and the days in two lines as before, the name asked in a few words without the day. Pairs: one line, per event the day and then what happened; the line for the days falls away.

| field | right: as built | right: two lists, short | right: pairs | filled where nothing belongs: as built | filled where nothing belongs: two lists, short | filled where nothing belongs: pairs | partly or wrong: as built | partly or wrong: two lists, short | partly or wrong: pairs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| related affairs | 46 | 47 | 48 | 4 | 2 | 2 | 5 | 6 | 5 |
| acts and references | 14 | 14 | 15 | 4 | 4 | 3 | 16 | 15 | 13 |
| events (name) | 4 | 6 | 10 | 0 | 1 | 0 | 49 | 53 | 47 |
| events (date) | 17 | 27 | 32 | 0 | 0 | 0 | 34 | 32 | 25 |
| all four, of 240 | 81 | 94 | 105 | 8 | 7 | 5 | 104 | 106 | 90 |

| | as built | two lists, short | pairs |
|---|---:|---:|---:|
| documents with an event | 52 | 60 | 56 |
| names | 92 | 108 | 118 |
| names of more than 4 words | 63 | 37 | 40 |
| names with a day inside | 16 | 0 | 1 |
| names that stand literally in the text of the call | 21 | 42 | 42 |
| days | 77 | 100 | 104 |
| documents with as many names as days | 47 | 47 | 48 |
| days in the reference | 106 | 106 | 106 |
| of these named by the model | 54 | 64 | 81 |
| days of the model that are not in the reference | 21 | 26 | 23 |
| names in the reference | 109 | 109 | 109 |
| of these named, the same or meant the same | 18 | 31 | 46 |
| entries without a day (pairs only) | 0 | 0 | 14 |

### Through the pipeline, and what the first run showed

The first run with the questions by role, the events as pairs and French and Italian words in the conditions for session and department: 827 of 1 260 fields right, 788 before; addressee 47 against 24, parliament 50 against 42, session 38 against 41, the days of events 10 against 10.

- Of 102 days in the pairs 47 found no place on the page; 37 of these stand there written out with a French or Italian name of the month. The code that reads a day and looks for it on the page knew German names only. Built: the names of the months in German, French, Italian and English, with and without the marks on their letters.
- Of 112 names of events 65 found no place: the model words what happened. Built: where the name does not stand literally, the block of its day counts as the block named for it, under the rule of every named block (a word of the value must stand there), marked for a person.
- The stored answers of that run put through the changed code, no call: the days of events right in 20 of 60 documents against 10, the names in 9 against 7; 67 entries in the records against 31; 53 of the 106 days of the reference in the records against 28, 14 days there that the reference does not hold against 3.
- With the French and Italian words the session was asked in 23 documents instead of 11 and came out right in 38 instead of 41; these words were taken out again. The department was asked in 13 instead of 4 and came out right in 52 instead of 50; its words stay.

## Documents that come through with every field right

Counted on 13 October 2026 per document instead of per field. In the fourth run no document has every one of its 21 fields right: 3 to 14 fields a document are not, 7 in the middle. The fields are not right in different documents: with any three fields set right throughout, one document would come through, with any five three, with any eight seven.

Two patterns reach most documents. The model sets a value in a field for which the document prints nothing: 111 fields in 49 of the 60 documents (party 24, place 22, on behalf of 14, co-signers 8). And three lists taken from the running text differ from the reference in most documents: the names of events in 51, acts and references in 46, the days of events in 40.

- The place without the model, no call: where a line of a place and a day stands on the pages ("Liestal, 3. März 2020", "Lausanne, le 3 mars 2020"), the place is what stands before the day, else the field stays empty. As in the reference in 56 of 60 documents; the model: 34, with a place set in 22 documents that print none, mostly the polity. No list of places stands behind it.
- Of the 24 parties set where the reference has none, 9 are the group the reference holds under on behalf of, 9 a body of the document or its polity ("Kantonsrat", "Gran Consiglio"), 4 the submitter once more.
- Three ways to tell without a person which fields are right, none of which separates: fields without a mark are right in 69 % (822 of 1 186); the same value in a second run in 70 %, the model answers the same question alike; the model asked to check the values set, one call a document, 60 calls: of 402 values it confirms, 257 are right (64 %).

Fifth run, the place read by code, a party or on-behalf-of left out where it already stands under the submitters or as a body, a bare no taken as no value; 643 calls: 883 of 1 260 fields right (70.1 %) against 841. The place 56 against 34, the party 41 against 31, on behalf of 46 against 41, the polity 48 against 44; the title 39 against 41. Filled where nothing belongs 75 against 111. A person has fewer fields to set right in 38 documents, more in 6.

| | fourth run | fifth run |
|---|---:|---:|
| documents with all 21 fields right | 0 | 0 |
| the same, leaving aside acts and references and the names and days of events | 0 | 2 |
| at most one of these 18 fields not right | 4 | 9 |
| at most two | 10 | 17 |

What keeps the documents back after that, by the number of documents: the kind of document 24, title 21, date of submission 20, session 19, party 19, authors 17, number 17, co-signers 17. The reference is a draft; the three lists were left aside by the assistant, open.
