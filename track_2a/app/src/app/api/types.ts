// What the server answers with, as the API under /api/ shapes it. The record itself is the affair after the
// contract (data/schema/docket.json); the app reads only what it shows and never rebuilds it.

export interface Counts {
    places: number;
    open: number;
    done: number;
}

export interface AffairSummary {
    key: string;
    number: string | null;
    title: string | null;
    type: string | null;
    documents: string[];
    kinds: ( string | null )[];
    counts: Counts;
    updated_at: string | null;
}

export interface Review {
    at: string;
    decision: 'confirmed' | 'changed' | 'rejected';
    before?: string;
    by?: string;
    rule?: string;
}

export interface Same {
    count: number;
    examples: { key: string; value: unknown; doc: number }[];
}

// a value with a place: the path of its source object and of the value, and what people decided
export interface SourceEntry {
    source: string;
    path: string;
    label: string;
    value: unknown;
    doc: number | null;
    block: string | null;
    how: string | null;
    approve: boolean;
    review: Review | null;
    open: boolean;
    values?: Record<string, unknown>;
    same?: Same;
    // for the id of a person: the name the register holds for it
    hint?: string;
}

export interface DocumentInfo {
    name: string;
    id: number;
    pages: number;
}

export interface Block {
    id: string;
    page: number;
    type: string;
    x: number;
    y: number;
    width: number;
    height: number;
    approve?: boolean;
    title?: string;
    text?: string;
    rows?: string[][];
    items?: ( string | { term: string; def: string } )[];
    content?: Block[];
}

// number, title, date and type of an affair, found by what its fields are, not by the keys of the record
export interface Head {
    number: string | null;
    title: string | null;
    date: string | null;
    type: string | null;
}

export interface Affair {
    key: string;
    head: Head;
    record: Record<string, any>;
    documents: DocumentInfo[];
    sources: SourceEntry[];
    counts: Counts;
    updated_at: string | null;
    // after a decision: the rules it leaves proposed for the field, the one that reaches furthest first
    proposals?: Rule[];
}

export interface Decision {
    affair: string;
    doc: number | null;
    block: string | null;
    path: string;
    label: string;
    how: string | null;
    approve: boolean;
    decision: string;
    before: string | null;
    after: unknown;
    by: string | null;
    at: string;
    rule: string | null;
}

export interface DecisionBody {
    source: string;
    decision: 'confirmed' | 'changed' | 'rejected';
    by: string;
    after?: string;
    path?: string;
}

export interface FieldItem {
    value: string;
    block: string | null;
    how: string | null;
}

export interface FieldReport {
    value: string | null;
    state: string;
    items: FieldItem[];
    note?: string;
}

export interface FieldsReport {
    fields: Record<string, FieldReport>;
    first?: number[];
}

export interface Job {
    id: string;
    name: string;
    source: string;
    model: boolean;
    state: 'queued' | 'running' | 'done' | 'failed';
    created: string;
    started: string | null;
    finished: string | null;
    lines: string[];
    affairs: { key: string; documents: string[]; type: string; valid: boolean; kept: number }[];
    documents: unknown[];
    calls: number;
    error: string | null;
}

// what a proposed rule would change in the store
export interface Reach {
    count: number;
    affairs: number;
    examples: { key: string; before: string; after: string }[];
}

// A rule learnt from decisions. counting: one change so far; proposed: two, a person is asked; active: accepted;
// declined: a person said no; contradicted: a decision by hand speaks against it; off: switched off by hand.
export interface Rule {
    id: string;
    field: string;
    kind: string;
    parameter: string;
    to?: string;
    count: number;
    against?: number;
    confirmed: number;
    withdrawn: number;
    applied: number;
    active: boolean;
    state?: 'counting' | 'proposed' | 'active' | 'declined' | 'contradicted' | 'off';
    since: string | null;
    examples: { affair: string; before: string; after: string; by: string }[];
    reach?: Reach;
}

// the standard name of a type, an event or a kind of group, in the four languages of the record
export interface Standard {
    de: string | null;
    fr: string | null;
    it: string | null;
    en: string | null;
}

// A row of the vocabulary: what a parliament calls a thing (body is its key at OpenParlData) and the standard
// name it stands for, or none. A row with an empty body is a standard name itself. A row a person set says
// who and when, and keeps what the stem said beside it.
export interface VocabularyRow {
    list: 'types' | 'events' | 'groups' | 'roles';
    body: string;
    name: string;
    label: string;
    lang?: string | null;
    standard: Standard | null;
    origin: 'stem' | 'person';
    fetched?: string | null;
    by?: string;
    at?: string;
    stem?: { standard: Standard | null; fetched: string | null };
    wikidata?: string;
    count?: number;
    removed?: boolean;
}

export interface Parliament {
    name: string;
    parliament: string;
    canton: string | null;
    level: string | null;
}

export interface Health {
    ok: boolean;
    store: string;
    model: boolean;
    admin: 'token' | 'open';
    at: string;
}

// The fields of the fields file with what each is, held against the store: in how many documents a field was
// asked, and in how many never, because the document was read before the field existed.
export interface DefinitionField {
    name: string;
    entity: string;
    role: string;
    lookup: string;
    list: string;
    asked: number;
    never: number;
}

export interface Definition {
    version: string;
    documents: number;
    versions: Record<string, number>;
    entities: { name: string; lookup?: string; list?: string; means: string }[];
    fields: DefinitionField[];
    gone: { name: string; asked: number }[];
}

// What the second opinion learnt from the store: per way (the usual place in a parliament, or the network)
// and field, how often it agreed and disagreed on documents held back, and whether it is used in the runs.
export interface LearntWay {
    way: 'place' | 'network';
    parliament: string;
    field: string;
    documents?: number;
    share?: number;
    cut: number | null;
    agree: number;
    disagree: number;
    use: boolean;
}

export interface Learnt {
    documents: number;
    ways: LearntWay[];
}
