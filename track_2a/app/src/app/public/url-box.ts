import { Component, input, model } from '@angular/core';
import { Icon } from '../shared/icon';

// The address of what is shown, to copy, with the switch between the page and its JSON: as on the pages of
// OpenParlData's public app. The count at the right says how many of how many are shown.
@Component( {
    selector: 'app-url-box',
    imports: [ Icon ],
    template: `
        <div class="url-box">
            <span class="label" i18n>URL:</span>
            <input type="text" readonly [value]="address()" (focus)="$any( $event.target ).select()">
            <button type="button" class="copy" (click)="copy()" title="Adresse kopieren" i18n-title><app-icon name="copy" /></button>
            <div class="side">
                @if ( count() ) { <span class="count">{{ count() }}</span> }
                <div class="switch">
                    <button type="button" [class.on]="!json()" (click)="json.set( false )" i18n>HTML</button>
                    <button type="button" [class.on]="json()" (click)="json.set( true )" i18n>JSON</button>
                </div>
            </div>
        </div>`,
    styleUrl: './url-box.scss',
} )
export class UrlBox {
    readonly address = input.required<string>();
    readonly count = input( '' );
    readonly json = model( false );

    copy(): void {
        navigator.clipboard?.writeText( this.address() );
    }
}
