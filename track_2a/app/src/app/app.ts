import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { Who } from './shared/who';

// The frame: the dark top bar with the wordmark and the three areas, the reviewer's name at the right,
// the screens below. The bar follows the one of OpenParlData's public app.
@Component( {
    selector: 'app-root',
    imports: [ RouterOutlet, RouterLink, RouterLinkActive, MatToolbarModule, MatButtonModule ],
    templateUrl: './app.html',
    styleUrl: './app.scss',
} )
export class App {
    readonly who = inject( Who );

    rename(): void {
        this.who.set( prompt( 'Kürzel für Entscheidungen', this.who.name() ) ?? this.who.name() );
    }
}
