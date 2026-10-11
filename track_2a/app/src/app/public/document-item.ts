import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Api } from '../api/api';
import { Parliament, Rec } from '../api/types';
import { Icon } from '../shared/icon';
import { LANGUAGES, dayOf, kindName } from '../shared/words';
import { docsOf, textIn, titleOf, screenAt } from './records';
import { Sheet } from './sheet';
import { UrlBox } from './url-box';

// One document as a visitor sees it: what the record of its affair says about it, and its pages set from
// the blocks the record holds, every text at its place and in its size. Read from the affair in the affair
// schema and from nothing else, no image of a page; the switch shows the document's part of the record, its
// entry under `docs`.
@Component( {
    selector: 'app-document-item',
    imports: [ RouterLink, Icon, Sheet, UrlBox ],
    templateUrl: './document-item.html',
    styleUrl: './item.scss',
} )
export class DocumentItem implements OnInit {
    private readonly api = inject( Api );
    private readonly router = inject( Router );
    readonly name = input.required<string>();
    readonly affair = signal<Rec | null>( null );
    readonly bodies = signal<Record<string, Parliament>>( {} );
    readonly error = signal( '' );
    readonly json = signal( false );
    readonly page = signal( 1 );

    // the document in the affair schema: its entry in the record of its affair
    readonly entry = computed<Rec>( () => docsOf( this.affair() || {} ).find( ( d ) => d[ 'name' ] === this.name() ) || {} );
    readonly affairTitle = computed( () => titleOf( this.affair() || {} ) );
    readonly body = computed( () => this.bodies()[ String( this.affair()?.[ 'body_key' ] || '' ) ] );
    readonly pages = computed( () => this.entry()[ 'page-count' ] || 1 );
    readonly kind = computed( () => kindName( this.entry()[ 'article-type' ] ) );
    readonly language = computed( () => LANGUAGES[ this.entry()[ 'language' ] || '' ] || '' );
    readonly meta = computed( () => [ this.kind(), this.language(), $localize`${this.pages()}:pages: S.` ].filter( Boolean ) );
    readonly rows = computed( () => {
        const e = this.entry();
        const rows: { label: string; value: string }[] = [];
        const add = ( label: string, value: unknown ) => {
            const text = textIn( value );
            if ( text ) {
                rows.push( { label, value: text } );
            }
        };
        add( $localize`Name`, e[ 'name' ] || this.name() );
        add( $localize`Dokumenttyp`, this.kind() );
        add( $localize`Sprache`, this.language() );
        add( $localize`Seiten`, this.pages() );
        add( $localize`Format`, e[ 'format' ] );
        add( $localize`Fassung`, e[ 'article-version' ] );
        const c = e[ 'conference' ] || {};
        add( $localize`Sitzung`, [ c[ 'conf-name' ], dayOf( c[ 'conf-date' ] ), c[ 'conf-loc' ] ].filter( Boolean ).join( ', ' ) );
        add( $localize`Zusammenfassung`, e[ 'abstract' ] );
        return rows;
    } );
    // the answers within the document, as the record holds them, each with the page it begins on
    readonly answers = computed( () => ( ( this.entry()[ 'response' ] || [] ) as Rec[] )
        .filter( ( r ) => r[ 'body' ]?.length )
        .map( ( r ) => ( { title: r[ 'title' ] || $localize`Antwort`, page: r[ 'body' ][ 0 ].page as number } ) ) );
    // every block of the document as the record holds it: the body, the content of a section beside the
    // section, and the answers within the document, which the record keeps apart
    readonly blocks = computed<Rec[]>( () => {
        const e = this.entry();
        const out: Rec[] = [];
        const take = ( list: Rec[] ) => {
            for ( const b of list || [] ) {
                out.push( b );
                take( b[ 'content' ] );
            }
        };
        take( e[ 'body' ] );
        for ( const answer of e[ 'response' ] || [] ) {
            take( answer[ 'body' ] );
        }
        return out;
    } );
    readonly address = computed( () => ( this.json()
        ? location.origin + '/api/documents/' + encodeURIComponent( this.name() ) + '/record'
        : screenAt( this.router, [ '/documents', this.name() ] ) ) );
    readonly raw = computed( () => JSON.stringify( this.entry(), null, 2 ) );

    async ngOnInit(): Promise<void> {
        try {
            this.bodies.set( await this.api.parliaments() );
            // the affair that holds the document: the one whose record names it
            const listed = await this.api.records();
            const held = listed.data.find( ( r ) => docsOf( r ).some( ( d ) => d[ 'name' ] === this.name() ) );
            if ( !held ) {
                this.error.set( $localize`Dieses Dokument gibt es im Bestand nicht.` );
                return;
            }
            this.affair.set( await this.api.record( String( held[ 'id' ] ) ) );
        } catch ( e ) {
            this.error.set( ( e as Error ).message );
        }
    }

    turn( by: number ): void {
        this.page.set( Math.min( this.pages(), Math.max( 1, this.page() + by ) ) );
    }
}
