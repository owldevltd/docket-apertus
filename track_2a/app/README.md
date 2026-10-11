# The browser app

The app of Docket, in two levels: what a visitor reads (the affairs, the documents set from the blocks of
their record, persons, groups, meetings, events) and, under `/admin`, the administration behind its account
(the review of one affair with its pages and every value with a place, the decisions, the runs, the rules and
the vocabulary). Angular with Angular Material, in the look of OpenParlData's own
apps; the font is served by the app itself, nothing is loaded from elsewhere.

Node is needed to build the app, never to run it. `make app` in the project folder (or `npm ci && npx ng
build` here) writes the bundle to `src/docket/app/`, from where the Python server serves it; the Docker build
does the same in its first stage. The bundle is not committed.

The app is written in German and built once per language (de, fr, it, en) by Angular's own localisation,
each build in a folder of its own; the switch at the top right changes the folder. A text is marked in the
template (`i18n`) or in the code (`$localize`). After a text has changed: `npx ng extract-i18n --format xlf
--output-path src/locale` here takes the texts out again, the new wording goes into
`src/locale/words.json` (one row per text, the four languages side by side), and `make translations` in the
project folder writes the three files the build reads and lists what has no wording yet.

For development, `npm start` serves the app on port 4200 and passes `/api` to a running Python server on
port 8080 (`python3 -m docket serve`).

- `src/app/public/` — what a visitor reads: the start with its six tabs, an affair, a document, a person, a
  group, a meeting
- `src/app/api/` — the one door to the server and the types of what it answers with
- `src/app/affairs/` — the list, one affair, the page with its blocks, a value with its decisions
- `src/app/decisions/` — every decision taken
- `src/app/admin/` — runs, rules, the vocabulary, processing a document
- `src/app/shared/` — the words of the app, the account of the administration, the icons
- `src/locale/` — the texts of the app and their wordings in the four languages
