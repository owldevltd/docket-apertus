# The whole chain over the shipped documents

Run of 8 October 2026, `make bench`, `python -m docket document --model`: pages rendered, geometry, text layer,
the scan page read by the model, blocks by the bridge, the leftover elements of the first pages sorted by the
model, the fields asked over the first pages and over the whole document, every answer placed by code, the
record validated against the contract. Apertus 8B at the CSCS endpoint, temperature 0, one call at a time.
60 calls for the eight documents, 4.5 minutes.

| Document | Pages | Blocks | Calls | On the page | Block from the model | Not on the page | Empty | Places | Approve | Contract | Time |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|
| aargau-scan | 1 | 14 | 19 | 17 | 1 | 0 | 5 | 19: literal 16, derived 2, composed 1 | 16 | valid | 69 s |
| ayent-6082 | 4 | 51 | 6 | 8 | 0 | 5 | 10 | 8: literal 7, composed 1 | 1 | valid | 34 s |
| basel-137584 | 1 | 107 | 7 | 8 | 1 | 3 | 11 | 22: literal 21, composed 1 | 1 | valid | 25 s |
| lugano-5192 | 3 | 37 | 6 | 7 | 0 | 3 | 12 | 8: literal 8 | 0 | valid | 29 s |
| neuchatel-grand-conseil | 1 | 10 | 5 | 5 | 1 | 2 | 15 | 6: literal 5, cited 1 | 1 | valid | 18 s |
| nidau-m185 | 2 | 23 | 5 | 14 | 0 | 2 | 7 | 22: literal 22 | 0 | valid | 23 s |
| wettingen-115631 | 2 | 16 | 5 | 15 | 2 | 0 | 6 | 21: literal 19, cited 1, composed 1 | 2 | valid | 42 s |
| zuerich-219587 | 1 | 15 | 7 | 15 | 1 | 2 | 5 | 17: literal 15, cited 1, composed 1 | 2 | valid | 26 s |

The columns "on the page" to "empty" count the 23 fields of the fields file per document (Lugano has one more
field whose answer was too short). "Places" counts the values that went into the record with a source; "approve"
the places a person has to look at: every cited or composed value, and every value from a block the reading
marked, which is why the scan has 16.

Over the eight: 184 field cells, 89 on the page, 6 with a block from the model, 17 not on the page, 71 empty;
123 places, 113 literal, 2 derived, 3 cited, 5 composed; 23 to look at. The scan page costs 13 calls for the
reading and one for the sorting; every digital document needs one call for the sorting and four to six for the
fields (two to three bundles over the first pages, one to two over the whole document, a follow-up where a line
was missing or refused).

The Nidau record holds 43 of the 48 values of the reference run of 6 October: the five others are the
harmonised type, which the next step sets, and one keyword the model did not return this time. Between the
three runs of the day the states of three cells changed; the model is not fully deterministic at temperature 0.

Known limits, visible in the records: the literal rule accepts a value that stands on the page in the wrong
field ("Lüthold Katrin, SP Kern" as one submitter, because the page writes the names and parties in one
line); the events of a document get one date where the model returns the dates in one line; the summary has a
place only when the model names a block with a word of it, so three of eight documents have none. The 103
images of the Basel page are the inkless fragments the geometry leaves on a dense page; they carry no text and
are harmless, and they are a known limit of the geometry on such pages.
