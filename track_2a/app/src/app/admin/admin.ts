import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Api } from '../api/api';
import { Health, Job, Rule } from '../api/types';
import { Icon } from '../shared/icon';
import { Who } from '../shared/who';
import { KINDS, LABELS, STATE, StampPipe } from '../shared/words';
import { VocabularyArea } from './vocabulary';

type Area = 'runs' | 'rules' | 'vocabulary' | 'process';

// The admin as in OpenParlData's panel: a drawer with the areas at the left, the area at the right. Runs
// start here (a PDF, or a document of theirs by id) and are watched while they run; rules are seen and
// switched here; the vocabulary is seen and changed in an area of its own (vocabulary.ts).
@Component( {
    selector: 'app-admin',
    imports: [ FormsModule, RouterLink, MatButtonModule, MatCheckboxModule, MatFormFieldModule, MatInputModule,
        MatListModule, MatSlideToggleModule, Icon, StampPipe, VocabularyArea ],
    templateUrl: './admin.html',
    styleUrl: './admin.scss',
} )
export class Admin implements OnInit, OnDestroy {
    private readonly api = inject( Api );
    private readonly who = inject( Who );
    private readonly snack = inject( MatSnackBar );
    private timer: ReturnType<typeof setInterval> | null = null;

    readonly area = signal<Area>( 'runs' );
    readonly health = signal<Health | null>( null );
    readonly runs = signal<Job[]>( [] );
    readonly rules = signal<Rule[]>( [] );
    readonly file = signal<File | null>( null );
    readonly docId = signal<number | null>( null );
    readonly withModel = signal( true );
    readonly token = signal( localStorage.getItem( 'docket.token' ) || '' );
    readonly busy = signal( false );
    readonly words = { STATE, KINDS, LABELS };
    readonly areas: { id: Area; name: string; icon: string }[] = [
        { id: 'runs', name: 'Läufe', icon: 'runs' },
        { id: 'rules', name: 'Regeln', icon: 'rule' },
        { id: 'vocabulary', name: 'Vokabular', icon: 'list' },
        { id: 'process', name: 'Verarbeiten', icon: 'upload' },
    ];

    async ngOnInit(): Promise<void> {
        await this.refresh();
        // a run takes a while; the list follows it without a reload
        this.timer = setInterval( () => { this.refresh().catch( () => undefined ); }, 4000 );
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
    }

    saveToken( value: string ): void {
        this.token.set( value.trim() );
        localStorage.setItem( 'docket.token', value.trim() );
    }

    chose( event: Event ): void {
        const input = event.target as HTMLInputElement;
        this.file.set( input.files?.[ 0 ] || null );
    }

    async upload(): Promise<void> {
        const file = this.file();
        if ( !file ) {
            this.snack.open( 'Bitte ein PDF wählen.', 'OK', { duration: 4000 } );
            return;
        }
        await this.guard( async () => {
            await this.api.upload( file, this.withModel() );
            this.file.set( null );
            this.area.set( 'runs' );
        } );
    }

    async fetch(): Promise<void> {
        const id = this.docId();
        if ( !id ) {
            this.snack.open( 'Bitte eine Kennung eingeben.', 'OK', { duration: 4000 } );
            return;
        }
        await this.guard( async () => {
            await this.api.fetchDocument( id, this.withModel() );
            this.docId.set( null );
            this.area.set( 'runs' );
        } );
    }

    async toggle( rule: Rule, active: boolean ): Promise<void> {
        const by = this.who.require();
        await this.guard( () => this.api.switchRule( rule.id, active, by ) );
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
