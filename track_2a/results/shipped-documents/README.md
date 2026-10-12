# Run: the whole chain over the eight shipped documents

The run behind five entries in `docs/tests.md`: "Do the ported rules build the blocks of the shipped documents, with
and without the model?", "Do the answers of the model land in the fields of the shipped documents?", "Is the kind of
a document told from its first page?", "Do the shipped documents get the key of their affair?" and "What does a run
over the shipped documents cost?". It is the last run of 8 October 2026; the earlier runs of that day, which the
entries also name, were not kept.

- `calls/<document>/read/call-<k>.json` – the page without a text layer read by the model (`aargau-scan` only,
  13 calls).
- `calls/<document>/sort/call-<k>.json` – the leftover elements of the first page sorted into kinds, one call a
  document.
- `calls/<document>/fields/call-<k>.json` – the fields asked in bundles of up to six, first over the first pages, then
  over the whole document; a field whose answer did not hold is asked once more. Four to six calls a document.
- `result.md` – calls, blocks, fields, places, kinds, keys and affairs of the run, per document.

Every call is the file the client wrote: the time (UTC), the tag of the step, the model, the temperature, the room for
the answer, the prompt, the size of the image in bytes where one was sent (the image itself is not in the log), the
duration, the status and the raw answer. The calls are numbered in their order within a step; the order of the
documents is the one of the table in `result.md`. The tags of the field calls carry the names of the fields as they
were on that day, in German; the fields have had English names since 10 October (`data/schema/fields.json`).

The names of people in the logs are replaced by made-up ones, a year and a date of birth printed beside two of them
are taken out, and the documents themselves are not in the repository
(`data/documents/README.md` says where each comes from). Where a name was replaced, a recount from these files will
not match the document.

How it was made, on 8 October 2026, with the eight PDFs in their folders and `LLM_API_KEY` in `.env`:

1. `make bench`, that is `python3 -m docket affairs --model --out storage/bench/documents data/documents/*/*.pdf`.
   60 calls.
2. `result.md`: counted from the logged calls and from the files the run wrote beside them (`<document>.json` with the
   blocks and the places, `<document>-fields.json` with the state of every field and the identity, `affairs/<key>.json`),
   against `data/documents/*/document.json`. These files hold the text of the documents and stay local.
