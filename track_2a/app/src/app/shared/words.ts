import { Pipe, PipeTransform } from '@angular/core';
import { Block, Rule, SourceEntry } from '../api/types';

// The words of the app, German first; the field names of the record translated for the screen. The fields
// file names its fields in German already (nummer, titel), the record keeps OpenParlData's keys.

export const LABELS: Record<string, string> = {
    'number': 'Nummer',
    'title': 'Titel',
    'type_name': 'Art',
    'begin_date': 'Datum',
    'kwd-group': 'Schlagwort',
    'docs.abstract': 'Zusammenfassung',
    'docs.article-version': 'Fassung',
    'docs.article-type': 'Dokumenttyp',
    'contributors.fullname': 'Beteiligte',
    'contributors.party': 'Partei',
    'contributors.on-behalf-of': 'Im Namen von',
    'contributors.person_id': 'Person im Register',
    'events.title': 'Ereignis',
    'events.date': 'Ereignisdatum',
    'docs.conference.conf-name': 'Sitzung',
    'docs.conference.conf-date': 'Sitzungsdatum',
    'docs.conference.conf-loc': 'Sitzungsort',
    'related-article.number': 'Verwandtes Geschäft',
    'related-object.text': 'Verweis',
};

export const HOW: Record<string, string> = {
    literal: 'wörtlich',
    derived: 'abgeleitet',
    cited: 'vom Modell genannt',
    composed: 'vom Modell formuliert',
};

export const DECISION: Record<string, string> = {
    confirmed: 'bestätigt',
    changed: 'geändert',
    rejected: 'verworfen',
};

export const STATE: Record<string, string> = {
    queued: 'wartend',
    running: 'läuft',
    done: 'erfolgreich',
    failed: 'fehlgeschlagen',
};

// the kinds of documents (data/knowledge/kinds.json); an unknown one is shown as it is
export const DOCUMENT_KINDS: Record<string, string> = {
    'submission': 'Eingereichter Text',
    'answer': 'Antwort',
    'bill': 'Vorlage',
    'minutes': 'Protokoll',
    'committee-report': 'Kommissionsbericht',
    'act': 'Erlass',
    'attachment': 'Beilage',
};

export function kindName( kind: string | null | undefined ): string {
    return kind ? DOCUMENT_KINDS[ kind ] || kind : 'Typ offen';
}

// the lists of the vocabulary, and where a row comes from
export const LISTS: Record<string, string> = {
    types: 'Arten',
    events: 'Ereignisse',
    groups: 'Gruppen',
};

export const ORIGIN: Record<string, string> = {
    stem: 'Stamm',
    person: 'von Hand',
};

export const RULE_STATE: Record<string, string> = {
    counting: 'zählt',
    proposed: 'vorgeschlagen',
    active: 'aktiv',
    declined: 'abgelehnt',
    contradicted: 'widersprochen',
    off: 'aus',
};

// what a rule does, in words
export function ruleWords( rule: Rule ): string {
    const p = '„' + rule.parameter + '“';
    switch ( rule.kind ) {
        case 'prefix-off': return p + ' am Anfang weg';
        case 'suffix-off': return p + ' am Ende weg';
        case 'prefix-on': return p + ' am Anfang dazu';
        case 'suffix-on': return p + ' am Ende dazu';
        case 'digits': return 'Buchstabe als Ziffer gelesen (' + rule.parameter + ')';
        case 'spelling': return 'Schreibung ' + p;
        case 'value': return p + ' wird „' + ( rule.to ?? '' ) + '“';
        default: return rule.kind + ' ' + p;
    }
}

export function labelOf( entry: SourceEntry ): string {
    return LABELS[ entry.label ] || entry.label;
}

// the last part of a value path, for entries with several values (conf-date, conf-loc)
export function leafOf( path: string ): string {
    const leaf = path.split( '.' ).pop() || path;
    return LABELS[ 'docs.conference.' + leaf ] || LABELS[ leaf ] || leaf;
}

export function blocksOf( body: Block[] | undefined ): Block[] {
    const out: Block[] = [];
    for ( const b of body || [] ) {
        out.push( b );
        if ( b.type === 'sec' ) {
            out.push( ...( b.content || [] ) );
        }
    }
    return out;
}

export function textOf( block: Block | undefined ): string {
    if ( !block ) {
        return '';
    }
    if ( block.rows ) {
        return block.rows.map( ( r ) => r.join( ' | ' ) ).join( '\n' );
    }
    if ( block.items ) {
        return block.items.map( ( i ) => ( typeof i === 'string' ? i : i.term + ': ' + i.def ) ).join( '\n' );
    }
    return block.title || block.text || '';
}

// "2026-10-08T15:12:00+02:00" as "08.10.2026 15:12"; the server's zone is the one shown
@Pipe( { name: 'stamp' } )
export class StampPipe implements PipeTransform {
    transform( value: string | null | undefined, withTime = true ): string {
        if ( !value ) {
            return '–';
        }
        const [ day, time ] = value.split( 'T' );
        const [ y, m, d ] = day.split( '-' );
        const date = d + '.' + m + '.' + y;
        return withTime && time ? date + ' ' + time.slice( 0, 5 ) : date;
    }
}
