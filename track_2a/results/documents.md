# The whole chain over the shipped documents

Run of 8 October 2026, `make bench`, `python -m docket document --model`: pages rendered, geometry, text layer,
the scan page read by the model, blocks by the bridge, the leftover elements of the first pages sorted by the
model, the record validated against the contract. Apertus 8B at the CSCS endpoint, temperature 0, one call at
a time. 21 calls for the eight documents, 2.7 minutes.

| Document | Pages | Blocks | Of which | Rest | Calls | Contract | Time |
|---|---:|---:|---|---:|---:|---|---:|
| aargau-scan | 1 | 14 | p 7, sec 4, list 2, def-list 1 | 0 | 14 | valid | 60 s |
| ayent-6082 | 4 | 51 | p 48, list 2, sec 1 | 0 | 1 | valid | 26 s |
| basel-137584 | 1 | 107 | graphic 103, p 3, sec 1 | 0 | 1 | valid | 10 s |
| lugano-5192 | 3 | 37 | p 25, list 9, sec 1, sig-block 1, graphic 1 | 0 | 1 | valid | 20 s |
| neuchatel-grand-conseil | 1 | 10 | p 8, def-list 1, list 1 | 0 | 1 | valid | 9 s |
| nidau-m185 | 2 | 23 | p 14, sec 5, def-list 2, graphic 2 | 0 | 1 | valid | 14 s |
| wettingen-115631 | 2 | 16 | p 12, sec 2, def-list 1, graphic 1 | 0 | 1 | valid | 14 s |
| zuerich-219587 | 1 | 15 | p 11, sec 2, def-list 1, sig-block 1 | 0 | 1 | valid | 9 s |

The scan page costs 13 calls for the reading and one for the sorting; every digital document needs one call,
since the bridge leaves few elements over on a first page. The Nidau record has the same blocks as the frozen
reference run of 6 October (14 paragraphs, 5 sections, 2 labelled lists, 2 images). The 103 images of the Basel
page are the inkless fragments the geometry leaves on a dense page; they carry no text and are harmless, and they
are a known limit of the geometry on such pages.
