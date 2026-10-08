import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Affair, AffairSummary, Decision, DecisionBody, FieldsReport, Health, Job, Rule } from './types';

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

    // the PDF goes as it is; the name and the model switch ride in headers, so no multipart is needed
    upload( file: File, model: boolean ): Promise<Job> {
        const headers = this.headers().set( 'Content-Type', 'application/pdf' )
            .set( 'X-Name', file.name ).set( 'X-Model', model ? '1' : '0' );
        return firstValueFrom( this.http.post<Job>( '/api/runs', file, { headers } ) ).catch( fail );
    }

    fetchDocument( id: number, model: boolean ): Promise<Job> {
        return this.post<Job>( 'runs', { document: id, model } );
    }

    rules(): Promise<Rule[]> {
        return this.get<Rule[]>( 'rules' );
    }

    switchRule( id: string, active: boolean, by: string ): Promise<Rule> {
        return this.post<Rule>( 'rules/' + encodeURIComponent( id ), { active, by } );
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
