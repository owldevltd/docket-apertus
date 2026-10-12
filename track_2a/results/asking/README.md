# Run: how the fields are asked

The run behind four entries in `docs/tests.md`: "Can code decide where a value set in two fields belongs?", "Do the
contributor fields come out right when they are asked in one call?", "Does the first field of a call draw a value?" and
"Are keywords set where the document prints none?".

- `result.md` – three runs through the whole pipeline side by side, field by field, and the trials on the answers of
  the model that led from one to the next.
- `fields.csv` – every field of every document with its state in the three runs: right, right but for the spelling,
  rightly empty, partly, wrong, filled where nothing belongs, missing.

The prompts, the answers and the values are not kept here: they are the text of the documents, which are not in the
repository (`data/documents/README.md`). The reference is a draft and not in the repository either.

How it was made: `python3 -m docket affairs --model --out <folder> <the 60 PDFs>` at three states of
`data/schema/fields.json` and `src/docket/fields/filler.py`; the fields of each run held against the reference as in
`docs/evidence.md`, section 6. For the trials on the answers the stored call of a document was sent again with other
lines for the fields, through the client of the repository.
