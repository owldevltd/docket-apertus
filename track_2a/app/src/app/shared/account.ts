import { Injectable, inject, signal } from '@angular/core';
import { Api } from '../api/api';

// The account of the administration. The server says whether it has one (a password is set) and who is
// signed in; a session rides in a cookie the page cannot read, so nothing of it is kept here. Without an
// account the administration is open and everyone acts under its name. What a visitor reads never asks.
@Injectable( { providedIn: 'root' } )
export class Account {
    private readonly api = inject( Api );
    // whether the administration has a password, and the name signed in (null: nobody)
    readonly needed = signal( false );
    readonly user = signal<string | null>( null );
    private asked: Promise<void> | null = null;

    // asks the server once; every screen of the administration waits for the answer
    load(): Promise<void> {
        this.asked ??= this.api.session().then( ( s ) => {
            this.needed.set( s.account );
            this.user.set( s.user );
        } );
        return this.asked;
    }

    async signIn( user: string, password: string ): Promise<void> {
        const s = await this.api.login( user, password );
        this.needed.set( s.account );
        this.user.set( s.user );
    }

    async signOut(): Promise<void> {
        const s = await this.api.logout();
        this.needed.set( s.account );
        this.user.set( s.user );
    }
}
