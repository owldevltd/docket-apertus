# Run: two digital first pages read as if they had no text layer

The runs behind the entry "Does the model read a page as its text layer has it?" in `docs/tests.md`.

- `calls/run-1/scan-page/call-<k>.json` – 13 calls of the first run: the page of `aargau-scan`, which has no text
  layer, read by the model.
- `calls/run-1/two-pages/call-<k>.json` – 35 calls of the first run: page 1 of `nidau-m185` (calls 1 to 20) and of
  `zuerich-219587` (calls 21 to 35), read as if they had no text layer.
- `calls/run-2/two-pages/call-<k>.json` – the same 35 calls 19 minutes later.
- `result.md` – both runs judged against the text layer, element by element, and what differs between them.

Every call is the file the client wrote: the time (UTC), the tag of the step (`read strip` for three elements cut out
and stacked, `read single` for one element with its surroundings), the model, the temperature, the room for the answer,
the prompt, the duration, the status and the raw answer. The image sent with a call is not in the log, only its size
in bytes. The calls are numbered in their order.

The names of people in the logs and in `result.md` are replaced by made-up ones, and the documents themselves are not
in the repository (`data/documents/README.md` says where each comes from).

How it was made, on 8 October 2026, with the three PDFs in their folders and `LLM_API_KEY` in `.env`:

1. Run 1: `python3 -m docket read --out storage/bench/pages data/documents/aargau-scan/aargau-scan.pdf`, then
   `python3 tests/read.py --out=storage/bench/read.md data/documents/nidau-m185 data/documents/zuerich-219587`
   (today `make bench-read`). 48 calls.
2. Run 2: the second command again. 35 calls. Between the two runs the label in the image of a single element was
   moved up by 4 pixels, as the work log notes; the prompts are the same.
3. `result.md`: the logged answers handed back to the reader call by call in place of the model, with the pages
   rendered anew from the PDFs, and judged by the functions of `tests/read.py`.
