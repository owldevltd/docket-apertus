.PHONY: run fill test test-store bench bench-read reference knowledge vocabulary register rows learn mapping
.PHONY: questions app translations

export PYTHONPATH := src

# the daily affairs export of OpenParlData (NDJSON, gzip), for make knowledge
EXPORT ?= affairs.ndjson.gz

# Starts Postgres and the web server in Docker; the app is at http://localhost:8080. On a clean checkout the
# store is empty and stays so until a PDF is handed in: the parliamentary documents are not in the repository
# (data/documents/README.md). Where they lie in their folders with the runs stored beside them
# (data/documents/*/run.json), the server forms their affairs from these, without the model and without a key;
# it takes about two minutes and shows under the runs of the admin. With LLM_API_KEY set (in the shell or in
# .env), `make fill` runs them with the model.
run:
	docker compose up --build

# Runs the affairs over the shipped documents inside the running container, into the Postgres store.
fill:
	docker compose exec docket python3 -m docket affairs --model --out storage/bench/documents data/documents/*/*.pdf

# Runs the geometry and the text layer over the shipped documents and measures them against the text layer of
# their PDFs, builds the blocks and the record, and looks for the known values of the affairs on the first
# pages; then forms the affairs again from the stored run of every shipped document and compares them with
# the stored ones, directly and by way of the rows, takes decisions on them and lays them into a second JSON
# of another shape, fills an empty store with them as a clean checkout does, and answers the three questions
# across the parliaments from it. No model call, no network; needs poppler to render the pages. Results and
# control images land in storage/tests/.
# The parliamentary documents are not in the repository (data/documents/README.md says where each comes from and
# how to put them back). Without them only the tests that need no document run.
DOCUMENTS := $(wildcard data/documents/*/*.pdf)

test:
ifeq ($(DOCUMENTS),)
	@echo "No document under data/documents: only the tests that need none run. See data/documents/README.md."
	python3 tests/client.py
	python3 tests/bundles.py
	python3 tests/settle.py
	python3 tests/rules.py
	python3 tests/store.py
	python3 tests/vocabulary.py
	python3 tests/register.py
	python3 tests/mapping.py
	python3 tests/translations.py
else
	python3 -m docket analyze --out storage/tests/pages data/documents/*/*.pdf
	python3 tests/sources.py --got=storage/tests/pages --out=storage/tests/sources.md data/documents/*
	python3 tests/text.py --got=storage/tests/pages data/documents/*
	python3 tests/blocks.py --pages=storage/tests/pages --out=storage/tests/documents data/documents/*
	python3 tests/fields.py --pages=storage/tests/pages --documents=storage/tests/documents --out=storage/tests/fields.md data/documents/*
	python3 tests/kinds.py --pages=storage/tests/pages --documents=storage/tests/documents --out=storage/tests/kinds.md data/documents/*
	python3 tests/affairs.py --pages=storage/tests/pages --documents=storage/tests/documents --out=storage/tests/affairs.md --store=storage/tests/store data/documents/*
	python3 tests/baseline.py data/documents/*
	python3 tests/response.py data/documents/*
	python3 tests/language.py data/documents/*
	python3 tests/rows.py data/documents/*
	python3 tests/decisions.py data/documents/*
	python3 tests/entries.py --pages=storage/tests/pages
	python3 tests/views.py data/documents/*
	python3 tests/second.py data/documents/*
	python3 tests/ask.py --pages=storage/tests/pages data/documents/*
	python3 tests/shipped.py --pages=storage/tests/pages
	python3 tests/questions.py --pages=storage/tests/pages
	python3 tests/server.py --store=storage/tests/store --pages=storage/tests/pages
	python3 tests/client.py
	python3 tests/bundles.py
	python3 tests/settle.py
	python3 tests/rules.py
	python3 tests/store.py
	python3 tests/vocabulary.py
	python3 tests/register.py
	python3 tests/admin.py data/documents/neuchatel-grand-conseil/*.pdf
	python3 tests/mapping.py
	python3 tests/translations.py
endif

# The store's operations over Postgres as well, inside the running container (after `make run`). The test
# works in a schema of its own and removes it at the end; the store in use is not touched.
test-store:
	docker compose exec docket sh -c 'python3 tests/store.py --postgres="$$DATABASE_URL"'

# With the model: the whole chain over the shipped documents, the scan page read, the leftover elements of the
# first pages sorted, the fields asked and placed, every document keyed and the documents of one key merged
# into one affair, every record validated. Needs LLM_API_KEY in .env (copy .env.example). About 70 calls, one
# after the other, about three minutes. Results, the raw exchange and the control images land in storage/bench/;
# the committed run is in results/.
bench:
	@test -f .env || { echo "copy .env.example to .env and set LLM_API_KEY"; exit 1; }
	python3 -m docket affairs --model --out storage/bench/documents data/documents/*/*.pdf

