# Run: how long a document takes

The run behind the entry "How long does a document take, and what would the whole stock take?" in `docs/tests.md`.

- `result.md` – the time per document in two runs with the model and one without, and the stock calculated from it.
- `documents.csv` – every document: pages, whether it has a text layer, and per run the calls, the seconds at the model
  and the wall clock.
- `calls.csv` – one row per call to the model in both runs: the document, the kind of call (`read` a page element read,
  `sort` the leftover elements sorted, `fields` the fields asked), the duration in milliseconds as the client logged it,
  the status and the tokens. The prompts and answers of these calls are not kept here: they are the text of the
  documents, which are not in the repository (`data/documents/README.md`).

How it was made: `python3 -m docket affairs --model --out <folder> <the 60 PDFs>`, once with the client as it was and
once with the pace as built (`src/docket/model/client.py`); then the same command without `--model`. The wall clock per
document is the one the command prints, the time at the model the sum of the durations in the logged calls.
