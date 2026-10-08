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

export interface Affair {
    key: string;
    record: Record<string, any>;
    documents: DocumentInfo[];
    sources: SourceEntry[];
    counts: Counts;
    updated_at: string | null;
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

export interface Rule {
    id: string;
    field: string;
    kind: string;
    parameter: string;
    count: number;
    confirmed: number;
    withdrawn: number;
    applied: number;
    active: boolean;
    since: string | null;
    examples: { affair: string; before: string; after: string; by: string }[];
}

export interface Health {
    ok: boolean;
    store: string;
    model: boolean;
    admin: 'token' | 'open';
    at: string;
}
