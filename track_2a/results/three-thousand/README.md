# Run: 3 000 documents through the chain

The same measure as `results/three-hundred/`, ten times as large: 3 000 further documents of OpenParlData, none of them
among the 300, through the chain with the model. The run is still going; the files hold the state named at the top of
`result.md`. The order is shuffled, so every state is a random sample of the 3 000.

- `result.md` – the share of documents without a mark for a person, with intervals, per language, level and kind of
  affair, the course over the shuffled order, the calls and the time, and the documents without a record.
- `runs.json` – the 3 000 documents in the order of the run, each by its OpenParlData affair and document id, with
  language, level, kind of affair and parliament, and for the documents run so far the result.

The documents, the values and the calls are not kept here: the documents are not in the repository
(`data/documents/README.md`).
