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

## Further rules, counted by replay

The stored runs of both sets put through the code again with the answers of the model as stored, no call. The replay
gives the stored run back field by field (1 440 of 1 440 fields) where the code is unchanged.

| | reference set | other documents |
|---|---:|---:|
| as above | 30 of 60 | 19 of 60 |
| a value has to stand on the page as whole words; a session without a place that is the polity again, a name that is the parliament, or a day without a session; a co-signer is no party | 29 | 19 |
| the model's kind stands without a mark, also against the words of the page; a mark only where the model names none | 38 | 30 |
| the date of submission read from the submission itself only; a word for further co-signers is no person | 40 | 30 |
| co-signers and on behalf of read from the submission only; who submitted is no co-signer again; the number of an affair holds a digit and is more than one digit | 40 | 31 |

A mark on the kind where the words of the page say another kind held 14 documents of the reference set to find 2
wrong kinds: the model was right in 12 of the 14.

A value inside a longer word had counted as found on the page: 58 of 1 451 values placed as literal on the 120
documents ("Parlament" in "Parlamentarischer Vorstoss", "1" in "12", "Motion" in "Motionstext"). A word may go on
with an ending of its own ("des Kantonsrates").

What the rules for the session and the party leave out on the 60 other documents, which they were not made on: 9
places of a session that are the polity or the place again, 5 names of a session that are the parliament or the
addressee, 4 days and places without a session, 5 parties that are the submitter, the parliament or the polity, 8
values under on behalf of that are a body of the document. A rule tried first, which also left out a value that
holds the other one and more, took "CVP Glarus" for the polity Glarus and "Sitzung des Einwohnerrats" for the
parliament; it was narrowed to a value that is the other one or a part of it.

On the reference set after these rules: 266 fields not as in the reference against 273, 136 fields with a value the
reference does not hold against 148. On the other documents: of the 30 without a mark, 17 hold none of the four
fields OpenParlData knows in another value.

The date of submission by the kind of the document, before the last row. Reference set: in documents the model
names a submission the date is right in 31 of 33 where one is set; in documents of another kind in 10 of 19, and
in 6 of these the reference holds no date of submission at all. Other documents, against the date of OpenParlData:
26 of 32 in submissions, 7 of 18 in documents of another kind. Asked for the day an affair was submitted, the model
gives the day the document at hand carries. With the date read from the submission only: on the other documents 32
values set that differ from OpenParlData against 42, 131 as OpenParlData against 138; of the 30 documents without a
mark, 19 hold none of the four fields in another value against 17. On the reference set 124 fields with a value the
reference does not hold against 136, and 270 fields not as in the reference against 266: the dates that were right
in an answer or a report are no longer set.

What still holds a document after that, by documents (reference set / other documents): a printed header entry 14 /
20, the kind against the words 14 / 17, the title 8 / 18, a contributor 8 / 18, the date 7 / 11, the type 6 / 8, the
number 3 / 7. These are values that stand on the page in no literal form.

## What the documents that run through hold

On the reference set, against the draft reference, before the further rules: of the 30 documents without a mark, 3
hold no value that is not in the reference under its field; 11 hold one such field, 16 more than one. After them: 5
of 38. By documents: party 10, co-signers 6,
parliament 5, on behalf of 5, session 5, authors 5, days of events 5. No document of the 30 has every field as in the
reference and complete. The reference is a draft; whether a value that is not in it is wrong or only read
differently was not told apart.

In the same run the day an affair was submitted became its first event, as OpenParlData lists it: the days of
events right in 33 of 60 documents against 20, 939 of 1 260 fields right (74.5 %) against 922.

Co-signers and on behalf of by the kind of the document, before the last row, on the reference set: in documents
of another kind than a submission, co-signers are set in 4 and hold in none, on behalf of is set in 9 and holds in
2; the reference holds neither for any such document. In an answer the model names who signed the answer. Who
submitted stood among the co-signers once more in 3 documents. On the 60 other documents the two rules leave out
22 co-signers that stand under the submitters, 5 co-signers and 6 values under on behalf of in answers and reports.
Asked for the affairs a text refers to, the model lists the numbers of its points: 9 single digits in one document
of the reference set and 9 in two of the others; two numbers of affairs on the other documents hold no digit.

With these: on the reference set co-signers as in the reference in 51 of 60 documents against 45, on behalf of in
49 against 46; fields with a value the reference does not hold 101 against 116; of the 40 documents without a mark,
8 hold no such value against 6. On the other documents 31 without a mark against 30, 21 of them with none of the
four fields in another value against 19. No field as in the reference in fewer documents than before.

