import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Api } from '../api/api';
import { Definition, Health, Job, Learnt, Rule } from '../api/types';
import { Icon } from '../shared/icon';
import { Account } from '../shared/account';
import { ENTITIES, LABELS, LOOKUPS, RULE_STATE, STATE, StampPipe, ruleWords } from '../shared/words';
import { AffairsList } from '../affairs/affairs-list';
import { Decisions } from '../decisions/decisions';
import { VocabularyArea } from './vocabulary';

type Area = 'review' | 'decisions' | 'runs' | 'rules' | 'vocabulary' | 'definition' | 'learnt' | 'process';

// The admin as in OpenParlData's panel: a drawer with the areas at the left, the area at the right. It has
// an account: where the server has a password for it, the screen is the form to sign in until someone has,
// and every decision is by that account. The
// review is here: the affairs with how many values are open, each leading to its review, and the log of the
// decisions taken; a visitor of the public pages decides nothing. Runs
// start here (a PDF, with its parliament where the person knows it) and are watched while they run; rules are seen here, a
// proposed one answered, an accepted one switched; the vocabulary is seen and changed in an area of its own
// (vocabulary.ts); the definition shows the fields with what each is and in how many documents it was asked.
@Component( {
    selector: 'app-admin',
    imports: [ FormsModule, RouterLink, MatButtonModule, MatCheckboxModule, MatFormFieldModule, MatInputModule,
        MatListModule, MatSelectModule, MatSlideToggleModule, Icon, StampPipe, VocabularyArea, AffairsList, Decisions ],
    templateUrl: './admin.html',
    styleUrl: './admin.scss',
} )
export class Admin implements OnInit, OnDestroy {
    private readonly api = inject( Api );
    readonly account = inject( Account );
    private readonly snack = inject( MatSnackBar );
    private timer: ReturnType<typeof setInterval> | null = null;

    readonly area = signal<Area>( 'review' );
    readonly health = signal<Health | null>( null );
    readonly runs = signal<Job[]>( [] );
    readonly rules = signal<Rule[]>( [] );
    readonly definition = signal<Definition | null>( null );
    readonly learnt = signal<Learnt | null>( null );
    readonly file = signal<File | null>( null );
    // the parliament of the PDF, where the person knows it; empty: read from the document
    readonly body = signal( '' );
    readonly parliaments = signal<{ key: string; name: string }[]>( [] );
    readonly withModel = signal( true );
    // the form to sign in, where the administration has an account
    readonly name = signal( '' );
    readonly password = signal( '' );
    readonly refused = signal( '' );
    readonly ready = signal( false );
    readonly busy = signal( false );
    readonly words = { STATE, LABELS, RULE_STATE, ENTITIES, LOOKUPS };
    readonly ruleWords = ruleWords;
    // the rules that wait for an answer first, then the accepted ones, last those that only count
    readonly ruleRows = computed( () => {
        const order = [ 'proposed', 'active', 'off', 'declined', 'contradicted', 'counting' ];
        return [ ...this.rules() ].sort( ( a, b ) => order.indexOf( a.state || 'counting' ) - order.indexOf( b.state || 'counting' ) );
    } );
    readonly areas: { id: Area; name: string; icon: string }[] = [
        { id: 'review', name: $localize`Prüfen`, icon: 'look' },
        { id: 'decisions', name: $localize`Entscheidungen`, icon: 'check' },
        { id: 'runs', name: $localize`Läufe`, icon: 'runs' },
        { id: 'rules', name: $localize`Regeln`, icon: 'rule' },
        { id: 'vocabulary', name: $localize`Vokabular`, icon: 'list' },
        { id: 'definition', name: $localize`Definition`, icon: 'fields' },
        { id: 'learnt', name: $localize`Zweite Meinung`, icon: 'rule' },
        { id: 'process', name: $localize`Verarbeiten`, icon: 'upload' },
    ];

    async ngOnInit(): Promise<void> {
        await this.account.load().catch( () => undefined );
        this.ready.set( true );
        if ( this.account.user() ) {
            await this.start();
        }
    }

    async signIn(): Promise<void> {
        this.refused.set( '' );
        this.busy.set( true );
        try {
            await this.account.signIn( this.name(), this.password() );
            this.password.set( '' );
            await this.start();
        } catch ( e ) {
            this.refused.set( ( e as { status?: number } ).status === 401 ? $localize`Name oder Passwort stimmt nicht.` : ( e as Error ).message );
        } finally {
            this.busy.set( false );
        }
    }

    // what the signed-in admin sees first, and the watch on the runs
    private async start(): Promise<void> {
        await this.refresh();
        // the parliaments to choose from at an upload, by name
        const known = await this.api.parliaments().catch( () => ( {} ) );
        this.parliaments.set( Object.entries( known ).map( ( [ key, p ] ) => ( { key, name: p.name + ', ' + p.parliament } ) )
            .sort( ( a, b ) => a.name.localeCompare( b.name ) ) );
        // a run takes a while; the list follows it without a reload
        this.timer ??= setInterval( () => {
            // a session that ended shows the form again instead of errors every four seconds
            if ( this.account.user() ) {
                this.refresh().catch( ( e ) => ( e as { status?: number } ).status === 401 && this.account.user.set( null ) );
            }
        }, 4000 );
    }

    ngOnDestroy(): void {
        if ( this.timer ) {
            clearInterval( this.timer );
        }
    }

    async refresh(): Promise<void> {
        this.health.set( await this.api.health() );
        this.runs.set( await this.api.runs() );
        this.rules.set( await this.api.rules() );
        // counted over every document of the store: only while it is looked at
        if ( this.area() === 'definition' ) {
            this.definition.set( await this.api.definition() );
        }
        if ( this.area() === 'learnt' ) {
            this.learnt.set( await this.api.learnt() );
        }
    }

    async show( area: Area ): Promise<void> {
        this.area.set( area );
        await this.refresh();
    }

    chose( event: Event ): void {
        const input = event.target as HTMLInputElement;
        this.file.set( input.files?.[ 0 ] || null );
    }

    async upload(): Promise<void> {
        const file = this.file();
        if ( !file ) {
            this.snack.open( $localize`Bitte ein PDF wählen.`, 'OK', { duration: 4000 } );
            return;
        }
        await this.guard( async () => {
            await this.api.upload( file, this.withModel(), this.body() );
            this.file.set( null );
            this.area.set( 'runs' );
        } );
    }

    // the documents read before a field existed are asked for it now; the run shows among the runs
    async askAgain( field: string ): Promise<void> {
        await this.guard( async () => {
            await this.api.askAgain( field );
            this.snack.open( $localize`Nachfragen gestartet – der Lauf steht unter „Läufe“.`, 'OK', { duration: 5000 } );
        } );
    }

    async answer( rule: Rule, accept: boolean ): Promise<void> {
        await this.guard( () => this.api.answerRule( rule.id, accept ) );
    }

    async toggle( rule: Rule, active: boolean ): Promise<void> {
        await this.guard( () => this.api.switchRule( rule.id, active ) );
    }

    lastLine( job: Job ): string {
        return job.lines[ job.lines.length - 1 ] || '';
    }

    private async guard( action: () => Promise<unknown> ): Promise<void> {
        this.busy.set( true );
        try {
            await action();
            await this.refresh();
        } catch ( e ) {
            this.snack.open( ( e as Error ).message, 'OK', { duration: 6000 } );
        } finally {
            this.busy.set( false );
        }
    }
}
