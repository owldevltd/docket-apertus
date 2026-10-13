# Run: documents the changes were not made on

The run behind the entry "Do the changes hold on documents they were not made on?" in `docs/tests.md`.

- `result.md` – the 60 documents through the pipeline before and after the changes of 12 and 13 October, each of four
  fields held against what OpenParlData holds for the affair; and the two rules that did not hold.
- `fields.csv` – every one of the four fields of every document with its state before and after: as OpenParlData,
  another value, empty.

The documents, the values and the calls are not kept here: the documents are not in the repository
(`data/documents/README.md`), and what OpenParlData holds was fetched for the test only; the pipeline itself takes
nothing from there.

How it was made: `python3 -m docket affairs --model --out <folder> <the 60 PDFs>`, once in a copy of the repository at
the commit before the changes and once in the repository as it is; the placed values of number, title, type and date
of each run held against the values of OpenParlData.
