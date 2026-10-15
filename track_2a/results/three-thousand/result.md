# Result: 3 000 documents through the chain

State: **15 October 2026, 16:39**, the run is still going; 2 005 of 3 000 documents have run. The order is shuffled, so
every state is a random sample of the 3 000.

Measured at commit `62e1fcb`; the code (`src/`, `data/`) has not changed since. The 3 000 documents were drawn from
OpenParlData's affairs (seed 20261013) beside the 300 of `results/three-hundred/`, none of them again: 1 000 per
language, 1 750 from cantons and 1 250 from municipalities, the five kinds of affair in turn. They go through the chain
with the model in a shuffled order (seed 20261014), one document at a time in a process of its own with a time limit of
30 minutes, one stream to the model; the input is the PDF only. The register of persons is loaded as in operation.

## Documents without a mark for a person

| | without a mark | 95 % interval |
|---|---:|---|
| all with a record | 1 413 of 2 001 (70.6 %) | 68.6–72.6 % |
| German | 490 of 678 (72.3 %) | 68.8–75.5 % |
| French | 469 of 651 (72.0 %) | 68.5–75.4 % |
| Italian | 454 of 672 (67.6 %) | 63.9–71.0 % |
| cantons | 930 of 1 185 (78.5 %) | 76.1–80.7 % |
| municipalities | 483 of 816 (59.2 %) | 55.8–62.5 % |
| motion | 449 of 600 (74.8 %) | 71.2–78.1 % |
| postulate | 183 of 256 (71.5 %) | 65.7–76.7 % |
| interpellation | 324 of 494 (65.6 %) | 61.3–69.6 % |
| question | 351 of 519 (67.6 %) | 63.5–71.5 % |
| parliamentary initiative | 106 of 132 (80.3 %) | 72.7–86.2 % |

2 001 documents have a record, from 78 parliaments. In the shuffled order the share after 500, 1 000, 1 500 and 2 001
documents: 69, 70, 70, 71 %.

## Language by level

| | cantons | municipalities |
|---|---:|---:|
| German | 314 of 424 (74.1 %) | 176 of 254 (69.3 %) |
| French | 293 of 401 (73.1 %) | 176 of 250 (70.4 %) |
| Italian | 323 of 360 (89.7 %) | 131 of 312 (42.0 %) |

## The run

- **Calls to the model:** 47 279 for the 2 001 documents with a record, 8 in the median per document (from 6 to 2 383).
- **Time:** 21.6 hours for these documents, 17 seconds in the median per document; the longest took 25 minutes. No
  document hit the time limit.
- **No record:** 4 of 2 005; they are not in the shares above, counted as documents with a mark the share of all is
  70.5 %. Each has pages declared many times the size of an A4 page, and the laptop of the run (6.9 GB usable) could not
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
