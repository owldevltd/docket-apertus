import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import {
    Affair, AffairSummary, Decision, DecisionBody, Definition, DocumentView, FieldsReport, Health, Job, Learnt, Listed,
    Parliament, Rec, Rule, Session, Standard, VocabularyRow,
} from './types';

// The query string of a search, for a call and for the address a visitor can copy.
export function queryOf( asked: Record<string, string> ): string {
    const parts = Object.entries( asked ).filter( ( [ , v ] ) => v !== '' )
        .map( ( [ k, v ] ) => encodeURIComponent( k ) + '=' + encodeURIComponent( v ) );
    return parts.length ? '?' + parts.join( '&' ) : '';
}

// The one door to the server. Every call goes through here, so the error text is in
// one place; the server's error message is what the user gets to see.
@Injectable( { providedIn: 'root' } )
export class Api {
    private readonly http = inject( HttpClient );

    // what a visitor reads: the affairs in the affair schema, narrowed by q, body_key, type, kind, language
    records( asked: Record<string, string> = {} ): Promise<Listed> {
        return this.get<Listed>( 'records' + queryOf( asked ) );
    }

    // one affair in the affair schema, whole
    record( id: string ): Promise<Rec> {
        return this.get<Rec>( 'records/' + encodeURIComponent( id ) );
    }

    // one of the tables that follow from the affairs: contributors, groups, meetings, events
    table( name: string, asked: Record<string, string> = {} ): Promise<Listed> {
        return this.get<Listed>( name + queryOf( asked ) );
    }

    // the review's list: the affairs with how many values are open, narrowed by q, body, type, kind, language
    affairs( asked: Record<string, string> = {} ): Promise<AffairSummary[]> {
        return this.get<AffairSummary[]>( 'affairs' + queryOf( asked ) );
    }

    affair( key: string ): Promise<Affair> {
        return this.get<Affair>( 'affairs/' + encodeURIComponent( key ) );
    }

    decisions( key?: string ): Promise<Decision[]> {
        return this.get<Decision[]>( key ? 'affairs/' + encodeURIComponent( key ) + '/decisions' : 'decisions' );
    }

    decide( key: string, body: DecisionBody ): Promise<Affair> {
        return this.post<Affair>( 'affairs/' + encodeURIComponent( key ) + '/decisions', body );
    }

    document( name: string ): Promise<DocumentView | null> {
        return this.get<DocumentView>( 'documents/' + encodeURIComponent( name ) + '/blocks' ).catch( () => null );
    }

    fields( name: string ): Promise<FieldsReport | null> {
        return this.get<FieldsReport>( 'documents/' + encodeURIComponent( name ) + '/fields' ).catch( () => null );
    }

    pageImage( name: string, n: number ): string {
        return '/api/documents/' + encodeURIComponent( name ) + '/pages/' + n + '.png';
    }

    health(): Promise<Health> {
        return this.get<Health>( 'health' );
    }

    runs(): Promise<Job[]> {
        return this.get<Job[]>( 'runs' );
    }

    run( id: string ): Promise<Job> {
        return this.get<Job>( 'runs/' + encodeURIComponent( id ) );
    }

    // the PDF goes as it is; the name, the model switch and the parliament ride in headers, so no multipart
    // is needed
    upload( file: File, model: boolean, body: string ): Promise<Job> {
        let headers = new HttpHeaders().set( 'Content-Type', 'application/pdf' )
            .set( 'X-Name', file.name ).set( 'X-Model', model ? '1' : '0' );
        if ( body ) {
            headers = headers.set( 'X-Body', body );
        }
        return firstValueFrom( this.http.post<Job>( '/api/runs', file, { headers } ) ).catch( fail );
    }

    rules(): Promise<Rule[]> {
        return this.get<Rule[]>( 'rules' );
    }

    // a person's yes or no to a proposed rule; yes applies it to every value that fits
    answerRule( id: string, accept: boolean ): Promise<Rule> {
        return this.post<Rule>( 'rules/' + encodeURIComponent( id ) + '/answer', { accept } );
    }

    switchRule( id: string, active: boolean ): Promise<Rule> {
        return this.post<Rule>( 'rules/' + encodeURIComponent( id ), { active } );
    }

    definition(): Promise<Definition> {
        return this.get<Definition>( 'definition' );
    }

    // queues a run that asks the stored documents a field they were never asked
    askAgain( field: string ): Promise<Job> {
        return this.post<Job>( 'definition/ask', { field } );
    }

    learnt(): Promise<Learnt> {
        return this.get<Learnt>( 'learnt' );
    }

    vocabulary(): Promise<VocabularyRow[]> {
        return this.get<VocabularyRow[]>( 'vocabulary' );
    }

    parliaments(): Promise<Record<string, Parliament>> {
        return this.get<Record<string, Parliament>>( 'parliaments' );
    }

    // standard is one of the list's standard names, or null for a name that stands for none
    setName( row: { list: string; body: string; name: string }, standard: string | null ): Promise<VocabularyRow> {
        return this.post<VocabularyRow>( 'vocabulary', { list: row.list, body: row.body, name: row.name, standard } );
    }

    // a standard name of the administration's own, with its wording in the four languages
    addStandard( list: string, standard: Standard ): Promise<VocabularyRow> {
        return this.post<VocabularyRow>( 'vocabulary', { list, standard } );
    }

    resetName( row: { list: string; body: string; name: string } ): Promise<VocabularyRow> {
        return this.post<VocabularyRow>( 'vocabulary', { list: row.list, body: row.body, name: row.name, reset: true } );
    }

    // the account of the administration: whether there is one and who is signed in, signing in and out. The
    // session itself is the server's, in a cookie the page cannot read
    session(): Promise<Session> {
        return this.get<Session>( 'session' );
    }

    login( user: string, password: string ): Promise<Session> {
        return this.post<Session>( 'login', { user, password } );
    }

    logout(): Promise<Session> {
        return this.post<Session>( 'logout', {} );
    }

    private get<T>( route: string ): Promise<T> {
        return firstValueFrom( this.http.get<T>( '/api/' + route ) ).catch( fail );
    }

    private post<T>( route: string, body: unknown ): Promise<T> {
        return firstValueFrom( this.http.post<T>( '/api/' + route, body ) ).catch( fail );
    }
}

function fail( error: any ): never {
    const text = error?.error?.error || error?.message || $localize`Der Server antwortet nicht.`;
    // the status goes with it, so a screen can say in its own words that something is not there
    throw Object.assign( new Error( text ), { status: Number( error?.status ?? 0 ) } );
}
