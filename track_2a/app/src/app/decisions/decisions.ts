import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Api } from '../api/api';
import { Decision } from '../api/types';
import { DECISION, LABELS, StampPipe } from '../shared/words';

// Every decision anyone took, newest first; a row leads to its affair.
@Component( {
    selector: 'app-decisions',
    imports: [ StampPipe ],
    templateUrl: './decisions.html',
} )
export class Decisions implements OnInit {
    private readonly api = inject( Api );
    private readonly router = inject( Router );
    readonly rows = signal<Decision[]>( [] );
    readonly error = signal( '' );
    readonly words = { DECISION, LABELS };

    async ngOnInit(): Promise<void> {
        try {
            const rows = await this.api.decisions();
            this.rows.set( rows.sort( ( a, b ) => ( b.at || '' ).localeCompare( a.at || '' ) ) );
        } catch ( e ) {
            this.error.set( ( e as Error ).message );
        }
    }

    open( row: Decision ): void {
        this.router.navigate( [ '/admin/review', row.affair ] );
    }
}
