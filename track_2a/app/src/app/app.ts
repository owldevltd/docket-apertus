import { Component, LOCALE_ID, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { Account } from './shared/account';

// The frame: the dark top bar with the wordmark and the way back to the affairs; the screens below. The
// administration is not linked from what a visitor sees, it stands under /admin; within it the name of the
// account that is signed in stands at the right, with the way out. The bar follows the one of OpenParlData's
// public app. The app is built once per language, each build under its own
// folder, so the switch at the right is a link to the same screen under the other folder.
@Component( {
    selector: 'app-root',
    imports: [ RouterOutlet, RouterLink, RouterLinkActive, MatToolbarModule, MatButtonModule ],
    templateUrl: './app.html',
    styleUrl: './app.scss',
} )
export class App {
    readonly account = inject( Account );
    private readonly router = inject( Router );
    readonly inAdmin = signal( false );
    readonly languages = [ 'de', 'fr', 'it', 'en' ];
    readonly here = inject( LOCALE_ID ).slice( 0, 2 );
    readonly path = signal( '/' );

    constructor() {
        this.router.events.subscribe( ( e ) => {
            if ( e instanceof NavigationEnd ) {
                this.inAdmin.set( e.urlAfterRedirects.startsWith( '/admin' ) );
                this.path.set( e.urlAfterRedirects );
            }
        } );
    }

    async signOut(): Promise<void> {
        await this.account.signOut().catch( () => undefined );
        await this.router.navigateByUrl( '/admin' );
    }
}
