# Result: two digital first pages read as if they had no text layer

Two runs of `tests/read.py` on 8 October 2026 with swiss-ai/Apertus-v1.5-8B at temperature 0 on the first pages of
`nidau-m185` and `zuerich-219587`: every text element is set back to unknown, read by the model (three elements
per strip, then every multi-line element alone) and held against the text the PDF carries for the same element.
Run 1 also read the page of `aargau-scan`, which has no text layer, beforehand (13 calls).

The figures below are counted by replaying the logged answers through the same code without the model: the
reader asks, the logged answer of the same call is handed back, and `tests/read.py` judges. They were counted on the
logs before the names of people were replaced.

A reading counts as **identical** when it equals the reference after ß is written ss, runs of white space are one
space and case is ignored; as **near** when the edit distance is at most 10 % of the length of the reference; as
**other** beyond that; as **empty** when nothing came back. Character errors are the sum of the edit distances over
the sum of the reference lengths. "Flagged" counts the readings the image check marks for a person (approve).

## The two runs

| | run 1 | run 2 |
|---|---:|---:|
| first call (UTC) | 10:47:50 | 11:06:12 |
| last call (UTC) | 10:49:41 | 11:08:03 |
| calls | 35 | 35 |
| of them strips | 18 | 18 |
| of them single elements | 17 | 17 |
| answered with status 200 | 35 | 35 |
| time at the model, sum over the calls | 39.5 s | 38.6 s |
| elements with a reference | 50 | 50 |
| identical | 35 | 34 |
| near | 12 | 13 |
| other | 3 | 3 |
| empty | 0 | 0 |
| characters of the references | 5024 | 5024 |
| edit distance, sum | 419 | 421 |
| character errors | 8.3 % | 8.4 % |
| flagged among the identical | 26 of 35 | 25 of 34 |
| flagged among the near | 12 of 12 | 13 of 13 |
| flagged among the other | 3 of 3 | 3 of 3 |
| prompts equal to those the code builds on 12 October | 35 of 35 | 35 of 35 |
| images of the same size as the code cuts on 12 October | 22 of 35 | 35 of 35 |

Per page:

| page | elements | calls | run 1: identical / near / other | run 2: identical / near / other |
|---|---:|---:|---|---|
| nidau-m185-s1 | 35 | 20 | 27 / 7 / 1 | 27 / 7 / 1 |
| zuerich-219587-s1 | 15 | 15 | 8 / 5 / 2 | 7 / 6 / 2 |

## Between the runs

The prompts of the two runs are the same in 35 of 35 calls. The answers differ in 4 calls (calls 15, 24, 28, 33).
Between the runs the label of a single element was moved up by 4 pixels in its image: 13 of the 17 single images have another size in run 2, the 18 strips have the same size. Of the calls with another answer, 3 are single elements (15, 28, 33) and 1 is a strip (24), whose prompt and image size are the same in both runs.

Elements whose reading differs:

| page | reference (first 60 characters) | run 1 | run 2 |
|---|---|---|---|
| nidau-m185-s1 | Vorstossart: Vorstoss-Nr.: Richtlinienmotion: Beantwortung i | near, distance 2 | near, distance 1 |
| zuerich-219587-s1 | Gestützt auf Artikel 160 Abs. 1 der Bundesverfassung reicht  | identical, distance 0 | near, distance 3 |
| zuerich-219587-s1 | Begründung: | other, distance 296 | other, distance 298 |
| zuerich-219587-s1 | Deshalb sollten die Arbeitgebenden mit wenig Aufwand beantra | near, distance 6 | near, distance 4 |

## Not identical, run 1

"!" marks a reading the image check flags. Reference and reading are cut after 60 characters.

