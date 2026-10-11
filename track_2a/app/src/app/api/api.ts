import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Affair, AffairSummary, Decision, DecisionBody, Definition, DocumentView, FieldsReport, Health, Job, Learnt, Parliament, Rule, VocabularyRow } from './types';

// The one door to the server. Every call goes through here, so the admin token and the error text are in
// one place; the server's error message is what the user gets to see.
@Injectable( { providedIn: 'root' } )
export class Api {
    private readonly http = inject( HttpClient );

    affairs(): Promise<AffairSummary[]> {
        return this.get<AffairSummary[]>( 'affairs' );
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
        let headers = this.headers().set( 'Content-Type', 'application/pdf' )
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
    answerRule( id: string, accept: boolean, by: string ): Promise<Rule> {
        return this.post<Rule>( 'rules/' + encodeURIComponent( id ) + '/answer', { accept, by } );
    }

    switchRule( id: string, active: boolean, by: string ): Promise<Rule> {
        return this.post<Rule>( 'rules/' + encodeURIComponent( id ), { active, by } );
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
    setName( row: { list: string; body: string; name: string }, standard: string | null, by: string ): Promise<VocabularyRow> {
        return this.post<VocabularyRow>( 'vocabulary', { list: row.list, body: row.body, name: row.name, standard, by } );
    }

    resetName( row: { list: string; body: string; name: string } ): Promise<VocabularyRow> {
        return this.post<VocabularyRow>( 'vocabulary', { list: row.list, body: row.body, name: row.name, reset: true } );
    }

    private get<T>( route: string ): Promise<T> {
        return firstValueFrom( this.http.get<T>( '/api/' + route, { headers: this.headers() } ) ).catch( fail );
    }

    private post<T>( route: string, body: unknown ): Promise<T> {
        return firstValueFrom( this.http.post<T>( '/api/' + route, body, { headers: this.headers() } ) ).catch( fail );
    }

    private headers(): HttpHeaders {
        const token = localStorage.getItem( 'docket.token' );
        return token ? new HttpHeaders( { 'X-Token': token } ) : new HttpHeaders();
    }
}

function fail( error: any ): never {
    const text = error?.error?.error || error?.message || 'Der Server antwortet nicht.';
    throw new Error( text );
}
