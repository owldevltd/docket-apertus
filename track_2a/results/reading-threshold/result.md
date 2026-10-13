# Result: the threshold of the check of a reading against the image

Measured on 13 October 2026. Every document without a text layer is held for a person: of the 60 documents of
`results/unseen/` 19 have none, and all 19 carry marks on blocks the check of the reading against the image set
(`src/docket/fluffy.py`, threshold 0.01). In `results/read.md` that check marks 16 of 16 readings that are not
identical, and 25 of 34 that are.

12 first pages with a text layer, of documents no threshold was set on, four each in German, French and Italian,
read as if they had no text layer: 203 elements, 269 calls. Against the text of the PDF: 92 identical, 102 near or
other, 9 empty; 5.4 % character errors. A reading counts as near when its edit distance is at most 10 % of the
reference.

| threshold | readings not identical that are marked (of 102) | identical readings that are marked (of 92) | not identical and not marked |
|---:|---:|---:|---:|
| 0.01 (as built) | 98 | 56 | 4 |
| 0.02 | 86 | 49 | 16 |
| 0.03 | 70 | 38 | 32 |
| 0.05 | 40 | 30 | 62 |
| 0.08 | 26 | 16 | 76 |
| 0.10 | 20 | 13 | 82 |
| 0.15 | 13 | 8 | 89 |
| 0.20 | 11 | 6 | 91 |

No threshold lets the identical readings through and keeps the others marked: with every step the marks on wrong
readings fall about as fast as those on right ones. The threshold stays at 0.01.

What the mark tells about the values, counted on the stored runs, no call. Values placed literally in documents
without a text layer, reference set: in a block with the mark 58 values, 39 of them in the reference under their
field (67 %); in a block without it 21 values, 20 in the reference (95 %); in documents with a text layer 607 values,
480 in the reference (79 %). On the documents of `results/unseen/`, the four fields OpenParlData holds: 24 of 31
values as OpenParlData with the mark (77 %), 10 of 10 without it, 93 of 112 in documents with a text layer (83 %).
