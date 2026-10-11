import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Api, queryOf } from '../api/api';
import { Listed, Parliament, Rec } from '../api/types';
import { Icon } from '../shared/icon';
import { GROUPS, LANGUAGES, LEVELS, dayOf, kindName } from '../shared/words';
import { docsOf, textIn, titleOf, typeOf, screenAt } from './records';
import { UrlBox } from './url-box';

// the table of the server an element is a row of, the key its name stands under there, and its icon
const KINDS: Record<string, { table: string; name: string; icon: string }> = {
    persons: { table: 'contributors', name: 'fullname', icon: 'person' },
    groups: { table: 'groups', name: 'name', icon: 'list' },
    meetings: { table: 'meetings', name: 'conf-name', icon: 'fields' },
};

// One person, one group or one meeting as a visitor sees it: what the affairs say of it, and every affair
// and every document it stands in, as on the pages of OpenParlData. Read from the affairs in the affair
// schema; the switch shows the rows of the table that follow from them for this name.
@Component( {
    selector: 'app-element',
    imports: [ RouterLink, Icon, UrlBox ],
    templateUrl: './element.html',
    styleUrl: './item.scss',
} )
export class Element implements OnInit {
    private readonly api = inject( Api );
    private readonly router = inject( Router );
    readonly kind = input.required<string>();
    readonly name = input.required<string>();
    readonly listed = signal<Listed | null>( null );
    readonly rows = computed( () => this.listed()?.data || [] );
    readonly affairs = signal<Rec[]>( [] );
    readonly bodies = signal<Record<string, Parliament>>( {} );
    readonly error = signal( '' );
    readonly json = signal( false );
    readonly words = { LANGUAGES, dayOf, kindName, titleOf, typeOf };

    readonly spec = computed( () => KINDS[ this.kind() ] || KINDS[ 'persons' ] );
    // what the rows say of the name beyond the affair: a person's parties and roles, a group's kinds, a
    // meeting's day and place
    readonly notes = computed( () => {
        const say = new Set<string>();
        for ( const r of this.rows() ) {
            if ( this.kind() === 'persons' ) {
                [ textIn( r[ 'party' ] ), textIn( r[ 'role_harmonized' ] ) || textIn( r[ 'role' ] ) ].filter( Boolean ).forEach( ( x ) => say.add( x ) );
            } else if ( this.kind() === 'groups' ) {
                say.add( GROUPS[ r[ 'type' ] ] || r[ 'type' ] );
            } else {
                [ dayOf( r[ 'conf-date' ] ), r[ 'conf-loc' ] ].filter( Boolean ).forEach( ( x ) => say.add( x ) );
            }
        }
        return [ ...say ];
    } );
    // the documents the name stands in: for a meeting the ones that name it, else those of its affairs
    readonly documents = computed( () => {
        const named = new Set( this.rows().map( ( r ) => r[ 'doc' ] ).filter( Boolean ) );
        return this.affairs().flatMap( ( a ) => docsOf( a )
            .filter( ( d ) => !named.size || named.has( d[ 'name' ] ) )
            .map( ( d ) => ( { doc: d, affair: a } ) ) );
    } );
    readonly address = computed( () => ( this.json()
        ? location.origin + '/api/' + this.spec().table + queryOf( { [ this.spec().name ]: this.name() } )
        : screenAt( this.router, [ '/' + this.kind(), this.name() ] ) ) );
    readonly raw = computed( () => JSON.stringify( this.listed(), null, 2 ) );

    async ngOnInit(): Promise<void> {
        try {
            this.bodies.set( await this.api.parliaments() );
            // the rows of this name alone, as the server holds them under the address the switch shows
            const listed = await this.api.table( this.spec().table, { [ this.spec().name ]: this.name() } );
            this.listed.set( listed );
            const ids = new Set( listed.data.map( ( r ) => r[ 'affair_id' ] ) );
            this.affairs.set( ( await this.api.records() ).data.filter( ( r ) => ids.has( r[ 'id' ] ) ) );
        } catch ( e ) {
            this.error.set( ( e as Error ).message );
        }
    }

    bodyName( record: Rec ): string {
        return this.bodies()[ String( record[ 'body_key' ] || '' ) ]?.name || String( record[ 'body_key' ] || '' );
    }

    level( record: Rec ): string {
        const level = this.bodies()[ String( record[ 'body_key' ] || '' ) ]?.level || '';
        return LEVELS[ level ] || level;
    }
}
