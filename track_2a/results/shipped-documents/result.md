# Result: the whole chain over the eight shipped documents

One run of `python3 -m docket affairs --model` (`make bench`) on 8 October 2026 with swiss-ai/Apertus-v1.5-8B at
temperature 0, one call after the other. Everything below is counted from what that run left: the logged calls
(`calls/`), and the records, field reports and affairs it wrote (they hold the text and the names of the documents and
are not in the repository). It was counted before the names of people were replaced in the logs.

## Calls

| document | pages | read | sort | fields | calls | first call (UTC) | first call to last answer | time at the model | tokens in | tokens out |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| aargau-scan | 1 | 13 | 1 | 5 | 19 | 15:35:49 | 68 s | 28.8 s | 24486 | 1689 |
| ayent-6082 | 4 | 0 | 1 | 6 | 7 | 15:37:15 | 20 s | 8.1 s | 14503 | 893 |
| basel-137584 | 1 | 0 | 1 | 6 | 7 | 15:37:43 | 17 s | 5.0 s | 10790 | 422 |
| lugano-5192 | 3 | 0 | 1 | 5 | 6 | 15:38:14 | 15 s | 4.9 s | 6485 | 482 |
| neuchatel-grand-conseil | 1 | 0 | 1 | 4 | 5 | 15:38:36 | 12 s | 3.4 s | 4347 | 258 |
| nidau-m185 | 2 | 0 | 1 | 4 | 5 | 15:38:58 | 12 s | 4.6 s | 6575 | 443 |
| wettingen-115631 | 2 | 0 | 1 | 4 | 5 | 15:39:21 | 30 s | 4.3 s | 6502 | 409 |
| zuerich-219587 | 1 | 0 | 1 | 5 | 6 | 15:39:58 | 15 s | 4.8 s | 6714 | 432 |
| all eight | 15 | 13 | 8 | 39 | 60 | 15:35:49 | 264 s | 63.8 s | 80402 | 5028 |

Status of the 60 calls: 200: 60. The answer ended by itself in 59 calls and at the limit of its room in 1 (`ayent-6082`, fields call 4: a list of block ids cut off).
From the first call to the last answer the run took 264 seconds (4.4 minutes); the client pauses two seconds between calls and rests 20 seconds after the 50th. The time before the first call (rendering and geometry of the first document) is not in the logs.

## Blocks

| document | blocks | p | graphic | sec | list | def-list | sig-block |
|---|---:|---:|---:|---:|---:|---:|---:|
| aargau-scan | 14 | 7 | – | 4 | 2 | 1 | – |
| ayent-6082 | 51 | 48 | – | 1 | 2 | – | – |
| basel-137584 | 107 | 3 | 103 | 1 | – | – | – |
| lugano-5192 | 37 | 25 | 1 | 1 | 9 | – | 1 |
| neuchatel-grand-conseil | 10 | 8 | – | – | 1 | 1 | – |
| nidau-m185 | 23 | 14 | 2 | 5 | – | 2 | – |
| wettingen-115631 | 16 | 12 | 1 | 2 | – | 1 | – |
| zuerich-219587 | 15 | 11 | – | 2 | – | 1 | 1 |
| all eight | 273 | 128 | 107 | 16 | 14 | 6 | 2 |

A block is counted once, whatever it is nested in. The 103 `graphic` blocks of `basel-137584` carry no text.

## The 23 fields per document

| document | on the page | block from the model | not on the page | empty | missing | too short | fields |
|---|---:|---:|---:|---:|---:|---:|---:|
| aargau-scan | 16 | – | – | 7 | – | – | 23 |
| ayent-6082 | 7 | – | 7 | 8 | 1 | – | 23 |
| basel-137584 | 8 | 1 | 3 | 11 | – | – | 23 |
| lugano-5192 | 7 | – | 3 | 12 | – | 1 | 23 |
| neuchatel-grand-conseil | 5 | 1 | 3 | 14 | – | – | 23 |
| nidau-m185 | 14 | – | 2 | 7 | – | – | 23 |
| wettingen-115631 | 15 | 2 | – | 6 | – | – | 23 |
| zuerich-219587 | 14 | 2 | 2 | 5 | – | – | 23 |
| all eight | 86 | 6 | 20 | 70 | 1 | 1 | 184 |

The state is the one the field report of the run gives each field: **on the page** when the answer stands literally in a block, **block from the model** when it does not but the block the model names holds every word of it, **not on the page** when neither holds, **empty** when the model answered with a dash or the field was not asked because none of its words stands on the page, **missing** when no line of the answer belongs to the field, **too short** when the answer is under the shortest length.

