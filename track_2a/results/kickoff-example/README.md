# Run: the kickoff example, two runs

The runs behind two entries in `docs/tests.md`: "Which values of the kickoff example come out as the page prints
them?" (run 1) and "Does pairing a column of labels with the column of values repair the kickoff example?" (run 2).

- `calls/run-1/sort/call-1.json`, `calls/run-1/fields/call-<k>.json` – the six calls of the run with the code as it
  stood in the night of 11 October 2026.
- `calls/run-2-columns-paired/sort/call-1.json`, `calls/run-2-columns-paired/fields/call-<k>.json` – the six calls of
  the run six minutes later, with one change in the working tree: a column of labels and the column of values beside
  it become one list, line by line. The change was taken out again after the run and built in later that night
  (`src/docket/text/layer.py`, `src/docket/document/bridge.py`).
- `result.md` – calls, blocks and every field of both runs, beside what the page prints and what OpenParlData holds.

Every call is the file the client wrote: the time (UTC), the tag of the step, the model, the temperature, the room for
the answer, the prompt, the duration, the status and the raw answer. No image is sent in these calls. The calls are
numbered in their order within a step: the sorting comes first, then the fields.

The names of people in the logs and in `result.md` are replaced by made-up ones, and the document itself is not in the
repository (`data/documents/README.md` says where it comes from).

How it was made, with the PDF in its folder and `LLM_API_KEY` in `.env`:

1. `python3 -m docket affairs --model --out <a folder> data/documents/nidau-m185/nidau-m185.pdf`, with `STORAGE_DIR`
   set to a folder of its own so that the store in use stays untouched. Six calls.
2. The same again with the change in place. Six calls.
3. `result.md`: counted from the logged calls and from the field report and the record each run wrote
   (`nidau-m185-fields.json`, `nidau-m185.json`), against `data/documents/nidau-m185/document.json`. These files hold
   the text of the document and stay local.
