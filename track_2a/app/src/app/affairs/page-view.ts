import { Component, computed, input, model, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { Block, SourceEntry } from '../api/types';
import { Icon } from '../shared/icon';
import { textOf } from '../shared/words';

// A document's page with its blocks drawn over the image: every block framed in the colour of its kind
// with its id beside it, filled green where a value was found by code and red where a person has to look,
// a thick red frame where the reading itself asks for a check. The overlay scales with the image.
@Component( {
    selector: 'app-page-view',
    imports: [ MatButtonModule, Icon ],
    templateUrl: './page-view.html',
    styleUrl: './page-view.scss',
} )
export class PageView {
    readonly name = input.required<string>();
    readonly pages = input.required<number>();
    readonly blocks = input.required<Block[]>();
    readonly sources = input.required<SourceEntry[]>();
    readonly image = input.required<( n: number ) => string>();
    readonly page = model( 1 );
    readonly focus = model<string | null>( null );
    readonly size = signal( { width: 0, height: 0 } );

    readonly onPage = computed( () => this.blocks().filter( ( b ) => b.page === this.page() ) );
    readonly focused = computed( () => this.blocks().find( ( b ) => b.id === this.focus() ) );
    readonly focusedText = computed( () => textOf( this.focused() ) );

    // per block: open (red) wins over found (green)
    readonly marks = computed( () => {
        const out: Record<string, 'look' | 'hit'> = {};
        for ( const s of this.sources() ) {
            if ( s.block ) {
                out[ s.block ] = s.open || out[ s.block ] === 'look' ? 'look' : 'hit';
            }
        }
        return out;
    } );

    loaded( event: Event ): void {
        const img = event.target as HTMLImageElement;
        this.size.set( { width: img.naturalWidth, height: img.naturalHeight } );
    }

    turn( step: number ): void {
        this.page.set( Math.min( this.pages(), Math.max( 1, this.page() + step ) ) );
    }

    classOf( b: Block ): string {
        return [ b.type, b.approve ? 'flag' : '', this.marks()[ b.id ] || '', this.focus() === b.id ? 'focus' : '' ]
            .filter( Boolean ).join( ' ' );
    }

    labelX( b: Block ): number {
        return Math.max( 4, b.x - 110 );
    }
}
