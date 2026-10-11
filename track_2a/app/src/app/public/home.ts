import { Component, OnInit, computed, effect, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Api, queryOf } from '../api/api';
import { Listed, Parliament, Rec } from '../api/types';
import { Icon } from '../shared/icon';
import { GROUPS, LANGUAGES, LEVELS, dayOf, kindName } from '../shared/words';
import { SCREENS, docsOf, textIn, titleOf, typeOf } from './records';
import { UrlBox } from './url-box';

type Tab = 'affairs' | 'documents' | 'persons' | 'groups' | 'meetings' | 'events';

// the table of the server a tab reads, where it is not the affairs themselves
const TABLE: Partial<Record<Tab, string>> = { persons: 'contributors', groups: 'groups', meetings: 'meetings', events: 'events' };

// one line of a tab that is neither an affair nor a document: a person, a group, a meeting
interface Named {
    name: string;
    note: string;
    affairs: string[];
}

// The public start: what a visitor sees. The affairs the store holds and what follows from them, the
// documents, the persons, the groups, the meetings and the events, to search and to filter; the address of
// what is shown, and its JSON. All of it is read from the affairs in the affair schema. Nothing here changes
// anything: looking at values and deciding on them is the administration's part.
@Component( {
    selector: 'app-home',
    imports: [ RouterLink, Icon, UrlBox ],
    templateUrl: './home.html',
    styleUrl: './home.scss',
} )
export class Home implements OnInit {
    private readonly api = inject( Api );
    private readonly route = inject( ActivatedRoute );
    private readonly router = inject( Router );

    // everything the store holds, for the choices of the filters and the counts at the left
    readonly all = signal<Rec[]>( [] );
    readonly found = signal<Listed>( { meta: { total: 0, count: 0 }, data: [] } );
    readonly rows = signal<Listed>( { meta: { total: 0, count: 0 }, data: [] } );
    readonly bodies = signal<Record<string, Parliament>>( {} );
    readonly error = signal( '' );
    readonly tab = signal<Tab>( 'affairs' );
    readonly q = signal( '' );
    readonly filters = signal( false );
    readonly body = signal( '' );
    readonly type = signal( '' );
    readonly kind = signal( '' );
    readonly language = signal( '' );
    readonly json = signal( false );
    readonly words = { LANGUAGES, dayOf, kindName, textIn, titleOf, typeOf, docsOf };
    readonly tabs: { id: Tab; icon: string }[] = [
        { id: 'affairs', icon: 'affair' },
        { id: 'documents', icon: 'document' },
        { id: 'persons', icon: 'person' },
        { id: 'groups', icon: 'list' },
        { id: 'meetings', icon: 'fields' },
        { id: 'events', icon: 'runs' },
    ];

    readonly asked = computed( () => {
        const asked: Record<string, string> = {};
        const set = ( name: string, value: string ) => {
            if ( value.trim() ) {
                asked[ name ] = value.trim();
            }
        };
        set( 'q', this.q() );
        set( 'body_key', this.body() );
        set( 'type', this.type() );
        set( 'kind', this.kind() );
        set( 'language', this.language() );
        return asked;
    } );
    readonly affairs = computed( () => this.found().data );
    readonly titles = computed( () => new Map( this.all().map( ( r ) => [ String( r[ 'id' ] ), titleOf( r ) ] as [ string, string ] ) ) );
    readonly documents = computed( () => this.affairs().flatMap( ( r ) => docsOf( r )
        .filter( ( d ) => ( !this.kind() || d[ 'article-type' ] === this.kind() ) && ( !this.language() || d[ 'language' ] === this.language() ) )
        .map( ( d ) => ( { doc: d, affair: r } ) ) ) );
    // persons, groups and meetings: every name once, with the affairs it stands in
    readonly named = computed<Named[]>( () => {
        const tab = this.tab();
        const seen = new Map<string, Named>();
        for ( const row of this.rows().data ) {
            const name = tab === 'persons' ? String( row[ 'fullname' ] || '' )
                : tab === 'meetings' ? String( row[ 'conf-name' ] || '' ) : String( row[ 'name' ] || '' );
            const note = tab === 'persons' ? textIn( row[ 'party' ] )
                : tab === 'meetings' ? [ dayOf( row[ 'conf-date' ] ), row[ 'conf-loc' ] ].filter( Boolean ).join( ', ' )
                    : String( row[ 'type' ] || '' );
            if ( !name ) {
                continue;
            }
            const one = seen.get( name ) || { name, note, affairs: [] };
            one.note = one.note || note;
            if ( !one.affairs.includes( String( row[ 'affair_id' ] ) ) ) {
                one.affairs.push( String( row[ 'affair_id' ] ) );
            }
            seen.set( name, one );
        }
        return [ ...seen.values() ].sort( ( a, b ) => a.name.localeCompare( b.name ) );
    } );
    readonly events = computed( () => [ ...this.rows().data ].sort( ( a, b ) => String( b[ 'date' ] || '' ).localeCompare( String( a[ 'date' ] || '' ) ) ) );
    readonly shown = computed( () => {
        const tab = this.tab();
        return tab === 'affairs' ? this.affairs().length : tab === 'documents' ? this.documents().length
            : tab === 'events' ? this.events().length : this.named().length;
    } );
    readonly total = computed( () => {
        const tab = this.tab();
        return tab === 'affairs' ? this.found().meta.total : tab === 'documents' ? this.all().reduce( ( n, r ) => n + docsOf( r ).length, 0 )
            : tab === 'events' ? this.rows().meta.total : this.named().length;
    } );

