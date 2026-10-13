# Run: the threshold of the check of a reading against the image

The run behind the entry "Is there a threshold that lets right readings through and still finds the wrong ones?" in
`docs/tests.md`.

- `result.md` – 12 first pages with a text layer read as if they had none, every read element with its deviation
  from the image and its judgement against the text layer; what each threshold marks.

The pages and the calls are not kept here: the documents are not in the repository (`data/documents/README.md`).

How it was made: as `tests/read.py` reads a page (the text elements set back to unknown, then `read_page`), on the
first pages of 12 of the documents of `results/unseen/`, four each in German, French and Italian; per element the
deviation the check measures and the state against the text of the PDF.
