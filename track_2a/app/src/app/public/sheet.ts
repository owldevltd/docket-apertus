import { Component, computed, input } from '@angular/core';
import { Rec } from '../api/types';

// the box the positions of a record are measured in: a page upright at 300 dots per inch, A4 where no block
// lies outside it. The record holds no paper size, so a wider or longer page shows by its blocks alone.
const SHEET = { width: 2481, height: 3508 };
// a point of a font size, in the dots of the positions
const POINT = 300 / 72;
// the line of a text against its font size, to tell how many lines a box holds
const LEADING = 1.2;

interface Piece {
    id: string;
    kind: string;
    lines: string[];
    pairs: { term: string; def: string }[];
    cells: string[][];
    box: Record<string, string>;
    light: boolean;
    tip: string;
}

// One page of a document, set from the blocks of its record and from nothing else: every block with its text
// at its place, in its size, weight and colour, as the affair schema holds them (x, y, width, height at 300
// dpi, font, font-size in points, color). No image of the page is used; a picture or a line of the page is a
// grey box, since the record keeps its place and not the picture. Pointing at a block shows what the record
// says about it. A record without positions is set as running text.
@Component( {
    selector: 'app-sheet',
    template: `
        @if ( placed() ) {
            <div class="page" [style.aspect-ratio]="size().width + ' / ' + size().height">
                @for ( p of pieces(); track p.id ) {
                    <div class="piece" [class.graphic]="p.kind === 'graphic'" [class.light]="p.light" [style]="p.box" [title]="p.tip">
                        @for ( line of p.lines; track $index ) { <div>{{ line }}</div> }
                        @for ( pair of p.pairs; track $index ) { <div class="pair"><span>{{ pair.term }}</span><span>{{ pair.def }}</span></div> }
                        @for ( row of p.cells; track $index ) { <div class="cells">@for ( cell of row; track $index ) { <span>{{ cell }}</span> }</div> }
                    </div>
                }
            </div>
        } @else {
            <div class="flow">
                @for ( p of pieces(); track p.id ) {
                    <div class="run" [class.head]="p.kind === 'sec'" [title]="p.tip">
                        @for ( line of p.lines; track $index ) { <div>{{ line }}</div> }
                        @for ( pair of p.pairs; track $index ) { <div class="pair"><span>{{ pair.term }}</span><span>{{ pair.def }}</span></div> }
                        @for ( row of p.cells; track $index ) { <div class="cells">@for ( cell of row; track $index ) { <span>{{ cell }}</span> }</div> }
                    </div>
                }
            </div>
        }`,
    styleUrl: './sheet.scss',
} )
export class Sheet {
    // the blocks of the document, the content of a section beside it, and the page to show
    readonly blocks = input.required<Rec[]>();
    readonly page = input( 1 );

    readonly placed = computed( () => this.blocks().some( ( b ) => typeof b[ 'x' ] === 'number' ) );
    // one box for all pages of the document, so a turn of the page does not change the scale
    readonly size = computed( () => {
        let width = SHEET.width;
        let height = SHEET.height;
        for ( const b of this.blocks() ) {
            if ( typeof b[ 'x' ] === 'number' ) {
                width = Math.max( width, b[ 'x' ] + ( b[ 'width' ] || 0 ) + Math.min( b[ 'x' ], 120 ) );
                height = Math.max( height, b[ 'y' ] + ( b[ 'height' ] || 0 ) + Math.min( b[ 'y' ], 120 ) );
            }
        }
        return { width, height };
    } );
    readonly pieces = computed<Piece[]>( () => this.blocks()
        .filter( ( b ) => ( b[ 'page' ] || 1 ) === this.page() )
        .map( ( b, at ) => this.piece( b, at ) ) );

