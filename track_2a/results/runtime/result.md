# Result: how long a document takes, and what the whole stock would take

Measured on 12 October 2026 on the 60 documents of the reference set (52 drawn in German, French and Italian and the eight listed in `data/documents/README.md`), `python3 -m docket affairs --model`, the PDFs as the only input, with Apertus 8B at the CSCS endpoint, one call after the other. Machine: 4 cores, 8 threads (Intel i5-1135G7), 6.9 GB of memory; the pipeline computes on one core.

Run 1, the pace of the client as it was (two seconds before every call, twenty before every fiftieth): 583 calls, 583 × 200. Run 2, the pace as built (ten calls one after the other, then half a second): 583 calls, 583 × 200. A third run without the model timed the computing alone. During the first 33 documents of run 1 other measurements ran on the machine; its seconds per document are therefore given for the 27 documents after that only.

## Per document

| | documents | pages | calls | at the model | wall clock, mean | median | tokens in | tokens out |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| run 1, all (wall clock: 27 documents on the free machine, 6 of them without a text layer) | 60 | 2.9 | 9.7 | 13.0 s | 57.5 s | 31 s | 14628 | 746 |
| run 1, with a text layer | 51 | 3.1 | 5.9 | 7.6 s | 30.9 s | 28 s | 9310 | 463 |
| run 1, without a text layer (pages read by the model) | 9 | 2.1 | 31.4 | 43.1 s | 150.7 s | 118 s | 44768 | 2352 |
| run 2, all | 60 | 2.9 | 9.7 | 9.8 s | 24.8 s | 17 s | 14627 | 747 |
| run 2, with a text layer | 51 | 3.1 | 5.9 | 5.2 s | 20.6 s | 15 s | 9307 | 466 |
| run 2, without a text layer | 9 | 2.1 | 31.4 | 35.5 s | 48.7 s | 35 s | 44773 | 2337 |
| run 2, the same 27 documents as the wall clock of run 1 | 27 | 2.4 | 13.1 | 13.9 s | 26.4 s | 18 s | 19055 | 1023 |

Without the model the pipeline needs 14.8 s a document on these 60, 5.1 s a page: rendering, geometry, blocks, the record. A profile over two documents (7 pages) puts 44 % of that into one function that scales the page image (`src/docket/page/raster.py`, `scale_box`), 32 % into writing the control image of every page (`src/docket/page/painter.py`) and 4 % into rendering.

The whole run over the 60 documents: run 1 90 minutes (stretched by the other measurements), run 2 25 minutes; at the model 13.0 and 9.8 minutes.

Documents without a text layer: 9 of 60 documents, 283 of 583 calls and 5.3 of 9.8 minutes at the model in run 2; a page that is read costs 12 calls.

## The whole stock, calculated

A multiplication of the means of run 2, one document after the other on one stream to the model and one core; not a measurement. OpenParlData held 325 599 affairs and 907 472 documents in its API on 4 October 2026.

| documents | calls | tokens in | at the model | computing without the model (one core) | as measured in run 2 | with the pace of run 1 |
|---:|---:|---:|---:|---:|---:|---:|
| 325 599 | 3.2 million | 4.8 billion | 37 days | 56 days | 93 days | 167 days |
| 907 472 | 8.8 million | 13.3 billion | 102 days | 156 days | 260 days | 465 days |

The last column adds the pauses of the pace before, two seconds a call, to run 2. The documents of the reference set are short, 2.9 pages on average; the set the geometry was measured on had 482 pages in 64 documents (7.5 a document). The computing grows with the pages: at 7.5 pages a document it alone would be 144 core-days for 325 599 documents and 401 for 907 472. How the time at the model grows with the length was not measured. The computing can be spread over cores; whether the endpoint takes several streams at once was not tested. A record is 31 KB on average: about 10 GB for 325 599 documents, 28 GB for 907 472.
