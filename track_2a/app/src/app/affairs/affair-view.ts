import { Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Api } from '../api/api';
import { Affair, Block, DecisionBody, FieldsReport, Rule, SourceEntry } from '../api/types';
import { Icon } from '../shared/icon';
import { Who } from '../shared/who';
import { LABELS, blocksOf, kindName, ruleWords } from '../shared/words';
import { PageView } from './page-view';
import { ValueCard } from './value-card';

// One affair: the head as in OpenParlData's detail, the page with its blocks at the left, every value with a
// place at the right, the open ones first. A decision goes to the server and the affair comes back whole. When
// the decision was the second of its kind, the server sends a proposed rule along: the screen asks whether the
// other values it fits should be set right too, and the person says yes, no or later.
@Component( {
    selector: 'app-affair-view',
    imports: [ RouterLink, MatButtonModule, MatSelectModule, Icon, PageView, ValueCard ],
    templateUrl: './affair-view.html',
    styleUrl: './affair-view.scss',
} )
export class AffairView implements OnInit {
    private readonly api = inject( Api );
    private readonly who = inject( Who );
    private readonly snack = inject( MatSnackBar );

    readonly key = input.required<string>();
    readonly affair = signal<Affair | null>( null );
    readonly error = signal( '' );
    readonly proposal = signal<Rule | null>( null );
    readonly ruleWords = ruleWords;
    readonly doc = signal( 0 );
    readonly page = signal( 1 );
    readonly focus = signal<string | null>( null );
    readonly reports = signal<Record<string, FieldsReport | null>>( {} );

    readonly record = computed( () => this.affair()?.record || {} );
    readonly title = computed( () => this.affair()?.head?.title || this.key() );
    readonly meta = computed( () => {
        const head = this.affair()?.head;
        return [ head?.number, head?.date, head?.type ].filter( Boolean );
    } );
    readonly current = computed( () => this.affair()?.documents[ this.doc() ] );
    readonly docRecord = computed( () => {
        const d = this.current();
        const docs: any[] = this.record()[ 'docs' ]?.data || [];
        return docs.find( ( x ) => x.id === d?.id ) || docs[ this.doc() ];
    } );
    readonly blocks = computed<Block[]>( () => blocksOf( this.docRecord()?.body ) );
    readonly kind = computed( () => this.docRecord()?.[ 'article-type' ] as string | undefined );
    readonly kindText = computed( () => kindName( this.kind() ) );
    readonly docSources = computed( () => ( this.affair()?.sources || [] ).filter( ( s ) => s.doc === this.docRecord()?.id ) );
    readonly sorted = computed( () => [ ...( this.affair()?.sources || [] ) ].sort( ( a, b ) => Number( b.open ) - Number( a.open ) ) );
    readonly image = computed( () => {
        const name = this.current()?.name || '';
        return ( n: number ) => this.api.pageImage( name, n );
    } );

    async ngOnInit(): Promise<void> {
        try {
            const affair = await this.api.affair( this.key() );
            this.affair.set( affair );
            const reports: Record<string, FieldsReport | null> = {};
            for ( const d of affair.documents ) {
                reports[ d.name ] = await this.api.fields( d.name );
            }
            this.reports.set( reports );
        } catch ( e ) {
            this.error.set( ( e as Error ).message );
        }
    }

    docName( s: SourceEntry ): string {
        return this.affair()?.documents.find( ( d ) => d.id === s.doc )?.name || '';
    }

    // the raw line of the model for a value, from the fields report of its document
    answerOf( s: SourceEntry ): string {
        const report = this.reports()[ this.docName( s ) ];
        if ( !report ) {
            return '';
        }
        const hit = Object.values( report.fields ).find( ( f ) =>
            f.items.some( ( i ) => i.block === s.block && String( i.value ) === String( s.value ) ) );
        return hit?.value || '';
    }

    selectDoc( index: number ): void {
        this.doc.set( index );
        this.page.set( 1 );
        this.focus.set( null );
    }

    jump( s: SourceEntry ): void {
        const i = this.affair()?.documents.findIndex( ( d ) => d.id === s.doc ) ?? -1;
        if ( i >= 0 && i !== this.doc() ) {
            this.doc.set( i );
        }
        const b = this.blocks().find( ( x ) => x.id === s.block );
        if ( b ) {
            this.page.set( b.page );
        }
        this.focus.set( s.block );
        document.querySelector( '.split' )?.scrollIntoView( { behavior: 'smooth', block: 'start' } );
    }

    async decide( body: DecisionBody ): Promise<void> {
        const by = this.who.require();
        if ( !by ) {
            return;
        }
        try {
            const affair = await this.api.decide( this.key(), { ...body, by } );
            this.affair.set( affair );
            this.proposal.set( affair.proposals?.[ 0 ] || null );
        } catch ( e ) {
            this.snack.open( ( e as Error ).message, 'OK', { duration: 6000 } );
        }
    }

    fieldOf( rule: Rule ): string {
        return LABELS[ rule.field ] || rule.field;
    }

    // yes changes every value the rule fits, here and in the other affairs; no keeps it from being proposed again
    async answer( rule: Rule, accept: boolean ): Promise<void> {
        const by = this.who.require();
        if ( !by ) {
            return;
        }
        try {
            const done = await this.api.answerRule( rule.id, accept, by );
            this.proposal.set( null );
            if ( accept ) {
                this.affair.set( await this.api.affair( this.key() ) );
                this.snack.open( done.applied + ( done.applied === 1 ? ' Wert geändert.' : ' Werte geändert.' ), 'OK', { duration: 5000 } );
            }
        } catch ( e ) {
            this.snack.open( ( e as Error ).message, 'OK', { duration: 6000 } );
        }
    }
}