    readonly choices = computed( () => ( {
        bodies: unique( this.all().filter( ( r ) => r[ 'body_key' ] ).map( ( r ) => [ String( r[ 'body_key' ] ), this.bodyName( r ) ] ) ),
        types: unique( this.all().map( ( r ) => typeOf( r ) ).filter( Boolean ).map( ( t ) => [ t, t ] ) ),
        kinds: unique( this.all().flatMap( docsOf ).filter( ( d ) => d[ 'article-type' ] ).map( ( d ) => [ d[ 'article-type' ], kindName( d[ 'article-type' ] ) ] ) ),
        languages: unique( this.all().flatMap( docsOf ).filter( ( d ) => d[ 'language' ] ).map( ( d ) => [ d[ 'language' ], LANGUAGES[ d[ 'language' ] ] || d[ 'language' ] ] ) ),
    } ) );
    readonly filtered = computed( () => [ this.body(), this.type(), this.kind(), this.language() ].filter( Boolean ).length );

    readonly address = computed( () => {
        const tab = this.tab();
        if ( this.json() ) {
            return location.origin + '/api/' + ( TABLE[ tab ] || 'records' ) + queryOf( this.asked() );
        }
        return SCREENS + '/' + queryOf( tab === 'affairs' ? this.asked() : { tab, ...this.asked() } );
    } );
    readonly raw = computed( () => JSON.stringify( TABLE[ this.tab() ] ? this.rows() : this.found(), null, 2 ) );

    constructor() {
        // every change of the search asks the server anew and stands in the address, so a search can be linked
        effect( () => {
            const asked = this.asked();
            const tab = this.tab();
            const fail = ( e: unknown ) => this.error.set( ( e as Error ).message );
            this.api.records( asked ).then( ( listed ) => this.found.set( listed ) ).catch( fail );
            if ( TABLE[ tab ] ) {
                this.api.table( TABLE[ tab ]!, asked ).then( ( listed ) => this.rows.set( listed ) ).catch( fail );
            }
            this.router.navigate( [], { queryParams: tab === 'affairs' ? asked : { tab, ...asked }, replaceUrl: true } );
        } );
    }

    async ngOnInit(): Promise<void> {
        const from = this.route.snapshot.queryParamMap;
        this.q.set( from.get( 'q' ) || '' );
        this.body.set( from.get( 'body_key' ) || '' );
        this.type.set( from.get( 'type' ) || '' );
        this.kind.set( from.get( 'kind' ) || '' );
        this.language.set( from.get( 'language' ) || '' );
        this.tab.set( this.tabs.find( ( t ) => t.id === from.get( 'tab' ) )?.id || 'affairs' );
        this.filters.set( this.filtered() > 0 );
        try {
            this.bodies.set( await this.api.parliaments() );
            this.all.set( ( await this.api.records() ).data );
        } catch ( e ) {
            this.error.set( ( e as Error ).message );
        }
    }

    clear(): void {
        this.q.set( '' );
        this.body.set( '' );
        this.type.set( '' );
        this.kind.set( '' );
        this.language.set( '' );
    }

    valueOf( event: Event ): string {
        return ( event.target as HTMLInputElement | HTMLSelectElement ).value;
    }

    // the parliament of an affair by the key the record carries: its name and its level
    bodyName( record: Rec ): string {
        return this.bodies()[ String( record[ 'body_key' ] || '' ) ]?.name || String( record[ 'body_key' ] || '' );
    }

    level( record: Rec ): string {
        const level = this.bodies()[ String( record[ 'body_key' ] || '' ) ]?.level || '';
        return LEVELS[ level ] || level;
    }

    affairOf( id: unknown ): Rec {
        return this.all().find( ( r ) => r[ 'id' ] === id ) || { id };
    }

    // what kind of group a name is: a party, the one something was handed in for, the addressee, the department
    groupKind( kind: string ): string {
        return GROUPS[ kind ] || kind;
    }

    titleOfId( id: unknown ): string {
        return this.titles().get( String( id ) ) || String( id );
    }
}

// the choices of a filter: every value once, by its name
function unique( pairs: string[][] ): { value: string; name: string }[] {
    const seen = new Map<string, string>();
    for ( const [ value, name ] of pairs ) {
        seen.set( value, name );
    }
    return [ ...seen ].map( ( [ value, name ] ) => ( { value, name } ) ).sort( ( a, b ) => a.name.localeCompare( b.name ) );
}
