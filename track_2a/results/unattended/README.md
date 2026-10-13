# Run: documents that run through without a person

The run behind the entry "How many documents run through without a mark for a person?" in `docs/tests.md`.

- `result.md` – what holds a document for a person, the check of a worded text against its document, and how many
  documents carry no mark before and after, on the 60 documents of the reference set and on the 60 documents of
  `results/unseen/`.

The documents, the values and the calls are not kept here: the documents are not in the repository
(`data/documents/README.md`).

How it was made: `python3 -m docket affairs --model --out <folder> <the 60 PDFs>`; in every record the places that
carry `approve` counted, the blocks themselves left aside. The check of the summary was tried on the stored summaries
of both sets before it was built, no call.
