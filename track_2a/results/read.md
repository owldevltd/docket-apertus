# Reading against the text layer

Produced by `tests/read.py`: 50 elements, 35 calls, 1.9 minutes. Reading in strips of three, then multi-line blocks alone.

| identical | near | other | empty | character errors |
|---:|---:|---:|---:|---:|
| 34 | 13 | 3 | 0 | 8.4 % |

Flagged by the image check (approve): identical 25 of 34, near 13 of 13, other 3 of 3, empty 0 of 0.

## Not identical

| page | state | reference | reading |
|---|---|---|---|
| nidau-m185-s1 | near ! | Motion M 185 ☒ 21.03.2019 | Motion M 185 21.03.2019 |
| nidau-m185-s1 | near ! | Vorstossart: Vorstoss-Nr.: Richtlinienmotion: Beantwortung i | Vorstoßart: Vorstoß-Nr.: Richtlinienmotion: Beantwurtung im  |
| nidau-m185-s1 | near ! | Beschluss. Gemeinderat: Aktenzeichen: Ressort: Antrag Gemein | Beschluss. Gemeindeirat: Aktienzeichen: Ressort: Antrag Geme |
| nidau-m185-s1 | near ! | 18.02.2019 nid 0.1.6.2 / 2 Präsidiales Ablehnung | 18.02.2019 mid 0.1.6.2 / 2 Präsidiales Ablehnung |
| nidau-m185-s1 | near ! | Begründung | Begrü̈ndung |
| nidau-m185-s1 | near ! | in Europa. Statt nationaler Alleingänge an den Grenzen und i | in Europa. Staat nationaler Alleingänge an den Grenzen und i |
| nidau-m185-s1 | other ! | europäischen Hafen zu ermöglichen. Danach sollen sie in vers | europäischen Hafen zu ermöglichen. Danach sollen sie in vers |
| nidau-m185-s1 | near ! | sicheren Fluchtrouten und offenen Häfen in Europa angestrebt | sicheren Flüchtrouten und offenen Häfen in Europa angestrebt |
| zuerich-219587-s1 | near ! | Gestützt auf Artikel 160 Abs. 1 der Bundesverfassung reicht  | Gesetz auf Artikel 160 Abs. 1 der Bundesverfassung reicht de |
| zuerich-219587-s1 | other ! | 357/2018 | 3572018 |
| zuerich-219587-s1 | other ! | Begründung: | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg |
| zuerich-219587-s1 | near ! | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg | Aus wirtschaftlicher und gesellschaftlicher Sicht ist zu beg |
| zuerich-219587-s1 | near ! | Wenn ein Asylantrag durch einen rechtskräftigen Entscheid ab | Wenn ein Asylantrag durch einen rechtskräftigen Entscheid ab |
| zuerich-219587-s1 | near ! | Deshalb sollten die Arbeitgebenden mit wenig Aufwand beantra | Deshalb sollten die Arbeitgebenden mit wenig Aufwand beantra |
| zuerich-219587-s1 | near ! | Gemäss Artikel 43 Abs. 3 des Asylgesetzes können die Kantone | Gemäss Artikel 43 Abs. 3 des Asylgesetzes können die Kantone |
| zuerich-219587-s1 | near ! | Sinnvollerweise sollen die Abläufe vereinfacht und die Kompe | Sinnvollerweise sollen die Abläufe vereinfacht und die Kompe |