A rule that a submitter is not the polity itself left out two values on the reference set and none on the other
documents; it was not built.

## Values no single block holds

After the rules above a document was held mostly by a value that stands literally in no block and lies at the block
the model named. On the 120 documents these were 40 values in 31 documents (reference set 19 in 14, other documents
21 in 17). What keeps them from standing literally:

| | reference set | other documents |
|---|---:|---:|
| the value runs over several blocks in a row | 2 | 4 |
| every word stands on the pages, in another order | 6 | 4 |
| a word stands nowhere on the pages | 11 | 13 |

Ten of the 40 are days. Four stand on the page in a form the reading did not know (a zero before the day with the
month written out, a month cut short). For the other six the named block holds a year, or a month and a year, and
the day is made up.

Five rules followed, each tried alone on both sets by replay. Because both sets had been looked at for them, they
were then held against a third: 151 stored documents of three parliaments (the answers of the run of 10 October put
through the code again under today's field names; events and the summary are not replayed).

- A day is read with a zero before it, with the month cut short and with a year of two digits.
- A day has a place only where it stands; the block the model names for it is none.
- A value that runs over two or three blocks in a row of one page, from the start of the first, stands literally.
- Held against the named block, a word of five letters or more may differ in one character.
- An answer that sets several fields in one line is cut where a field asked follows a named block.

On the 151 documents 33 values in 30 documents change. 19 days lose their place: for 18 the named block holds a
month and a year only, one is an unreadable line. 11 values lose their mark: three titles set in several lines, one
day with a year of two digits, one title that is the text of its block but for a letter, and six values one
character off the page (a canton named in the nominative where the page has the genitive, a word without its
accent, a name with one letter less). One day gets a place it had not, in a form now read. One value without a
place, a line of several fields taken for one, is gone. Values at a named block only: 35 against 65.

A first form of the third rule took a value wherever it ran over blocks. On the 151 documents it made a co-signer
out of the first name in one row of a table and the last name in the next. The rule now asks that the value starts
where a block starts.

Documents without a mark:

| | before | after |
|---|---:|---:|
| reference set, of 60 | 40 | 41 |
| other documents, of 60 | 31 | 37 |
| the 151 documents (events and summary not replayed) | 108 | 130 |

On the reference set fields with a value the reference does not hold: 97 against 98; no field as in the reference
in fewer documents. On the other documents 23 of the 37 hold none of the four fields in another value than
OpenParlData, against 21 of 31; values as OpenParlData 131 of 240 as before, 30 set differently as before: one
made-up day is gone, and one day read from a year of two digits is not the date OpenParlData holds for the affair.

Since this run the count takes a person written in another spelling for the same person (ä as ae, a letter
without its accent, a form of address before the name): fields with a value the reference does not hold 98 against
101, all of them under the submitters.

Tried and not built: a share of its words that a value needs in the named block. At more than a third, 13 values on
the 151 documents lose their place: 7 are not on the page (three titles put into German among them), 4 are right. At
more than half, six fields of the reference set that were right are empty.

## A person found by the last name alone

A contributor found in the register of the parliament by the last name alone, or with one character off, carried a
mark. The count above runs without a register and does not see these marks. With the register filled for the test
from OpenParlData's export of persons, the parliament of each document as its run found it, documents without a
mark:

| | no register | mark on both | mark on one character off only |
|---|---:|---:|---:|
| reference set, of 60 | 41 | 35 | 38 |
| other documents, of 60 | 37 | 31 | 37 |
| the 151 documents | 130 | 117 | 129 |

Whether the person found is the right one, against the persons OpenParlData holds for the same affair, counted
where it holds a person of that last name (third set / other documents / reference set):

| found | the same person |
|---|---|
| by the full name | 188 of 188 / 35 of 35 / 76 of 76 |
| by the last name alone | 72 of 73 / 69 of 69 / 6 of 6 |
| one character off | none to compare / 3 of 3 / 3 of 3 |

The mark on the last name alone was taken off. The mark on one character off stays: six names are few, and one
character can make another first name.

A name written with ae for ä, or without its accents, is the same name in the register since this run. On the 1 120
names of the 151 documents no lookup changes. On the 567 names of the other 120 documents, looked up among the
persons of all parliaments at once, two more are found and two now fit a second person.
