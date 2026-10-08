import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { Api } from '../api/api';
import { AffairSummary } from '../api/types';
import { Icon } from '../shared/icon';

// The affairs as result cards, the ones with open marks first; a switch keeps only those.
@Component( {
    selector: 'app-affairs-list',
    imports: [ RouterLink, MatCheckboxModule, Icon ],
    templateUrl: './affairs-list.html',
    styleUrl: './affairs-list.scss',
} )
export class AffairsList implements OnInit {
    private readonly api = inject( Api );
    readonly affairs = signal<AffairSummary[]>( [] );
    readonly onlyOpen = signal( localStorage.getItem( 'docket.onlyOpen' ) === '1' );
    readonly error = signal( '' );
    readonly shown = computed( () => this.affairs().filter( ( a ) => !this.onlyOpen() || a.counts.open > 0 ) );

    async ngOnInit(): Promise<void> {
        try {
            this.affairs.set( await this.api.affairs() );
        } catch ( e ) {
            this.error.set( ( e as Error ).message );
        }
    }

    toggle( value: boolean ): void {
        this.onlyOpen.set( value );
        localStorage.setItem( 'docket.onlyOpen', value ? '1' : '0' );
    }
}
