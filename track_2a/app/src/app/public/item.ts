import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Api } from '../api/api';
import { Parliament, Rec } from '../api/types';
import { Icon } from '../shared/icon';
import { LABELS, LANGUAGES, LEVELS, dayOf, kindName } from '../shared/words';
import { docsOf, eventsOf, peopleOf, textIn, titleOf, typeOf, screenAt } from './records';
import { UrlBox } from './url-box';

// One affair as a visitor sees it, after the detail of OpenParlData's public app: the head, the rows with
// what the record holds, those who take part by their role, the course, the documents. All of it is read
// from the record in the affair schema, which the switch shows as it is. Nothing can be changed here.
@Component( {
    selector: 'app-item',
    imports: [ RouterLink, Icon, UrlBox ],
    templateUrl: './item.html',
    styleUrl: './item.scss',
} )
export class Item implements OnInit {
    private readonly api = inject( Api );
    private readonly router = inject( Router );
    readonly key = input.required<string>();
    readonly record = signal<Rec | null>( null );
    readonly bodies = signal<Record<string, Parliament>>( {} );
    readonly error = signal( '' );
    readonly json = signal( false );
    readonly words = { LANGUAGES, dayOf, kindName, textIn };

    readonly title = computed( () => titleOf( this.record() || {} ) );
    readonly body = computed( () => this.bodies()[ String( this.record()?.[ 'body_key' ] || '' ) ] );
    readonly level = computed( () => LEVELS[ this.body()?.level || '' ] || '' );
    readonly docs = computed( () => docsOf( this.record() || {} ) );
    readonly meta = computed( () => {
        const r = this.record() || {};
        return [ r[ 'number' ] ? $localize`Nr. ${r[ 'number' ]}:number:` : '', dayOf( r[ 'begin_date' ] ), typeOf( r ) ].filter( Boolean );
    } );
    readonly rows = computed( () => {
        const r = this.record() || {};
        const rows: { label: string; value: string }[] = [];
        const add = ( label: string, value: unknown ) => {
            const text = textIn( value );
            if ( text ) {
                rows.push( { label, value: text } );
            }
        };
        add( $localize`ID`, r[ 'id' ] );
        add( $localize`Titel`, r[ 'title' ] );
        add( $localize`Nummer`, r[ 'number' ] );
        add( $localize`Beginn`, dayOf( r[ 'begin_date' ] ) );
        add( $localize`Art`, r[ 'type_name' ] );
        add( $localize`Art (harmonisiert)`, r[ 'type_harmonized' ] );
        add( $localize`Körperschaft`, [ this.body()?.name || r[ 'body_key' ], this.body()?.parliament ].filter( Boolean ).join( ', ' ) );
        for ( const m of r[ 'custom-meta' ] || [] ) {
            add( LABELS[ m[ 'meta-name' ] ] || m[ 'meta-name' ], m[ 'meta-value' ] );
        }
        add( $localize`Schlagwörter`, ( r[ 'kwd-group' ] || [] ).join( ', ' ) );
        add( $localize`Verwandte Geschäfte`, ( r[ 'related-article' ] || [] ).map( ( x: Rec ) => x[ 'number' ] || x[ 'affair_id' ] ).join( ', ' ) );
        add( $localize`Verweise`, ( r[ 'related-object' ] || [] ).map( ( x: Rec ) => x[ 'text' ] ).join( '; ' ) );
        return rows;
    } );
    // those who take part, under their role, in the order the record names them
    readonly roles = computed( () => {
        const roles: { role: string; people: { name: string; party: string; behalf: string }[] }[] = [];
        for ( const c of peopleOf( this.record() || {} ) ) {
            const role = textIn( c[ 'role_harmonized' ] ) || textIn( c[ 'role' ] ) || $localize`Beteiligte`;
            let group = roles.find( ( x ) => x.role === role );
            if ( !group ) {
                group = { role, people: [] };
                roles.push( group );
            }
            group.people.push( { name: c[ 'fullname' ] || '', party: textIn( c[ 'party' ] ), behalf: c[ 'on-behalf-of' ] || '' } );
        }
        return roles;
    } );
    readonly events = computed( () => eventsOf( this.record() || {} )
        .map( ( e ) => ( { title: textIn( e[ 'title' ] ), date: dayOf( e[ 'date' ] ) } ) ) );
    readonly address = computed( () => ( this.json() ? location.origin + '/api/records/' + encodeURIComponent( this.key() )
        : screenAt( this.router, [ '/affairs', this.key() ] ) ) );
    readonly raw = computed( () => JSON.stringify( this.record(), null, 2 ) );

    async ngOnInit(): Promise<void> {
        try {
            this.bodies.set( await this.api.parliaments() );
            this.record.set( await this.api.record( this.key() ) );
        } catch ( e ) {
            const gone = ( e as { status?: number } ).status === 404;
            this.error.set( gone ? $localize`Dieses Geschäft gibt es im Bestand nicht.` : ( e as Error ).message );
        }
    }
}