| page | state | distance / length | reference | reading |
|---|---|---:|---|---|
| nidau-m185-s1 | near ! | 2 / 25 | Motion M 185 ☒ 21.03.2019 | Motion M 185 21.03.2019 |
| nidau-m185-s1 | near ! | 2 / 71 | Vorstossart: Vorstoss-Nr.: Richtlinienmotion: Beantwortung i | Vorstoßart: Vorstoß-Nr.: Rechtlinienmotion: Beantwurtung im  |
| nidau-m185-s1 | near ! | 3 / 66 | Beschluss. Gemeinderat: Aktenzeichen: Ressort: Antrag Gemein | Beschluss. Gemeindeirat: Aktienzeichen: Ressort: Antrag Geme |
| nidau-m185-s1 | near ! | 1 / 48 | 18.02.2019 nid 0.1.6.2 / 2 Präsidiales Ablehnung | 18.02.2019 mid 0.1.6.2 / 2 Präsidiales Ablehnung |
| nidau-m185-s1 | near ! | 1 / 10 | Begründung | Begrü̈ndung |
| nidau-m185-s1 | near ! | 1 / 87 | in Europa. Statt nationaler Alleingänge an den Grenzen und i | in Europa. Staat nationaler Alleingänge an den Grenzen und i |
| nidau-m185-s1 | other ! | 85 / 86 | europäischen Hafen zu ermöglichen. Danach sollen sie in vers | europäischen Hafen zu ermöglichen. Danach sollen sie in vers |
| nidau-m185-s1 | near ! | 1 / 90 | sicheren Fluchtrouten und offenen Häfen in Europa angestrebt | sicheren Flüchtrouten und offenen Häfen in Europa angestrebt |
| zuerich-219587-s1 | other ! | 1 / 8 | 357/2018 | 3572018 |
| zuerich-219587-s1 | other ! | 296 / 11 | Begründung: | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg |
| zuerich-219587-s1 | near ! | 3 / 306 | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg |
| zuerich-219587-s1 | near ! | 14 / 471 | Wenn ein Asylantrag durch einen rechtskräftigen Entscheid ab | Wenn ein Asylantrag durch einen rechtskräftigen Entscheid ab |
| zuerich-219587-s1 | near ! | 6 / 407 | Deshalb sollten die Arbeitgebenden mit wenig Aufwand beantra | Deshalb sollten die Arbeitgebenden mit wenig Aufwand beauftr |
| zuerich-219587-s1 | near ! | 2 / 509 | Gemäss Artikel 43 Abs. 3 des Asylgesetzes können die Kantone | Gemäss Artikel 43 Abs. 3 des Asylgesetzes können die Kantone |
| zuerich-219587-s1 | near ! | 1 / 165 | Sinnvollerweise sollen die Abläufe vereinfacht und die Kompe | Sinnvollerweise sollen die Abläufe vereinfacht und die Kompe |

## Not identical, run 2

"!" marks a reading the image check flags. Reference and reading are cut after 60 characters.

| page | state | distance / length | reference | reading |
|---|---|---:|---|---|
| nidau-m185-s1 | near ! | 2 / 25 | Motion M 185 ☒ 21.03.2019 | Motion M 185 21.03.2019 |
| nidau-m185-s1 | near ! | 1 / 71 | Vorstossart: Vorstoss-Nr.: Richtlinienmotion: Beantwortung i | Vorstoßart: Vorstoß-Nr.: Richtlinienmotion: Beantwurtung im  |
| nidau-m185-s1 | near ! | 3 / 66 | Beschluss. Gemeinderat: Aktenzeichen: Ressort: Antrag Gemein | Beschluss. Gemeindeirat: Aktienzeichen: Ressort: Antrag Geme |
| nidau-m185-s1 | near ! | 1 / 48 | 18.02.2019 nid 0.1.6.2 / 2 Präsidiales Ablehnung | 18.02.2019 mid 0.1.6.2 / 2 Präsidiales Ablehnung |
| nidau-m185-s1 | near ! | 1 / 10 | Begründung | Begrü̈ndung |
| nidau-m185-s1 | near ! | 1 / 87 | in Europa. Statt nationaler Alleingänge an den Grenzen und i | in Europa. Staat nationaler Alleingänge an den Grenzen und i |
| nidau-m185-s1 | other ! | 85 / 86 | europäischen Hafen zu ermöglichen. Danach sollen sie in vers | europäischen Hafen zu ermöglichen. Danach sollen sie in vers |
| nidau-m185-s1 | near ! | 1 / 90 | sicheren Fluchtrouten und offenen Häfen in Europa angestrebt | sicheren Flüchtrouten und offenen Häfen in Europa angestrebt |
| zuerich-219587-s1 | near ! | 3 / 427 | Gestützt auf Artikel 160 Abs. 1 der Bundesverfassung reicht  | Gesetz auf Artikel 160 Abs. 1 der Bundesverfassung reicht de |
| zuerich-219587-s1 | other ! | 1 / 8 | 357/2018 | 3572018 |
| zuerich-219587-s1 | other ! | 298 / 11 | Begründung: | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg |
| zuerich-219587-s1 | near ! | 3 / 306 | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg |
| zuerich-219587-s1 | near ! | 14 / 471 | Wenn ein Asylantrag durch einen rechtskräftigen Entscheid ab | Wenn ein Asylantrag durch einen rechtskräftigen Entscheid ab |
| zuerich-219587-s1 | near ! | 4 / 407 | Deshalb sollten die Arbeitgebenden mit wenig Aufwand beantra | Deshalb sollten die Arbeitgebenden mit wenig Aufwand beantra |
| zuerich-219587-s1 | near ! | 2 / 509 | Gemäss Artikel 43 Abs. 3 des Asylgesetzes können die Kantone | Gemäss Artikel 43 Abs. 3 des Asylgesetzes können die Kantone |
| zuerich-219587-s1 | near ! | 1 / 165 | Sinnvollerweise sollen die Abläufe vereinfacht und die Kompe | Sinnvollerweise sollen die Abläufe vereinfacht und die Kompe |

## The page without a text layer, run 1

`aargau-scan`, page 1: 13 calls (6 strips, 7 single elements), first call 10:46:56 UTC, 22.3 s at the model. The page has 17 elements; 16 were read and carry text, 11 of them are flagged by the image check. There is no reference for this page in the run: the document is the image-only copy.