    private piece( b: Rec, at: number ): Piece {
        const items: unknown[] = b[ 'items' ] || [];
        const lines = b[ 'type' ] === 'sec' ? [ String( b[ 'title' ] || '' ) ]
            : b[ 'text' ] ? [ String( b[ 'text' ] ) ]
                : items.filter( ( i ) => typeof i === 'string' ).map( String );
        const pairs = items.filter( ( i ) => i && typeof i === 'object' )
            .map( ( i ) => ( { term: String( ( i as Rec )[ 'term' ] || '' ), def: String( ( i as Rec )[ 'def' ] || '' ) } ) );
        const cells: string[][] = ( b[ 'rows' ] || [] ).map( ( row: unknown[] ) => row.map( ( c ) => String( c ?? '' ) ) );
        const font = String( b[ 'font' ] || '' );
        const size = Number( b[ 'font-size' ] || 0 );
        const { width, height } = this.size();
        // the size of the font in dots; a block without one is set as high as a line of its box
        const dots = size ? size * POINT : Math.min( Number( b[ 'height' ] || 40 ), 44 );
        const rows = Math.max( lines.length, pairs.length, cells.length, 1 );
        const held = Math.max( rows, Math.round( Number( b[ 'height' ] || 0 ) / ( dots * LEADING ) ) );
        const box: Record<string, string> = {};
        if ( typeof b[ 'x' ] === 'number' ) {
            box[ 'left' ] = share( b[ 'x' ], width );
            box[ 'top' ] = share( b[ 'y' ], height );
            box[ 'width' ] = share( b[ 'width' ], width );
            box[ 'min-height' ] = share( b[ 'height' ], height );
            box[ 'font-size' ] = wide( dots, width );
            box[ 'line-height' ] = wide( Math.max( Number( b[ 'height' ] || 0 ) / held, dots * 0.9 ), width );
            // a single line keeps to its line, whatever the font of the screen makes of its width
            box[ 'white-space' ] = held === 1 ? 'nowrap' : 'normal';
        }
        if ( /fett|bold|black|heavy/i.test( font ) ) {
            box[ 'font-weight' ] = '700';
        }
        if ( /kursiv|italic|oblique/i.test( font ) ) {
            box[ 'font-style' ] = 'italic';
        }
        box[ 'font-family' ] = familyOf( font );
        if ( b[ 'color' ] && b[ 'type' ] !== 'graphic' ) {
            box[ 'color' ] = String( b[ 'color' ] );
        }
        const tip = [
            b[ 'id' ], b[ 'type' ],
            typeof b[ 'x' ] === 'number' ? 'x ' + b[ 'x' ] + ', y ' + b[ 'y' ] : '',
            typeof b[ 'width' ] === 'number' ? b[ 'width' ] + ' × ' + b[ 'height' ] : '',
            font, size ? size + ' pt' : '', b[ 'color' ] || '', b[ 'isOCR' ] ? 'OCR' : '',
        ].filter( Boolean ).join( ' · ' );
        return { id: String( b[ 'id' ] || '' ) + '.' + at, kind: String( b[ 'type' ] || '' ), lines, pairs, cells, box, light: lightOf( b[ 'color' ] ), tip };
    }
}

// a length as a share of the page, for a place on it
function share( value: number, of: number ): string {
    return ( ( value || 0 ) / of * 100 ).toFixed( 3 ) + '%';
}

// a length in hundredths of the width the page is shown at, so text grows and shrinks with the page
function wide( value: number, of: number ): string {
    return ( value / of * 100 ).toFixed( 3 ) + 'cqw';
}

// the family of a font as the PDF names it ("Verdana fett", "TimesNewRomanPSMT"): the name itself first, then
// a font of its kind that every screen has
function familyOf( font: string ): string {
    const name = font.replace( /fett|kursiv|bold|italic|oblique|regular|black|heavy/gi, '' ).replace( /(PS)?MT$/, '' ).replace( /[-,]+$/, '' ).trim();
    const kind = /courier|mono|consol/i.test( font ) ? '"Courier New", monospace'
        : /times|serif|garamond|georgia|cambria|minion|palatino|book/i.test( font ) && !/sans/i.test( font ) ? '"Times New Roman", Times, serif'
            : 'Arial, Helvetica, sans-serif';
    return name ? '"' + name.replace( /"/g, '' ) + '", ' + kind : kind;
}

// whether a colour is too light to read on the white of the page (white letters of a dark field)
function lightOf( color: unknown ): boolean {
    const m = /^#?([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i.exec( String( color || '' ) );
    if ( !m ) {
        return false;
    }
    const [ r, g, b ] = [ m[ 1 ], m[ 2 ], m[ 3 ] ].map( ( x ) => parseInt( x, 16 ) / 255 );
    return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.8;
}
