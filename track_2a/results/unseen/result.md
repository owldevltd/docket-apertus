# Result: do the changes hold on documents they were not made on?

Measured on 13 October 2026. Every change of 12 and 13 October to the way the fields are asked and read was made and measured on the same 60 documents of the reference set (`results/asking/`). Here 60 other documents go through the pipeline twice: as it was before those changes (the commit of 12 October before them, with the pace of the client as built) and as it is after them. Nothing was changed on these documents and no rule was fitted to them.

The 60 documents: 20 each in German, French and Italian, from 40 parliaments; 26 of them from 23 parliaments of which the reference set holds no document. They were chosen by a rule fixed before any result: per language one document a parliament in turn, the parliaments the reference set does not hold first, parliaments and documents in the order of their names.

The reference is not a reading of the documents but what OpenParlData holds for the affair: number, title, type and date, fetched for the test. A number and a date count when they are the same; a title and a type also in another spelling or when one contains the other. The pipeline itself gets the PDF alone.

## All 60 documents

| field | as OpenParlData, before | after | another value, before | after | empty, before | after |
|---|---:|---:|---:|---:|---:|---:|
| number | 19 | 21 | 6 | 9 | 35 | 30 |
| title | 27 | 41 | 15 | 10 | 18 | 9 |
| type | 35 | 43 | 4 | 6 | 21 | 11 |
| date | 26 | 33 | 16 | 17 | 18 | 10 |
| all four, of 240 | 107 | 138 | | | | |

Documents with all four as OpenParlData: 7 before, 7 after, of 60.

Per document, more of the four fields as OpenParlData after than before in 23 documents, fewer in 2, as many in 35.

## The 26 documents of parliaments the reference set does not hold

| field | as OpenParlData, before | after | another value, before | after | empty, before | after |
|---|---:|---:|---:|---:|---:|---:|
| number | 8 | 10 | 2 | 4 | 16 | 12 |
| title | 18 | 22 | 3 | 2 | 5 | 2 |
| type | 20 | 22 | 1 | 1 | 5 | 3 |
| date | 14 | 14 | 8 | 9 | 4 | 3 |
| all four, of 104 | 60 | 68 | | | | |

Documents with all four as OpenParlData: 5 before, 5 after, of 26.

## The other 34 documents

| field | as OpenParlData, before | after | another value, before | after | empty, before | after |
|---|---:|---:|---:|---:|---:|---:|
| number | 11 | 11 | 4 | 5 | 19 | 18 |
| title | 9 | 19 | 12 | 8 | 13 | 7 |
| type | 15 | 21 | 3 | 5 | 16 | 8 |
| date | 12 | 19 | 8 | 8 | 14 | 7 |
| all four, of 136 | 47 | 70 | | | | |

Documents with all four as OpenParlData: 2 before, 2 after, of 34.

## What the document prints

Counted after the runs, no call: the number OpenParlData holds stands in the text of the document in 21 of the 60 documents; there the pipeline has the same number in 17, another in 1, none in 3. In the other 39 it holds none in 27, another number in 8, and the same number in another form in 4. The date OpenParlData holds stands in the document in 36 of the 60; there the pipeline has the same date in 30, another in 3, none in 3. Where it does not stand there, the pipeline holds another date in 14 documents, the same in 3, none in 7.

## Two rules that did not hold

Before the second run, the rules that need no model were tried on the stored blocks of 151 further documents of three parliaments, no call:

- The date taken from the line of a place and a day where the model gives none: on the 60 documents of the reference set it had brought the date to 43 of 60 from 39. On the 151 documents 26 have such a line, and its day is the date OpenParlData holds in 2 of them: it is the day an answer was adopted or a text was written, not the day the affair was submitted. The rule was taken out again.
- The place from that line: 5 of the 26 lines found were none (an abbreviation of a law, a broadcaster in brackets, a file reference before the place, the end of the sentence before); on the first documents of the run before, a day of the week ("Sitzung vom Montag, 3. März 2020"). The rule now asks for the form of a name (small letters, no digits), for a line that stands by itself, and leaves the days of the week aside. After that: 59 lines on the 60, the 151 and the first 27 of these documents, each a place.

The second run has both corrections. On the 60 documents of the reference set they give, counted on the stored run: the place right in 57 instead of 56, the date in 41 instead of 45, 919 of 1 260 fields right instead of 922.

## What the rules of code do on these documents

No reference for these; counted on the second run: a line of a place and a day in 27 of the 60 documents; the kind of the document without a mark in 32 (the model and the words say the same), with a mark in 27, none in 1; a party or on-behalf-of left out because it stands under the submitters or as a body in 9; 42 events, each with its own day.

Calls: 1 642 in the first run, 1 755 in the second, one of them without an answer; the documents hold more pages without a text layer than the reference set.
