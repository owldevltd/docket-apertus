# The whole chain over the shipped documents

Run of 8 October 2026, `make bench`, `python -m docket affairs --model`: pages rendered, geometry, text layer,
the scan page read by the model, blocks by the bridge, the leftover elements of the first pages sorted by the
model, the fields asked over the first pages and over the whole document, every answer placed by code, the
kind of every document from its first page, every document keyed, the documents of one key merged into one
affair, every record validated against the contract and written into the store. Apertus 8B at the CSCS
endpoint, temperature 0, one call at a time. 60 calls for the eight documents, 4.5 minutes; the chain's
peak memory with one document in flight was 0.6 GB.

| Document | Pages | Blocks | Calls | On the page | Block from the model | Not on the page | Empty | Places | Approve | Kind | Key | Contract | Time |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---|---|---:|
| aargau-scan | 1 | 14 | 19 | 16 | 0 | 0 | 7 | 19: literal 15, derived 3, composed 1 | 16 | submission | nr-19196, found on the page | valid | 72 s |
| ayent-6082 | 4 | 51 | 7 | 7 | 0 | 7 | 8 | 11: literal 9, derived 1, composed 1 | 2 | minutes | dok-communedayent-2024-03-28 | valid | 39 s |
| basel-137584 | 1 | 107 | 7 | 8 | 1 | 3 | 11 | 23: literal 21, derived 1, composed 1 | 2 | submission | nr-235448, read | valid | 25 s |
| lugano-5192 | 3 | 37 | 6 | 7 | 0 | 3 | 12 | 8: literal 8 | 0 | – | nr-2001, found on the page | valid | 29 s |
| neuchatel-grand-conseil | 1 | 10 | 5 | 5 | 1 | 3 | 14 | 7: literal 5, derived 1, cited 1 | 2 | submission | dok-2009-02-09 | valid | 18 s |
| nidau-m185 | 2 | 23 | 5 | 14 | 0 | 2 | 7 | 24: literal 23, derived 1 | 1 | submission | nr-0162, read | valid | 23 s |
| wettingen-115631 | 2 | 16 | 5 | 15 | 2 | 0 | 6 | 22: literal 19, derived 1, cited 1, composed 1 | 3 | submission | nr-20170683, read | valid | 41 s |
| zuerich-219587 | 1 | 15 | 6 | 14 | 2 | 2 | 5 | 18: literal 15, derived 1, cited 1, composed 1 | 3 | submission | nr-3572018, read | valid | 22 s |

The columns "on the page" to "empty" count the 23 fields of the fields file per document (Ayent has one field
without an answer, Lugano one whose answer was too short). "Places" counts the values that went into the record
with a source, the document's kind among them; "approve" the places a person has to look at: every cited or
composed value, every kind, and every value from a block the reading marked, which is why the scan has 16.

Over the eight: 184 field cells, 86 on the page, 6 with a block from the model, 20 not on the page, 70 empty;
132 places, 115 literal, 9 derived, 3 cited, 5 composed; 29 to look at. The scan page costs 13 calls for the
reading and one for the sorting; every digital document needs one call for the sorting and four to six for the
fields.

## The kinds

Seven of the eight documents get their kind from the words of the first page: six submissions (the sections
"Antrag", "Begründung" or "Text", or the label "Antrag" or "Question" in the headline), the Ayent sitting as
minutes ("Séance" in the headline). Lugano's agenda has no word of the list in its headline and stays without
a kind, open in the review. The scan gets its kind only after the reading, from the section "Text".

## The affairs

Eight documents give eight affairs (`affairs/<key>.json`, `affairs.ndjson`), all valid, all in the store. Of
the five documents with a known affair at OpenParlData, four get the key of the API's number: Basel, Wettingen
and Zürich from the read number (Basel prints the document number "23.5448.01", the document suffix comes off),
Aargau from the page, since the read "GR.19.196" does not have the parliament's form and "19.196" on the page
does. Nidau gets "nr-0162" from the read file reference "nid 0.1.6.2": the read number does not fit the form
"a999" of Nidau, and the page prints "M 185" as two words, which the search by form does not join. The three
documents without a known affair get a key from the page (Lugano "2001", a year that has the form "9999" of
Lugano) or a weak key from place and date.

The harmonised type comes from the table for Nidau and Wettingen (Motion) and Aargau ("Antrag" falls to 88 %
on government business in the export; the API holds this affair as an amendment); "Standesinitiative" is not
in the table with enough affairs, so Basel and Zürich keep the printed label only. The Nidau affair holds the
values of the reference run of 6 October but for a keyword the model did not return this time.

The parliament behind a document is resolved from the read place and parliament names against the 97 named
bodies; with that many bodies the place name alone is ambiguous where a canton and its capital share a name
(Zürich, Neuenburg, Basel), and the parliament name "Parlament" or "Bundesversammlung" does not settle it. The
key does not depend on it where the number is read; the check against the parliament's number form does.

Known limits, visible in the records: the literal rule accepts a value that stands on the page in the wrong
field ("Lüthold Katrin, SP Kern" as one submitter, because the page writes the names and parties in one
line); the events of a document get one date where the model returns the dates in one line; the summary has a
place only when the model names a block with a word of it, so three of eight documents have none. The 103
images of the Basel page are the inkless fragments the geometry leaves on a dense page; they carry no text and
are harmless, and they are a known limit of the geometry on such pages.
