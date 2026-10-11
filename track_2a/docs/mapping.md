# The affair schema and the standards

How the terms of the affair schema (`data/schema/docket.json`, described in `data/schema/DEFINITION.md`) are called in OpenParlData and in the standards the challenge names: per term the elements or properties that hold the same thing there, by their names in the standard's own schema; an empty list where none was found. Which element answers a term is a reading of the schemas, set by the assistant on 11 October 2026, open. That every name exists in its schema is checked by `tools/mapping.py`; this page is written from `data/schema/mapping.json`.

Checked on 2026-10-11: 339 names, all found in the schemas named below.

| Standard | Edition | How a name is written | Terms with a name there |
| --- | --- | --- | ---: |
| OpenParlData | the tables of its exports, as read on 10 October 2026 | table.field; a field per language is named in German (`title_de`) | 26 of 54 |
| JATS | 1.3, Archiving, the XSD with MathML3 | element, `@attribute`, `element/@attribute` | 42 of 54 |
| Akoma Ntoso | 3.0, akomantoso30.xsd of OASIS | element, `@attribute`, `element/@attribute` | 46 of 54 |
| Parla-CLARIN | the TEI customisation, parla-clarin.xsd | element, `@attribute`, `element/@attribute` | 44 of 54 |
| Popolo | the JSON schemas of the specification | class.property | 20 of 54 |
| Docling | DoclingDocument 1.10.0 of docling-core, its JSON Schema fetched on 11 October 2026 | Class, Class.property, `Class.property=value`, or a property of the document itself | 19 of 54 |

A dash means that nothing was found for the term in that schema.

## The affair

| Here | What it is | OpenParlData | JATS | Akoma Ntoso | Parla-CLARIN | Popolo | Docling |
| --- | --- | --- | --- | --- | --- | --- | --- |
| the record | one item of parliamentary business with its documents | `affairs` | – | `documentCollection` | – | `motion` | – |
| `schema` | the version of this definition | – | `article/@dtd-version` | – | – | – | `schema_name`, `version` |
| `number` | the affair's number | `affairs.number` | `article-id` | `docNumber`, `FRBRnumber` | `idno` | `motion.identifier` | – |
| `title` | the title, per language | `affairs.title_de` | `article-title`, `trans-title` | `docTitle` | `title` | – | `TitleItem` |
| `type_name` | the type as the document names it, and its standard name | `affairs.type_name_de`, `affairs.type_harmonized_de` | `subj-group`, `subject` | `docType`, `TLCConcept` | `catRef`, `category` | `motion.classification` | – |
| `begin_date` | the day the affair was handed in | `affairs.begin_date` | `history`, `date` | `docDate`, `FRBRdate` | `date` | `motion.date` | – |
| `contributors.data[]` | who takes part: a person or a group, by name | `contributors.fullname`, `contributors.type` | `contrib-group`, `contrib`, `string-name` | `docProponent`, `TLCPerson` | `person`, `persName` | `motion.creator_id`, `person` | – |
| `role` | what the contributor is to the affair: author, co-signer | `contributors.role_de`, `contributors.role_harmonized` | `role`, `contrib/@contrib-type` | `TLCRole`, `role` | `affiliation/@role` | `membership.role` | – |
| `party` | the party or parliamentary group of a contributor | `contributors.party_de`, `contributors.party_harmonized_de` | `aff` | `TLCOrganization`, `organization` | `affiliation`, `org` | `organization`, `membership.organization_id` | – |
| `person_id` | the id of the person a printed name was told as | `contributors.person_id`, `persons.id` | `contrib-id` | `TLCPerson/@href` | `person/@id` | `person.id`, `person.identifiers` | – |
| `on-behalf-of` | in whose name it was handed in | – | `on-behalf-of` | – | – | `membership.on_behalf_of_id` | – |
| `degrees`, `aff`, `address`, `email`, `author-comment`, `etal` | further details of a person, as printed | `persons.title`, `persons.email`, `persons.street` | `degrees`, `aff`, `address`, `email`, `author-comment`, `etal` | – | `affiliation`, `occupation` | `person.honorific_prefix`, `person.email`, `person.contact_details` | – |
| `events.data[]` | the course of the affair: what happened, and when | `events.title_de`, `events.date`, `events.title_harmonized` | `history`, `pub-history` | `workflow`, `step`, `lifecycle`, `eventRef` | `listEvent`, `event` | – | – |
| `custom-meta` | a printed header entry without a place of its own: its name and its value | – | `custom-meta-group`, `custom-meta`, `meta-name`, `meta-value` | `proprietary` | – | – | – |
| `custom-meta` addressee | whom the affair is addressed to | `bodies.executive_name` | – | `docAuthority` | – | `motion.organization_id` | – |
| `custom-meta` polity, parliament, place | the polity and its parliament as printed, and the place of signing | `affairs.body_key`, `bodies.name`, `bodies.legislative_name` | – | `docJurisdiction`, `FRBRcountry`, `organization`, `location` | `orgName`, `placeName` | `organization`, `area` | – |
| `custom-meta` department | the department in charge | – | – | `TLCOrganization` | `org` | `organization` | – |
| `related-article` | another affair this one refers to | – | `related-article` | `ref`, `documentRef` | `ref`, `relatedItem` | – | – |
| `related-object` | an act, a plan or a report it refers to | – | `related-object` | `ref` | `bibl`, `ref` | – | – |
| `kwd-group` | printed keywords | – | `kwd-group`, `kwd` | `classification`, `keyword` | `keywords`, `term` | – | `KeywordsMetaField` |
| values per language | one value per language of the parliament (`title.de`, `title.fr`) | `affairs.title_de`, `affairs.title_fr`, `affairs.title_it`, `affairs.title_rm` | `@lang`, `trans-title`, `trans-abstract` | `FRBRlanguage`, `@language` | `@lang`, `langUsage` | – | `LanguageMetaField` |

