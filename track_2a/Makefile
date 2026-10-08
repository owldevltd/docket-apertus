.PHONY: run test bench bench-read reference knowledge

export PYTHONPATH := src

# the daily affairs export of OpenParlData (NDJSON, gzip), for make knowledge
EXPORT ?= affairs.ndjson.gz

# Replace with the command that starts the project in a Docker container,
# e.g. `docker compose up`. It must work from a clean checkout.
run:
	@echo "make run is not implemented yet — edit this Makefile"; exit 1

# Runs the geometry and the text layer over the shipped documents and measures them against the text layer of
# their PDFs, builds the blocks and the record, and looks for the known values of the affairs on the first
# pages. No model call, no network; needs poppler to render the pages. Results and control images land in
# storage/tests/.
test:
	python3 -m docket analyze --out storage/tests/pages data/documents/*/*.pdf
	python3 tests/sources.py --got=storage/tests/pages --out=storage/tests/sources.md data/documents/*
	python3 tests/text.py --got=storage/tests/pages data/documents/*
	python3 tests/blocks.py --pages=storage/tests/pages --out=storage/tests/documents data/documents/*
	python3 tests/fields.py --pages=storage/tests/pages --documents=storage/tests/documents --out=storage/tests/fields.md data/documents/*
	python3 tests/affairs.py --pages=storage/tests/pages --documents=storage/tests/documents --out=storage/tests/affairs.md data/documents/*

# With the model: the whole chain over the shipped documents, the scan page read, the leftover elements of the
# first pages sorted, the fields asked and placed, every document keyed and the documents of one key merged
# into one affair, every record validated. Needs API_KEY in .env (copy .env.example). About 60 calls, one
# after the other, under five minutes. Results, the raw exchange and the control images land in storage/bench/;
# the committed run is in results/.
bench:
	@test -f .env || { echo "copy .env.example to .env and set API_KEY"; exit 1; }
	python3 -m docket affairs --model --out storage/bench/documents data/documents/*/*.pdf

# With the model: two digital first pages read as if they had no text layer, held against their text layer.
# About 35 calls, under three minutes.
bench-read:
	@test -f .env || { echo "copy .env.example to .env and set API_KEY"; exit 1; }
	python3 tests/read.py --out=storage/bench/read.md data/documents/nidau-m185 data/documents/zuerich-219587

# Rebuilds the reference JSON beside the shipped documents from their text layer. A preparation step, its
# results are committed; needs poppler (pdftoppm, pdftotext, pdftohtml).
reference:
	python3 tools/reference.py

# Rebuilds the prior knowledge in data/knowledge/ from the affairs export of OpenParlData (EXPORT=<path>) and
# the names of the parliaments from its API, one page at a time with a pause. A preparation step, its results
# are committed; the type table is provisional, as OpenParlData calls its harmonised types.
knowledge:
	python3 tools/knowledge.py $(EXPORT)
