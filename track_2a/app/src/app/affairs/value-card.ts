import { Component, computed, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { DecisionBody, SourceEntry } from '../api/types';
import { DECISION, HOW, StampPipe, labelOf, leafOf } from '../shared/words';

// One value with its place: the field, how it was found, the block, the value, what the model answered,
// what a person decided, and the three decisions. Red while a person has to look and nobody did.
@Component( {
    selector: 'app-value-card',
    imports: [ FormsModule, RouterLink, MatButtonModule, MatFormFieldModule, MatInputModule, MatSelectModule, StampPipe ],
    templateUrl: './value-card.html',
    styleUrl: './value-card.scss',
} )
export class ValueCard {
    readonly entry = input.required<SourceEntry>();
    readonly docName = input( '' );
    readonly answer = input( '' );
    readonly focused = input( false );
    readonly decided = output<DecisionBody>();
    readonly jump = output<SourceEntry>();

    readonly after = signal( '' );
    readonly path = signal( '' );
    readonly words = { HOW, DECISION };

    readonly label = computed( () => labelOf( this.entry() ) );
    readonly values = computed( () => {
        const e = this.entry();
        const all = e.values || { [ e.path ]: e.value };
        return Object.entries( all ).map( ( [ p, v ] ) => ( { path: p, leaf: leafOf( p ), value: v } ) );
    } );
    readonly several = computed( () => this.values().length > 1 );
    readonly modelDiffers = computed( () => this.answer() !== '' && this.answer() !== String( this.entry().value ?? '' ) );

    // the input starts with the value as it stands, so a small correction is a few keys
    constructor() {
        queueMicrotask( () => {
            this.after.set( String( this.entry().value ?? '' ) );
            this.path.set( this.entry().path );
        } );
    }

    confirm(): void {
        this.decided.emit( { source: this.entry().source, decision: 'confirmed', by: '' } );
    }

    change(): void {
        this.decided.emit( { source: this.entry().source, decision: 'changed', by: '', after: this.after(), path: this.path() } );
    }

    reject(): void {
        this.decided.emit( { source: this.entry().source, decision: 'rejected', by: '' } );
    }

    pick( path: string ): void {
        this.path.set( path );
        const v = this.values().find( ( x ) => x.path === path );
        this.after.set( String( v?.value ?? '' ) );
    }
}