# With the model: two digital first pages read as if they had no text layer, held against their text layer.
# About 35 calls, about a minute.
bench-read:
	@test -f .env || { echo "copy .env.example to .env and set LLM_API_KEY"; exit 1; }
	python3 tests/read.py --out=storage/bench/read.md data/documents/nidau-m185 data/documents/zuerich-219587

# Builds the browser app (Angular, in app/) into src/docket/app/, from where the Python server serves it:
# once per language (de, fr, it, en), each build in a folder of its own. Node is needed for this build only,
# never to run the server; the Docker build does the same in its first stage. The built bundle is not committed.
app:
	cd app && npm ci --no-audit --no-fund && npx ng build

# Writes the translation files the build of the app reads (app/src/locale/messages.{fr,it,en}.xlf) from the
# list of its texts in the four languages (app/src/locale/words.json), and lists the texts that have no
# wording yet. After a text of the app has changed, take the texts out again first (needs Node):
# cd app && npx ng extract-i18n --format xlf --output-path src/locale
translations:
	python3 tools/translations.py

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

# The roles of the vocabulary (author, co-signer, speaker and what every parliament calls them) are not among
# the panel's lists; they are read from OpenParlData's export of the contributors, fetched once by hand:
# python3 tools/vocabulary.py --roles contributors.ndjson.gz. Only the parliament's key and the names of the
# role are read from a row. The result is committed with the rest of the stem.

# Loads the persons of the parliaments from OpenParlData's exports into the store, so printed names can be told
# as persons: two files, fetched one after the other. A preparation step, run once by hand; the persons are the
# one list not shipped here, because they are people. Only id, name, parliament and party are taken; nothing of
# it is written into the repository. Inside the running container: docker compose exec docket python3
# tools/register.py. Run again with a newer export, it keeps what the register learnt.
register:
	python3 tools/register.py

# Writes the rows (what was found in a document, one row per value) for every document a store already holds,
# from its fields reports and blocks; no model call. For a store filled before the rows existed. Inside the
# running container: docker compose exec docket python3 tools/rows.py.
rows:
	python3 tools/rows.py

# Learns the second opinion from the store: where the value of a field usually stands in the documents of a
# parliament, and a small network that tells a block that holds a field by its look. No model call. Both are
# tried on documents held back, and only what agreed more often than not is kept; the runs after it hold the
# second opinion against the model. Inside the running container: docker compose exec docket python3
# tools/learn.py.
learn:
	python3 tools/learn.py

# Answers three questions across the parliaments from the store, without the model: how many members back an
# affair, what kinds of documents hang on the affairs, which details a parliament prints at all. With the
# exports of OpenParlData (--affairs= and --contributors=) the persons held there stand beside the first
# answer, with the list the documents were drawn with (--drawn=) parliament and affair are certain; see
# tools/questions.py. Inside the running container: docker compose exec docket python3 tools/questions.py.
questions:
	python3 tools/questions.py

# Writes docs/mapping.md from data/schema/mapping.json: what every term of the schema is called in
# OpenParlData, JATS, Akoma Ntoso, Parla-CLARIN, Popolo and Docling. With STANDARDS=<folder> every name is held
# against the schemas of the standards first; they are not part of this repository, see tools/mapping.py.
mapping:
	python3 tools/mapping.py $(if $(STANDARDS),--standards $(STANDARDS))