- the record in JATS: describes one document; nothing stands above it.
- the record in Akoma Ntoso: a collection of documents, chosen for any reason.
- the record in Parla-CLARIN: describes one text or a corpus of them.
- `title` in Popolo: a motion has its text, no title.
- `type_name` in Akoma Ntoso: docType marks the word in the text; the twelve document types of the schema have none for a submission of a member.
- `contributors.data[]` in Popolo: one creator per motion.
- `role` in Parla-CLARIN: the role within an organisation, not towards a text.
- `role` in Popolo: the role within an organisation.
- `events.data[]` in JATS: the dates of a publication, not of a procedure.
- `events.data[]` in Parla-CLARIN: an event in the life of a person, a place or an organisation.
- `custom-meta` addressee in OpenParlData: the name of the executive of a body, not a field of the affair.
- `custom-meta` addressee in Popolo: the organisation the motion is proposed in.
- `custom-meta` addressee in Akoma Ntoso: the authority the document was submitted to.

## The document

| Here | What it is | OpenParlData | JATS | Akoma Ntoso | Parla-CLARIN | Popolo | Docling |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `docs.data[]` | one document of the affair: its name, its format, its language, its pages | `docs.name`, `docs.url`, `docs.format`, `docs.language` | `article`, `article/@lang`, `counts`, `page-count` | `doc`, `FRBRManifestation`, `FRBRformat`, `FRBRlanguage` | `TEI`, `TEI/@lang`, `extent` | – | `name`, `origin`, `DocumentOrigin.mimetype`, `pages` |
| `article-type` | what the document is within the affair: the text handed in, the answer, the minutes | `docs.category_de`, `docs.category_harmonized` | `article/@article-type` | `doc/@name`, `bill`, `act`, `debateReport`, `statement`, `amendment` | `catRef` | – | – |
| `article-version` | the version as printed | – | `article-version` | `docStage`, `FRBRversionNumber` | `edition` | – | – |
| `abstract` | a summary, per language | – | `abstract`, `trans-abstract` | – | `abstract` | – | `SummaryMetaField` |
| `conference` | the session or meeting the document names | `meetings.name_de`, `meetings.begin_date`, `meetings.location` | `conference`, `conf-name`, `conf-date`, `conf-loc` | `session`, `legislature` | `meeting` | `motion.legislative_session_id`, `event` | – |
| `journal-meta`, `volume`, `issue`, `fpage`, `lpage` | press and periodicals among the documents | `docs.news_id` | `journal-meta`, `journal-title`, `publisher-name`, `issn`, `volume`, `issue`, `fpage`, `lpage` | `publication` | `bibl` | – | – |
| `body` | the build-up of the document, the text unabridged | `docs.text` | `body` | `mainBody`, `body` | `text`, `body` | `motion.text` | `body`, `texts` |
| `response` | the answer within the same document | – | `response`, `response/@response-type` | `answer` | – | – | – |
| `back` | what follows the text | – | `back` | `conclusions`, `attachments` | `back` | – | – |

- `article-type` in OpenParlData: free text per parliament; the harmonised list names papers of a meeting.
- `body` in OpenParlData: the text as one field.
- `body` in Popolo: the text as one field.
- `response` in Akoma Ntoso: an answer to a question, as part of a debate.
- `response` in OpenParlData: the answer is a file of its own at the same affair.

## The blocks

