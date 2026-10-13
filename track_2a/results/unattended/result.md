# Result: documents that run through without a person

Measured on 13 October 2026. A value of a record carries `approve` where a person should look. A document runs
through without a person when none of its values carries one. Counted per document on the 60 documents of the
reference set and on the 60 documents of `results/unseen/`, which no rule was made on.

## What held every document

Before: no document of the 60 without a mark, 2.6 marks a document. By the number of documents a mark hangs on:

| mark on | documents |
|---|---:|
| the summary | 60 |
| an event | 28 |
| the kind of the document | 25 |
| a printed header entry (`custom-meta`) | 14 |
| a contributor | 8 |
| the title | 8 |
| the date of submission | 7 |
| the type | 6 |
| the number | 3 |

The summary was marked in every document: the model words it, so it stands on no page.

## A worded text held against its document

Tried on the stored summaries of both sets, 120 documents, no call. What tells a summary of its document from one
that is not: the share of its words (from four letters) that stand in the document.

| | reference set | other documents |
|---|---:|---:|
| the summary of the document: smallest share | 0.43 | 0.39 |
| in the middle | 0.72 | 0.70 |
| the summary of another document of the same language, put in its place: in the middle | 0.18 | 0.18 |
| at nine in ten | 0.32 | 0.30 |

The summary is in the language of its document in 120 of 120. Of 122 numbers in the summaries 120 stand in the
document.

The check as built: a worded text is marked when less than 0.4 of its words stand in the document (set by the
assistant, open), when it is in another language than the document, or when it holds a number of two or more digits
the document does not. With it: no summary of the reference set marked, 1 of the other 60; a summary of another
document put in its place is marked in 57 of 60 and 57 of 59.

## Documents without a mark

| | reference set | other documents |
|---|---:|---:|
| before | 0 of 60 | 0 of 60 |
| the summary held against its document; run through the pipeline, 697 calls | 13 | |
| the same, counted on the stored run | 13 | 12 |
| also: the kind marked only where the words of the page say another kind; the name of an event held against the document like the summary; counted on the stored runs | 30 | 19 |

The kind of the document: the model right in 56 of the 60 documents of the reference set; with the words of the
first page saying the same in 34 of 35, with the words silent in 10 of 11, against the words in 12 of 14.

What still holds a document after that, by documents (reference set / other documents): a printed header entry 14 /
20, the kind against the words 14 / 17, the title 8 / 18, a contributor 8 / 18, the date 7 / 11, the type 6 / 8, the
number 3 / 7. These are values that stand on the page in no literal form.

## What the documents that run through hold

On the reference set, against the draft reference: of the 30 documents without a mark, 3 hold no value that is not in
the reference under its field; 11 hold one such field, 16 more than one. By documents: party 10, co-signers 6,
parliament 5, on behalf of 5, session 5, authors 5, days of events 5. No document of the 30 has every field as in the
reference and complete. The reference is a draft; whether a value that is not in it is wrong or only read
differently was not told apart.

In the same run the day an affair was submitted became its first event, as OpenParlData lists it: the days of
events right in 33 of 60 documents against 20, 939 of 1 260 fields right (74.5 %) against 922.
