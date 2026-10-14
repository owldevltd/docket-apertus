# Result: 300 documents through the chain, measured at every station

Measured on 14 October 2026 at commit `cc7a4da`. The 300 documents are the 60 of the reference set and 240 drawn at
random from OpenParlData's affairs (seed 20261011; about 100 per language, cantons and municipalities, five kinds of
affair, 62 parliaments). 180 of them had never been run before; they went through the chain with the model in a shuffled
order (seed 20261013), one document at a time, one stream to the model: 179 in 133 minutes, about 5 000 calls, all
answered (3 984 counted; the calls of one scan of ten pages that hit the time limit of 30 minutes are not counted, and
the scan is left out). At this pace 3 000 documents would take about 67 000 calls and 37 hours on one stream. The other
120 had been run with the same questions; all 299 were put through the code of the commit again from the stored answers,
so every document is counted by the same code. The register of persons was loaded as in operation.

## Documents without a mark for a person

| | without a mark | 95 % interval |
|---|---:|---|
| all, with the register of persons | 209 of 299 (69.9 %) | 64.5–74.8 % |
| all, without the register | 214 of 299 (71.6 %) | 66.2–76.4 % |
| German | 68 of 95 (71.6 %) | 61.8–79.7 % |
| French | 69 of 97 (71.1 %) | 61.4–79.2 % |
| Italian | 66 of 99 (66.7 %) | 56.9–75.2 % |

The eight shipped documents of `data/documents/` are in no language row. In the shuffled order the share after 50, 100,
150, 200, 250 and 299 documents: 72, 73, 73, 70, 70, 70 %.

## Every station

| Station | Result |
|---|---|
| a text layer | 215 of 299 (72 %); 84 were read by the model |
| the image check marks at least one block | 54 |
| the kind of the document named | 298 |
| the parliament found | 222 (74 %) |
| the key from the affair's number | 204 (68 %) |
| answers of the model | 5 144 fields answered with 6 500 values: 4 650 placed literally or derived, 211 only at the block the model named (marked), 185 worded by the model, 1 454 with no place on the page and not taken |
| values left out by the rules after the model | 668 |

What holds the 90 documents with a mark, by documents (only this reason in brackets): the image check of a read block
47 (34), a value that stands only at the block the model named 42 (35), a person found in the register one character
off 12 (5), a worded text that leaves its document 2 (1), other 1 (1).

## A question across the parliaments

How many members back an affair? Per document the persons Docket reads as submitters and co-signers with a place on
the page, each name once, beside the persons the structured data hold for the same affair (the export of
contributors, fetched for the test only).

| | documents | the document names more than one person | the structured data hold at most one | the document names more than the data |
|---|---:|---:|---:|---:|
| all | 299 | 153 | 185 of 296 | 96 of 296 |
| cantons | 174 | 104 | 98 of 173 | 60 of 173 |
| municipalities | 125 | 49 | 87 of 123 | 36 of 123 |

Per parliament the backing differs in kind: in the median a document of Graubünden names 33 members (23 documents), of
Neuchâtel 10 (9), of Valais 2.5, of Ticino 2, of most municipalities one. The persons are as Docket read them; the
co-signers are among the weaker fields.

## Repeatable

The documents are not in the repository (`data/documents/README.md`); `draw.json` lists the 300 by their OpenParlData
ids. The run: every document through `python3 -m docket affairs --model --out <folder>` in a process of its own with a
time limit; the count: the stored answers of each document put through the code without the model, marks counted on the
record, the register loaded from OpenParlData's export of persons into the store.