| Here | What it is | OpenParlData | JATS | Akoma Ntoso | Parla-CLARIN | Popolo | Docling |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sec` | a section with its heading | – | `sec`, `sec/@sec-type`, `title` | `hcontainer`, `hcontainer/@name`, `heading` | `div`, `div/@type`, `head` | – | `SectionHeaderItem`, `GroupItem` |
| `p` | a paragraph | – | `p` | `p` | `p` | – | `TextItem` |
| `list` | a list, numbered questions | – | `list`, `list-item` | `blockList`, `item`, `ul`, `ol`, `li` | `list`, `item` | – | `ListGroup`, `ListItem` |
| `def-list` | label and value, as on a cover sheet | – | `def-list`, `def-item`, `term`, `def` | – | `list`, `label`, `item` | – | `KeyValueItem` |
| `table-wrap` | a table | – | `table-wrap`, `table` | `table`, `tr`, `td` | `table`, `row`, `cell` | – | `TableItem`, `TableData`, `TableCell` |
| `graphic` | an image, a coat of arms, a plan | – | `graphic` | `img` | `figure`, `graphic` | – | `PictureItem` |
| `sig-block` | a signature | – | `sig-block`, `sig` | `signature` | – | – | – |
| `app` | an appendix | – | `app-group`, `app` | `attachment` | `back`, `div/@type` | – | – |
| `fn` | a footnote | – | `fn-group`, `fn` | `authorialNote` | `note` | – | `TextItem.label=footnote` |
| `ref-list` | a list of references | – | `ref-list`, `ref` | – | `listBibl`, `bibl` | – | `TextItem.label=reference` |
| `notes` | a note outside the flow of the text | – | `notes` | `notes`, `note` | `note` | – | `TextItem.content_layer=notes` |

## Where a value comes from

| Here | What it is | OpenParlData | JATS | Akoma Ntoso | Parla-CLARIN | Popolo | Docling |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `source`, `sources` | the place of a value: the document and the block it was taken from | – | – | `eop` | `facsimile`, `surface`, `zone`, `@facs`, `pb` | `motion.sources`, `link.url` | `TextItem.prov`, `ProvenanceItem.page_no`, `ProvenanceItem.bbox`, `ProvenanceItem.charspan` |
| `id`, `page`, `x`, `y`, `width`, `height` | the block: its id, its page and its box in the page image | – | `@id` | `@eId` | `@id`, `zone/@ulx`, `zone/@uly`, `zone/@lrx`, `zone/@lry` | – | `TextItem.self_ref`, `BoundingBox.l`, `BoundingBox.t`, `BoundingBox.r`, `BoundingBox.b`, `PageItem.size` |
| `how`, `approve` | how the value got its place, and whether a person should look | – | – | `@status` | `@cert`, `@resp`, `unclear`, `supplied` | – | – |
| `review` | what a person decided about a value: when, who, the value before, the rule | – | – | – | `revisionDesc`, `change`, `respStmt` | – | – |
| `isOCR` | whether the text of a block comes from text recognition | – | – | – | – | – | – |
| `font`, `font-size`, `color` | how the block is set | – | `styled-content`, `styled-content/@style` | `@style`, `@class` | `hi`, `@rend` | – | `TextItem.formatting`, `Formatting` |

- `source`, `sources` in Akoma Ntoso: marks where the page breaks; the value stays marked where it stands in the text.
- `source`, `sources` in Popolo: a link per object.
- `source`, `sources` in Docling: the place of every item on its page; an item is text, not a value.
- `how`, `approve` in Akoma Ntoso: of a passage: editorial, incomplete, unknown and seven more.
- `review` in Parla-CLARIN: the revision of the file, not of one value.

## The controlled lists

| Here | What it is | OpenParlData | JATS | Akoma Ntoso | Parla-CLARIN | Popolo | Docling |
| --- | --- | --- | --- | --- | --- | --- | --- |
| types of affairs | `data/knowledge/vocabulary.json`, list `types`: what a parliament calls a type and the standard type it stands for | `affairs.type_harmonized_id`, `affairs.type_harmonized_wikidata_id` | `subject`, `@vocab`, `@vocab-term` | `TLCConcept` | `taxonomy`, `category`, `catDesc` | `motion.classification` | – |
| roles | the same file, list `roles`: the standard roles and what every parliament calls them | `contributors.role_harmonized` | `role`, `@vocab-term` | `TLCRole` | `affiliation/@role` | `membership.role`, `post.role` | – |
| kinds of groups | the same file, list `groups` | `groups.type_harmonized` | – | `TLCOrganization` | `org/@type` | `organization.classification` | – |
| names of events | the same file, list `events` | `events.title_harmonized`, `events.title_harmonized_wikidata_id` | – | `TLCEvent` | `event/@type` | – | – |
| kinds of documents | `data/knowledge/kinds.json`: seven kinds with the words that tell them | `docs.category_harmonized` | `article/@article-type` | `doc/@name` | `taxonomy` | – | – |
| – | the state of an affair in its procedure: not a list here, the course stands in `events` | `affairs.state_name_de`, `affairs.state_name_harmonized_de` | – | `docStatus`, `docStage` | – | – | – |
| – | the outcome of a decision: not a field here (tried as one on 11 October 2026, not taken in) | `votings.decision`, `votings.results_yes`, `votings.results_no` | – | `voting`, `outcome`, `count` | – | `motion.result`, `vote_event.result`, `vote_event.counts` | – |

- types of affairs in Popolo: a free text.
