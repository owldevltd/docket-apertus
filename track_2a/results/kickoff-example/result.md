# Result: the kickoff example, two runs

`nidau-m185`, the example of the challenge (a motion of two pages), run twice on 10 October 2026 (UTC; the night of
11 October local time) with swiss-ai/Apertus-v1.5-8B at temperature 0, six calls each: one to sort the leftover
elements of the first page, five for the fields. Run 1 is the code of that day. For run 2 a change was laid into the
working tree: a column of labels and the column of values beside it are paired line by line into one list. Everything
below is counted from the logged calls and from the field reports and records the two runs wrote; it was counted
before the names of people were replaced, and the names in the tables are the made-up ones of the logs.

## Calls and blocks

| | run 1 | run 2 |
|---|---:|---:|
| first call (UTC) | 2026-10-10 22:04:10 | 2026-10-10 22:10:37 |
| calls | 6 | 6 |
| answered with status 200 | 6 | 6 |
| first call to last answer | 15 s | 15 s |
| time at the model, sum | 5.0 s | 5.4 s |
| blocks | 23 | 20 |
| of them `p` | 14 | 8 |
| of them `sec` | 5 | 5 |
| of them `def-list` | 2 | 5 |
| of them `graphic` | 2 | 2 |
| lists of label and value with more than one pair | 0 | 3 |
| key of the affair | `nr-0162` | `nr-2` |

The lists of run 2, by their labels: `b6`: Vorstossart, Vorstoss-Nr., Richtlinienmotion, Beantwortung im Stadtrat; `b7`: Eingereicht am, Eingereicht von; `b9`: Beschluss. Gemeinderat, Aktenzeichen, Ressort, Antrag Gemeinderat.

## The fields

| field | what the page prints | run 1 | run 2 | work log on run 1 |
|---|---|---|---|---|
| version | – | – (empty) | – (empty) | – |
| number | Vorstoss-Nr.: M 185 | nid 0.1.6.2 (on the page) | / 2 (on the page) | wrong |
| title | the heading: Aufnahme von Bootsflüchtlingen | Aufnahme von Bootsflüchtlingen (on the page) | Aufnahme von Bootsflüchtlingen (on the page) | right |
| type | Vorstossart: Motion; Richtlinienmotion: ☒ | Motion (on the page) | Motion (on the page) | wrong |
| date | Eingereicht am: 22.11.2018 | 22.11.2018 (on the page) | 22.11.2018 (on the page) | right |
| authors | Eingereicht von: two lines, each a name and a party | Lüthold Katrin, SP Kern; Edith, Grüne (on the page) | Edith, Grüne; Katrin, SP Kern (on the page) | wrong |
| party | in the lines of "Eingereicht von": SP, Grüne | SP Kern; Grüne (on the page) | Grüne; SP Kern (on the page) | wrong |
| on-behalf-of | – | Katrin, SP Kern (on the page) | SP Kern, Grüne (not on the page) | wrong |
| addressee | – | Gemeinderat (on the page) | Gemeinderat (on the page) | right |
| place | – | Nidau (on the page) | Lüthold (on the page) | – |
| parliament | – | Stadtrat (on the page) | Parlamentarischer Vorstoss (on the page) | right |
| polity | – | Nidau (on the page) | Nidau (on the page) | – |
| department | Ressort: Präsidiales | Präsidiales (on the page) | Präsidiales (on the page) | right |
| session | – | – (empty) | – (empty) | – |
| session-date | – | – (empty) | – (empty) | – |
| session-place | – | – (empty) | – (empty) | – |
| cosigners | Mitunterzeichnende: ten names | Brunner Beatrice, Dörig Manuel, Eicher Thomas, Kägi Noah, Kägi Nora, Kunz Véronique, Meier-Nussbaum Ursina, Rochat Sophie, Roth Marcel, Suter-Sommer C (on the page) | Brunner Beatrice, Dörig Manuel, Eicher Thomas, Kägi Noah, Kägi Nora, Kunz Véronique, Meier-Nussbaum Ursina, Rochat Sophie, Roth Marcel, Suter-Sommer C (on the page) | right |
| related | – | – (empty) | – (empty) | – |
| reference | – | – (empty) | – (empty) | – |
| keywords | – | Aufnahme von Bootsflüchtlingen (on the page) | – (empty) | wrong |
| event | Beantwortung im Stadtrat; Beschluss. Gemeinderat | Beantwortung im Stadtrat; Beschluss des Gemeinderates (on the page) | Beschluss. 18.02.2019; Ablehnung (on the page) | – |
| event-date | 21.03.2019; 18.02.2019 | 22.11.2018; 18.02.2019 (on the page) | 18.02.2019; - (on the page) | wrong |
| summary | – | Der Stadtrat von Nidau hat eine Richtlinienmotion zur Aufnahme von Bootsflüchtlingen aus dem Mittelmeer eingereicht, die vom Gemeinderat am 18.02.2019 (on the page) | Die Motion fordert den Gemeinderat auf, sich beim Bund für eine humanitäre Aufnahme von Bootsflüchtlingen aus dem Mittelmeer einzusetzen und die Krimi (not on the page) | – |

"What the page prints" is the label and value as they stand on the first page, where the page has a label for the field. The last column is what the work log of the night notes for run 1; fields it does not mention carry a dash. The summaries are cut after 150 characters.

## Against the values OpenParlData holds

| field | OpenParlData | run 1 | same | run 2 | same |
|---|---|---|---|---|---|
| number | M 185 | nid 0.1.6.2 | no | / 2 | no |
| title | Aufnahme von Bootsflüchtlingen | Aufnahme von Bootsflüchtlingen | yes | Aufnahme von Bootsflüchtlingen | yes |
| type | Richtlinienmotion | Motion | no | Motion | no |
| date | 22.11.2018 | 22.11.2018 | yes | 22.11.2018 | yes |

Same value: 2 of 4 in run 1, 2 of 4 in run 2. The four values are those of affair 330555 in `data/documents/nidau-m185/document.json`; they were fetched once for the tests, the pipeline fetches nothing.

## Not in the files

- How often a first page holds one element with at least two labels (3 of 204 documents of the stored runs, beside this one) was counted that night and stands in the work log only.
