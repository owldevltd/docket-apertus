.PHONY: run fill test test-store bench bench-read reference knowledge vocabulary register app

export PYTHONPATH := src

# the daily affairs export of OpenParlData (NDJSON, gzip), for make knowledge
EXPORT ?= affairs.ndjson.gz

# Starts Postgres and the web server in Docker; the app is at http://localhost:8080. The store is empty on a
# clean checkout: `make bench` (with API_KEY in .env) fills it with the shipped documents, or run
# `python3 -m docket affairs --model --out storage/bench/documents <pdf...>` inside the container.
run:
	docker compose up --build

# Runs the affairs over the shipped documents inside the running container, into the Postgres store.
fill:
	docker compose exec docket python3 -m docket affairs --model --out storage/bench/documents data/documents/*/*.pdf

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
	python3 tests/kinds.py --pages=storage/tests/pages --documents=storage/tests/documents --out=storage/tests/kinds.md data/documents/*
	python3 tests/affairs.py --pages=storage/tests/pages --documents=storage/tests/documents --out=storage/tests/affairs.md --store=storage/tests/store data/documents/*
	python3 tests/server.py --store=storage/tests/store --pages=storage/tests/pages
	python3 tests/rules.py
	python3 tests/store.py
	python3 tests/vocabulary.py
	python3 tests/register.py
	python3 tests/admin.py data/documents/neuchatel-grand-conseil/*.pdf

# The store's operations over Postgres as well, inside the running container (after `make run`). The test
# works in a schema of its own and removes it at the end; the store in use is not touched.
test-store:
	docker compose exec docket sh -c 'python3 tests/store.py --postgres="$$DATABASE_URL"'

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

# Builds the browser app (Angular, in app/) into src/docket/app/, from where the Python server serves it.
# Node is needed for this build only, never to run the server; the Docker build does the same in its first
# stage. The built bundle is not committed.
app:
	cd app && npm ci --no-audit --no-fund && npx ng build

# Rebuilds the reference JSON beside the shipped documents from their text layer. A preparation step, its
# results are committed; needs poppler (pdftoppm, pdftotext, pdftohtml).
reference:
	python3 tools/reference.py

# Rebuilds the prior knowledge in data/knowledge/ from the affairs export of OpenParlData (EXPORT=<path>) and
# the names of the parliaments from its API, one page at a time with a pause. A preparation step, its results
# are committed; the type table is provisional, as OpenParlData calls its harmonised types.
knowledge:
	python3 tools/knowledge.py $(EXPORT)

# Fetches the stem of the vocabulary anew from OpenParlData's admin panel into data/knowledge/vocabulary.json:
# per parliament the names of its affair types with the harmonised type, the names of the events, the kinds
# of groups. 18 requests, one every four seconds. A preparation step, its result is committed; the store
# takes a newer stem at its next start and keeps what a person changed.
vocabulary:
	python3 tools/vocabulary.py

# Loads the persons of the parliaments from OpenParlData's exports into the store, so printed names can be told
# as persons: two files, fetched one after the other. Only id, name, parliament and party are taken; nothing of
# it is written into the repository. Inside the running container: docker compose exec docket python3
# tools/register.py. Run again with a newer export, it keeps what the register learnt.
register:
	python3 tools/register.py
