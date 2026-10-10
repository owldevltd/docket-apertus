import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Api } from '../api/api';
import { Parliament, VocabularyRow } from '../api/types';
import { Who } from '../shared/who';
import { LISTS, StampPipe } from '../shared/words';

type ListName = VocabularyRow[ 'list' ];

// The vocabulary in the admin: what a parliament calls a thing and the standard name it stands for. The stem
// comes from OpenParlData, which calls it provisional, so every row can be changed here: a person sets
// another standard for a name, adds a name the stem does not have, or takes that back. The server holds the
// rows; the screen shows one list and one parliament at a time.
@Component( {
    selector: 'app-vocabulary',
    imports: [ FormsModule, MatButtonModule, MatFormFieldModule, MatSelectModule, StampPipe ],
    templateUrl: './vocabulary.html',
    styleUrl: './vocabulary.scss',
} )
export class VocabularyArea implements OnInit {
    private readonly api = inject( Api );
    private readonly who = inject( Who );
    private readonly snack = inject( MatSnackBar );

    readonly rows = signal<VocabularyRow[]>( [] );
    readonly parliaments = signal<Record<string, Parliament>>( {} );
    readonly list = signal<ListName>( 'types' );
    // the parliament shown, by its key; empty for the standard names of the list
    readonly body = signal( '' );
    readonly busy = signal( false );
    readonly newName = signal( '' );
    readonly newStandard = signal( '' );
    // counts the loads: a row is drawn anew after each, so a choice the server refused does not stay on screen
    readonly round = signal( 0 );
    readonly words = { LISTS };
    readonly lists: ListName[] = [ 'types', 'events', 'groups', 'roles' ];

    // the standard names of the chosen list, by name
    readonly standards = computed( () => this.rows().filter( ( r ) => r.list === this.list() && r.body === '' ) );

    // the same for the table: the events by how often OpenParlData holds them
    readonly standardsShown = computed( () => {
        const rows = [ ...this.standards() ];
        return this.list() === 'events' ? rows.sort( ( a, b ) => ( b.count ?? 0 ) - ( a.count ?? 0 ) ) : rows;
    } );

    readonly named = computed( () => this.rows().filter( ( r ) => r.body !== '' ) );
    readonly byHand = computed( () => this.rows().filter( ( r ) => r.origin === 'person' ).length );
    readonly bodyCount = computed( () => new Set( this.named().map( ( r ) => r.body ) ).size );

    // the day of the stem the rows come from: the newest one
    readonly fetched = computed( () => this.rows().map( ( r ) => r.fetched || '' ).sort().pop() || null );

    // every named parliament, by name, with the count of its names in the chosen list
    readonly bodies = computed( () => {
        const counts: Record<string, number> = {};
        for ( const r of this.named() ) {
            if ( r.list === this.list() ) {
                counts[ r.body ] = ( counts[ r.body ] || 0 ) + 1;
            }
        }
        const known = this.parliaments();
        const keys = new Set( [ ...Object.keys( known ), ...Object.keys( counts ) ] );
        return [ ...keys ].map( ( key ) => ( {
            key,
            // a municipality often has no name for its parliament in the knowledge
            name: known[ key ] ? [ known[ key ].name, known[ key ].parliament ].filter( Boolean ).join( ' · ' ) : key,
            count: counts[ key ] || 0,
        } ) ).sort( ( a, b ) => a.name.localeCompare( b.name, 'de' ) );
    } );

    readonly shown = computed( () => this.rows().filter( ( r ) => r.list === this.list() && r.body === this.body() ) );

    async ngOnInit(): Promise<void> {
        try {
            this.parliaments.set( await this.api.parliaments() );
            await this.load();
        } catch ( e ) {
            this.snack.open( ( e as Error ).message, 'OK', { duration: 6000 } );
        }
    }

    async load(): Promise<void> {
        this.rows.set( await this.api.vocabulary() );
        this.round.update( ( n ) => n + 1 );
    }

    key( row: VocabularyRow ): string {
        return row.list + '|' + row.body + '|' + row.name + '|' + this.round();
    }

    n( value: number ): string {
        return value.toLocaleString( 'de-CH' );
    }

    async change( row: VocabularyRow, standard: string ): Promise<void> {
        await this.guard( ( by ) => this.api.setName( row, standard || null, by ) );
    }

    async add(): Promise<void> {
        const name = this.newName().trim();
        if ( !name || !this.body() ) {
            return;
        }
        const row = { list: this.list(), body: this.body(), name };
        const done = await this.guard( ( by ) => this.api.setName( row, this.newStandard() || null, by ) );
        if ( done ) {
            this.newName.set( '' );
            this.newStandard.set( '' );
        }
    }

    async reset( row: VocabularyRow ): Promise<void> {
        await this.guard( () => this.api.resetName( row ) );
    }

    // a change carries who made it; the rows are read again afterwards, also when the server said no
    private async guard( action: ( by: string ) => Promise<unknown> ): Promise<boolean> {
        const by = this.who.require();
        this.busy.set( true );
        let done = false;
        try {
            if ( !by ) {
                throw new Error( 'Ohne Kürzel wird nichts geändert.' );
            }
            await action( by );
            done = true;
        } catch ( e ) {
            this.snack.open( ( e as Error ).message, 'OK', { duration: 6000 } );
        }
        try {
            await this.load();
        } catch ( e ) {
            this.snack.open( ( e as Error ).message, 'OK', { duration: 6000 } );
        } finally {
            this.busy.set( false );
        }
        return done;
    }
}
