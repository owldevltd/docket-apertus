# Result: 3 000 documents through the chain

The run is complete: all 3 000 documents ran, the last on **16 October 2026, 03:14**; 32.2 hours for the documents with
a record.

Measured at commit `62e1fcb`; the code (`src/`, `data/`) has not changed since. The 3 000 documents were drawn from
OpenParlData's affairs (seed 20261013) beside the 300 of `results/three-hundred/`, none of them again: 1 000 per
language, 1 750 from cantons and 1 250 from municipalities, the five kinds of affair in turn. They go through the chain
with the model in a shuffled order (seed 20261014), one document at a time in a process of its own with a time limit of
30 minutes, one stream to the model; the input is the PDF only. The register of persons is loaded as in operation.

## Documents without a mark for a person

| | without a mark | 95 % interval |
|---|---:|---|
| all with a record | 2 088 of 2 996 (69.7 %) | 68.0–71.3 % |
| German | 705 of 1 000 (70.5 %) | 67.6–73.2 % |
| French | 718 of 996 (72.1 %) | 69.2–74.8 % |
| Italian | 665 of 1 000 (66.5 %) | 63.5–69.4 % |
| cantons | 1 353 of 1 750 (77.3 %) | 75.3–79.2 % |
| municipalities | 735 of 1 246 (59.0 %) | 56.2–61.7 % |
| motion | 656 of 897 (73.1 %) | 70.1–75.9 % |
| postulate | 273 of 390 (70.0 %) | 65.3–74.3 % |
| interpellation | 482 of 729 (66.1 %) | 62.6–69.5 % |
| question | 520 of 780 (66.7 %) | 63.3–69.9 % |
| parliamentary initiative | 157 of 200 (78.5 %) | 72.3–83.6 % |

2 996 documents have a record, from 78 parliaments. In the shuffled order the share after 500, 1 000, 1 500, 2 000,
2 500 and 2 996 documents: 69, 70, 70, 71, 70, 70 %.

## Language by level

| | cantons | municipalities |
|---|---:|---:|
| German | 433 of 600 (72.2 %) | 272 of 400 (68.0 %) |
| French | 439 of 600 (73.2 %) | 279 of 396 (70.5 %) |
| Italian | 481 of 550 (87.5 %) | 184 of 450 (40.9 %) |

## The run

- **Calls to the model:** 75 176 for the 2 996 documents with a record, 8 in the median per document (from 6 to 2 383).
- **Time:** 32.2 hours for these documents, 16 seconds in the median per document; the longest took 25 minutes. No
  document hit the time limit.
- **No record:** 4 of 3 000; they are not in the shares above, counted as documents with a mark the share of all is
  69.6 %. Each has pages declared many times the size of an A4 page, and the laptop of the run (6.9 GB usable) could not
  hold the image of such a page:
  - `fr-328297-868932` (French, municipalities, motion): 2 pages, the largest 3 816 × 5 256 points (40 times A4); the
    image of a page could not be allocated
  - `fr-334204-894309` (French, municipalities, interpellation): 3 pages, the largest 2 481 × 3 507 points (17 times
    A4); the process was stopped by the system (signal 9)
  - `fr-328299-868934` (French, municipalities, postulate): 2 pages, the largest 3 816 × 5 256 points (40 times A4); the
    image of a page could not be allocated
  - `fr-338307-922990` (French, municipalities, question): 2 pages, the largest 2 481 × 3 507 points (17 times A4); the
    process was stopped by the system (signal 9)

## Repeatable

The documents are not in the repository (`data/documents/README.md`); `runs.json` lists the 3 000 by their OpenParlData
ids in the order of the run. The run: every document through `python3 -m docket affairs --model --out <folder>`; a
document counts as without a mark when its record holds no value with `approve`.
