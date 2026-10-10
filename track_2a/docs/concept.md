# Concept

Docket turns the PDF of a parliamentary affair into one common structure, with the place every value was taken
from. This document says what the problem is, what the idea is, and what the project holds itself to. The
numbers behind every decision are in [evidence.md](evidence.md).

## The problem

Switzerland has parliaments on three levels and in several languages. Their common object is the affair: a
motion, an interpellation, a request, submitted by members, answered by the executive, mostly closed by a
decision. OpenParlData reads about 90 parliaments every day and publishes some 300 000 affairs as open data,
each with its source documents. What is in the PDFs, the question asked, the answer with its reasoning, the
decision, the people involved, cannot be structured reliably today. The existing extraction works with one
prompt and one schema per parliament.

The client names three gaps: a format that carries both the document's structure and the affair's semantics
(Docling knows the structure, Akoma Ntoso is heavy, Parla-CLARIN is for debates); an extraction that does not
invent values at the scale of 300 000 documents; and a verification, since there is no gold standard and no
metric that says whether a pipeline is good enough to run unattended.

Counted on the corpus: 855 767 files, 325 599 affairs. In a sample of 48 PDFs from 48 bodies, 15 are scans, 7 of
them without a text layer; only 14 are a motion or its answer. The affair types are harmonised (464 labels onto
18 types), the procedural state is not: it is empty for 325 321 of 325 599 affairs.

## The idea

- **One input path.** Every page goes as an image through the same geometry, born digital or scanned. The
  geometry splits the page into elements with type and position without any model; words of the text layer
  are laid into the elements where there is one, the model reads where there is none.
- **First recognise, then read, then fill.** The model never locates anything and never decides what a page
  is. It reads elements it is shown, and it answers questions about a page it is shown as a text image, six
  fields per call. What code knows for sure, the page, the page count, the place of a value, is never asked.
- **The affair as OpenParlData has it, the document beneath it as JATS names it.** The API's record stays
  unchanged; what OpenParlData does not carry gets a key named after the element in JATS 1.3. No XML, no
  XSD: a JSON Schema, extended only when a document demands it.
- **Every value with its place.** A value from the document points at the block it stands in, literally or
  derived (every word of it in the block); what the model only cites or composes is marked for a person. A
  value with no place does not come from the document and is dropped.
- **The person's decision stays with the value.** Confirmed, changed or rejected, at the place, with the
  value before; the same change made twice proposes a rule that a person accepts or declines, and every
  decision is teaching material.
- **Prior knowledge is a table, not the model.** The harmonised type, the number forms per parliament, the
  section names and the values seen come from the export and from the documents, checked, and are shipped
  with the pipeline.

## Why Apertus

The track asks for it, and the client's own setting fits it: an own server with about 20 GB of memory for a
self-hosted model, Python and PostgreSQL behind an Angular front end. A small model that runs there has to be
used for what it can do. Measured: it reads running text nearly right and short entries less well; it cannot
map the affair type from the label (44.8 %) nor from the page (47 to 54 %); the more structure in the prompt
the worse it gets; it names source blocks that hold no word of the value in 142 of 204 cases. So the pipeline
gives it one thing at a time, shows it the page as it is, and checks every answer against the page by code.

## Principles

From the client's briefing:

- Conservative extraction: nothing added, nothing left out, nothing changed in meaning. The PDF decides.
- Provenance: every value keeps a reference to the page and, where possible, the text span.
- Extracted and inferred are told apart. Where it cannot be done reliably: say so, do not guess.
- Lean on existing standards rather than invent a model.

From the work:

- Nothing is invented: only what is unambiguous is set.
- The reference comes from the material, never from labels set by hand.
- Partial rates are not an answer; what was missed is listed and looked at.
- Calls to the services run one after the other, with pauses.
- The thresholds are measured, not chosen, and every attempt that failed is on record.

## The question the project measures

The project lead's question, verbatim:

> Erreicht die aus einem heterogenen Dokumentkorpus induzierte Ontologie einen stabilen Zustand, bevor ihre
> semantische Komplexität die zuverlässige Zuordnung durch das verwendete Modell übersteigt?

Does the ontology induced from a heterogeneous corpus of documents reach a stable state before its semantic
complexity exceeds what the model can map reliably? The client's own questions sit beside it: is a common
schema for parliamentary affairs feasible, which parts can be represented uniformly across parliaments, and
where do fundamental differences remain. A convincing partial or negative answer counts.

What has been measured so far points one way: the vocabulary of labels is small and runs dry fast (after 5 000
affairs 98.8 % of the rest carry a seen label), while the vocabulary of states does not travel across bodies;
the small model maps neither reliably, a corrected table does. The schema therefore stores what is printed and
harmonises through tables per parliament.

## Flow

1. The PDF comes in; nothing else. Pages are rendered at 300 dpi.
2. Geometry: lines, areas, marks, cells, text lines, objects, typed elements, without a model.
3. Text: from the text layer into the elements; pages without one are read by the model, element by element
   in strips, and every reading is checked against the image.
4. Blocks: elements become paragraphs, sections, lists, labelled values, tables and images by code; the rest
   is sorted by the model.
5. Fields: the model answers the fields file over the text image of the first pages, six at a time, with the
   contract excerpt; every value is placed by code.
6. The affair: the document's number, normalised and checked against the parliament's number forms, keys the
   affair; several documents fold into one affair; the harmonised type comes from the table.
7. Review: a person sees the values marked for a look, decides at the place, and the decision stays in the
   data.

## What the client measures

Insight first: how well the submission answers whether a common schema is feasible. Breadth second: how the
approach holds across parliaments, document kinds and languages. The evidence document is written for both.
