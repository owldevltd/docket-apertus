# The browser app

The review app of Docket: the affairs, one affair with its pages and every value with a place, the decisions,
and the admin with the runs, the rules and the vocabulary. Angular with Angular Material, in the look of OpenParlData's own
apps; the font is served by the app itself, nothing is loaded from elsewhere.

Node is needed to build the app, never to run it. `make app` in the project folder (or `npm ci && npx ng
build` here) writes the bundle to `src/docket/app/`, from where the Python server serves it; the Docker build
does the same in its first stage. The bundle is not committed.

For development, `npm start` serves the app on port 4200 and passes `/api` to a running Python server on
port 8080 (`python3 -m docket serve`).

- `src/app/api/` — the one door to the server and the types of what it answers with
- `src/app/affairs/` — the list, one affair, the page with its blocks, a value with its decisions
- `src/app/decisions/` — every decision taken
- `src/app/admin/` — runs, rules, the vocabulary, processing a document
- `src/app/shared/` — the words of the app, the reviewer's name, the icons
