import { Pipe, PipeTransform } from '@angular/core';
import { Block, Rule, SourceEntry } from '../api/types';

// The words of the app: the keys of the record and the names of the fields, both English, named for the
// screen. Written in German; the build puts the wording of its language in their place.

export const LABELS: Record<string, string> = {
    'number': $localize`Nummer`,
    'title': $localize`Titel`,
    'type_name': $localize`Art`,
    'begin_date': $localize`Datum`,
    'kwd-group': $localize`Schlagwort`,
    'docs.abstract': $localize`Zusammenfassung`,
    'docs.article-version': $localize`Fassung`,
    'docs.article-type': $localize`Dokumenttyp`,
    'contributors.fullname': $localize`Beteiligte`,
    'contributors.party': $localize`Partei`,
    'contributors.on-behalf-of': $localize`Im Namen von`,
    'contributors.person_id': $localize`Person im Register`,
    'events.title': $localize`Ereignis`,
    'events.date': $localize`Ereignisdatum`,
    'docs.conference.conf-name': $localize`Sitzung`,
    'docs.conference.conf-date': $localize`Sitzungsdatum`,
    'docs.conference.conf-loc': $localize`Sitzungsort`,
    'related-article.number': $localize`Verwandtes Geschäft`,
    'related-object.text': $localize`Verweis`,
    // a rule names its field as the fields file does, whatever keys the record uses; a value under custom-meta
    // carries the field's name as well
    'type': $localize`Art`,
    'date': $localize`Datum`,
    'authors': $localize`Einreichende`,
    'cosigners': $localize`Mitunterzeichnende`,
    'party': $localize`Partei`,
    'on-behalf-of': $localize`Im Namen von`,
    'addressee': $localize`Adressat`,
    'place': $localize`Ort`,
    'parliament': $localize`Parlament`,
    'polity': $localize`Gemeinwesen`,
    'department': $localize`Departement`,
    'related': $localize`Verwandtes Geschäft`,
    'reference': $localize`Verweis`,
    'keywords': $localize`Schlagwort`,
    'event': $localize`Ereignis`,
    'event-date': $localize`Ereignisdatum`,
    'version': $localize`Fassung`,
    'summary': $localize`Zusammenfassung`,
    'session': $localize`Sitzung`,
    'session-date': $localize`Sitzungsdatum`,
    'session-place': $localize`Sitzungsort`,
};

export const HOW: Record<string, string> = {
    literal: $localize`wörtlich`,
    derived: $localize`abgeleitet`,
    cited: $localize`vom Modell genannt`,
    composed: $localize`vom Modell formuliert`,
};

export const DECISION: Record<string, string> = {
    confirmed: $localize`bestätigt`,
    changed: $localize`geändert`,
    rejected: $localize`verworfen`,
};

export const STATE: Record<string, string> = {
    queued: $localize`wartend`,
    running: $localize`läuft`,
    done: $localize`erfolgreich`,
    failed: $localize`fehlgeschlagen`,
};

// the kinds of documents (data/knowledge/kinds.json); an unknown one is shown as it is
export const DOCUMENT_KINDS: Record<string, string> = {
    'submission': $localize`Eingereichter Text`,
    'answer': $localize`Antwort`,
    'bill': $localize`Vorlage`,
    'minutes': $localize`Protokoll`,
    'committee-report': $localize`Kommissionsbericht`,
    'act': $localize`Erlass`,
    'attachment': $localize`Beilage`,
};

export function kindName( kind: string | null | undefined ): string {
    return kind ? DOCUMENT_KINDS[ kind ] || kind : $localize`Typ offen`;
}

// the lists of the vocabulary, and where a row comes from
export const LISTS: Record<string, string> = {
    types: $localize`Arten`,
    events: $localize`Ereignisse`,
    groups: $localize`Gruppen`,
    roles: $localize`Rollen`,
};

// what a value can be (data/knowledge/entities.json), and what stands behind an entity to hold a value against
export const ENTITIES: Record<string, string> = {
    body: $localize`Körperschaft`,
    identifier: $localize`Kennung`,
    category: $localize`Kategorie`,
    person: $localize`Person`,
    group: $localize`Gruppe`,
    place: $localize`Ort`,
    date: $localize`Datum`,
    event: $localize`Ereignis`,
    text: $localize`Text`,
};

export const LOOKUPS: Record<string, string> = {
    bodies: $localize`Liste der Parlamente`,
    vocabulary: $localize`Vokabular`,
    register: $localize`Register`,
};

export const ORIGIN: Record<string, string> = {
    stem: $localize`Stamm`,
    person: $localize`von Hand`,
};

export const RULE_STATE: Record<string, string> = {
    counting: $localize`zählt`,
    proposed: $localize`vorgeschlagen`,
    active: $localize`aktiv`,
    declined: $localize`abgelehnt`,
    contradicted: $localize`widersprochen`,
    off: $localize`aus`,
};

// what a rule does, in words
export function ruleWords( rule: Rule ): string {
    const p = '„' + rule.parameter + '“';
    switch ( rule.kind ) {
        case 'prefix-off': return $localize`${p}:value: am Anfang weg`;
        case 'suffix-off': return $localize`${p}:value: am Ende weg`;
        case 'prefix-on': return $localize`${p}:value: am Anfang dazu`;
        case 'suffix-on': return $localize`${p}:value: am Ende dazu`;
        case 'digits': return $localize`Buchstabe als Ziffer gelesen (${rule.parameter}:value:)`;
        case 'spelling': return $localize`Schreibung ${p}:value:`;
        case 'value': return $localize`${p}:value: wird „${rule.to ?? ''}:to:“`;
        case 'label': return $localize`der Wert ist, was im Dokument bei ${p}:value: steht`;
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

// what kind of group a name is, by where the record holds it
export const GROUPS: Record<string, string> = {
    'party': $localize`Partei`,
    'on-behalf-of': $localize`im Namen von`,
    'addressee': $localize`Adressat`,
    'department': $localize`Departement`,
};

// the level of a parliament, as the app names it
export const LEVELS: Record<string, string> = {
    'country': $localize`Bund`,
    'canton': $localize`Kanton`,
    'city': $localize`Stadt`,
    'municipality': $localize`Gemeinde`,
};

// a day as the documents print it: 2018-11-22 becomes 22.11.2018
export function dayOf( date: string | null | undefined ): string {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec( date || '' );
    return m ? m[ 3 ] + '.' + m[ 2 ] + '.' + m[ 1 ] : ( date || '' );
}

// the languages a document can be told to be in, as the app names them
export const LANGUAGES: Record<string, string> = {
    'de': $localize`Deutsch`,
    'fr': $localize`Französisch`,
    'it': $localize`Italienisch`,
    'rm': $localize`Rätoromanisch`,
    'en': $localize`Englisch`,
};

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
