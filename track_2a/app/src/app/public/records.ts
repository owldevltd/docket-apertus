import { Router } from '@angular/router';
import { Rec } from '../api/types';

// Reading an affair in the affair schema: the few ways the public pages take what they show out of a record.
// Nothing here knows more than the record says.

// where the screens of this build stand: the address of the server with the folder of the language
export const SCREENS = document.baseURI.replace( /\/$/, '' );

// the address of one screen, written as the router writes it into a link: a name with round brackets or a
// slash in it comes out encoded the way the router reads it back
export function screenAt( router: Router, parts: string[] ): string {
    return SCREENS + router.serializeUrl( router.createUrlTree( parts ) );
}

// the language of this build of the app, as its page says it
const HERE = ( document.documentElement.lang || 'de' ).slice( 0, 2 );

// the text of a value the schema holds per language: in the language of the page where the record has it (a
// standard name comes in all four), else the first there is (what a document prints, in its own language)
export function textIn( value: unknown ): string {
    if ( value && typeof value === 'object' ) {
        const held = value as Record<string, unknown>;
        const first = held[ HERE ] ?? Object.values( held ).find( ( v ) => v !== null && v !== '' );
        return first === undefined || first === null ? '' : String( first );
    }
    return value === null || value === undefined ? '' : String( value );
}

export function titleOf( record: Rec ): string {
    return textIn( record[ 'title' ] ) || String( record[ 'id' ] || '' );
}

// the type under its standard name where the record has one, else as the document names it
export function typeOf( record: Rec ): string {
    return textIn( record[ 'type_harmonized' ] ) || textIn( record[ 'type_name' ] );
}

export function docsOf( record: Rec ): Rec[] {
    return record[ 'docs' ]?.data || [];
}

export function peopleOf( record: Rec ): Rec[] {
    return record[ 'contributors' ]?.data || [];
}

export function eventsOf( record: Rec ): Rec[] {
    return record[ 'events' ]?.data || [];
}

// a name as part of an address, and back
export function slug( name: string ): string {
    return encodeURIComponent( name );
}
