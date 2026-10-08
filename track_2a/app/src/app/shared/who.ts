import { Injectable, signal } from '@angular/core';

// Who decides: a short name the reviewer enters once; it goes with every decision as "by". Kept in the
// browser only, since the app has no accounts (the admin token is a separate thing).
@Injectable( { providedIn: 'root' } )
export class Who {
    readonly name = signal( localStorage.getItem( 'docket.by' ) || '' );

    set( name: string ): void {
        const clean = name.trim();
        this.name.set( clean );
        if ( clean ) {
            localStorage.setItem( 'docket.by', clean );
        } else {
            localStorage.removeItem( 'docket.by' );
        }
    }

    // a decision needs a name; without one the reviewer is asked first
    require(): string {
        if ( !this.name() ) {
            this.set( prompt( 'Kürzel für Entscheidungen' ) || '' );
        }
        return this.name();
    }
}