## Values with a place

| document | places | literal | derived | cited | composed | marked for a person |
|---|---:|---:|---:|---:|---:|---:|
| aargau-scan | 19 | 15 | 3 | – | 1 | 16 |
| ayent-6082 | 11 | 9 | 1 | – | 1 | 2 |
| basel-137584 | 23 | 21 | 1 | – | 1 | 2 |
| lugano-5192 | 8 | 8 | – | – | – | 0 |
| neuchatel-grand-conseil | 7 | 5 | 1 | 1 | – | 2 |
| nidau-m185 | 24 | 23 | 1 | – | – | 1 |
| wettingen-115631 | 22 | 19 | 1 | 1 | 1 | 3 |
| zuerich-219587 | 18 | 15 | 1 | 1 | 1 | 3 |
| all eight | 132 | 115 | 9 | 3 | 5 | 29 |

A place is a value in the record that names the block it comes from and how it was found; the kind of the document is one of them. "Marked for a person" counts the places that carry `approve`.

## The kind of each document

| document | kind in the record of the run | kind noted in `document.json` | same |
|---|---|---|---|
| aargau-scan | submission | submission | yes |
| ayent-6082 | minutes | minutes | yes |
| basel-137584 | submission | submission | yes |
| lugano-5192 | – | minutes | no |
| neuchatel-grand-conseil | submission | submission | yes |
| nidau-m185 | submission | submission | yes |
| wettingen-115631 | submission | submission | yes |
| zuerich-219587 | submission | submission | yes |

7 of 8 documents carry a kind, 7 of 8 the kind noted in `document.json`. Without the model, `tests/kinds.py` gives 6 of 8 on the same documents (output of 12 October 2026): the page without a text layer has no words before it is read.

## The key of each document

| document | number read | key | way | number at OpenParlData | key of that number | same |
|---|---|---|---|---|---|---|
| aargau-scan | GR.19.196 | `nr-19196` | read number does not fit the form, found on the page ("19.196") | 19.196 | `nr-19196` | yes |
| ayent-6082 | – | `dok-communedayent-2024-03-28` | no number read | – | – | – |
| basel-137584 | 23.5448.01 | `nr-235448` | read number | 23.5448 | `nr-235448` | yes |
| lugano-5192 | – | `nr-2001` | found on the page ("2001") | – | – | – |
| neuchatel-grand-conseil | DSAS | `dok-2009-02-09` | no number read | – | – | – |
| nidau-m185 | nid 0.1.6.2 | `nr-0162` | read number does not fit the parliament's form | M 185 | `nr-m185` | no |
| wettingen-115631 | 2017-0683 | `nr-20170683` | read number | 2017-0683 | `nr-20170683` | yes |
| zuerich-219587 | 357/2018 | `nr-3572018` | read number | 357/2018 | `nr-3572018` | yes |

4 of the 5 documents with a known affair get the key of the number OpenParlData holds for it. "Key of that number" is the number in lower case without separators behind `nr-`, as the keys were formed on 8 October; since 11 October a key also names the parliament. The numbers of OpenParlData stand in `data/documents/*/document.json`; they were fetched once for the tests, the pipeline fetches nothing.

## The affairs

| affair | documents | type read from the document | harmonised type of the run | harmonised type at OpenParlData |
|---|---:|---|---|---|
| `dok-2009-02-09` | 1 | – | – | – |
| `dok-communedayent-2024-03-28` | 1 | Délivrance d'une autorisation d'exploiter | – | – |
| `nr-0162` | 1 | Motion | Motion | Motion |
| `nr-19196` | 1 | Antrag | Regierungsgeschäft | Ergänzungsantrag |
| `nr-2001` | 1 | – | – | – |
| `nr-20170683` | 1 | Motion | Motion | Motion |
| `nr-235448` | 1 | Standesinitiative | – | Ergänzungsantrag |
| `nr-3572018` | 1 | Standesinitiative | – | Parlamentarische Initiative |

8 documents give 8 affairs.

## Not in the files

- The run time of 4.5 minutes and the peak memory of 0.6 GB (read from the process every five seconds) are in the work log only.
- That all eight records were valid against the contract was reported by the run; it is not checked again here, the contract has changed since.
- The comparison of the Nidau affair with the reference run of 6 October (47 of 48 values the same) is in the work log only; the reference run is not among the files of this run.
