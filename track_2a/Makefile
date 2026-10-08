.PHONY: run test bench reference

export PYTHONPATH := src

# Replace with the command that starts the project in a Docker container,
# e.g. `docker compose up`. It must work from a clean checkout.
run:
	@echo "make run is not implemented yet — edit this Makefile"; exit 1

# Runs the geometry and the text layer over the shipped documents and measures them against the text layer of
# their PDFs. No model call, no network; needs poppler to render the pages. Results and control images land in
# storage/tests/.
test:
	python3 -m docket analyze --out storage/tests/pages data/documents/*/*.pdf
	python3 tests/sources.py --got=storage/tests/pages --out=storage/tests/sources.md data/documents/*
	python3 tests/text.py --got=storage/tests/pages data/documents/*
	python3 tests/blocks.py --pages=storage/tests/pages --out=storage/tests/documents data/documents/*

# With the model: the whole chain over the shipped documents (the scan page read, the leftover elements of the
# first pages sorted), and two digital first pages read as if they had no text layer, held against their text
# layer. Needs API_KEY in .env (copy .env.example). About 65 calls, one after the other, under five minutes.
# Results and the raw exchange land in storage/bench/; the committed run is in results/.
bench:
	@test -f .env || { echo "copy .env.example to .env and set API_KEY"; exit 1; }
	python3 -m docket document --model --out storage/bench/documents data/documents/*/*.pdf
	python3 tests/read.py --out=storage/bench/read.md data/documents/nidau-m185 data/documents/zuerich-219587

# Rebuilds the reference JSON beside the shipped documents from their text layer. A preparation step, its
# results are committed; needs poppler (pdftoppm, pdftotext, pdftohtml).
reference:
	python3 tools/reference.py
