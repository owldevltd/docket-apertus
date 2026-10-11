import { inject } from '@angular/core';
import { Router, Routes } from '@angular/router';
import { AffairView } from './affairs/affair-view';
import { Admin } from './admin/admin';
import { DocumentItem } from './public/document-item';
import { Element } from './public/element';
import { Home } from './public/home';
import { Item } from './public/item';
import { Account } from './shared/account';

// Two levels. What a visitor sees: the start with the search, an affair, a document, a person, a group, a
// meeting; nothing there changes anything. And the administration: the areas of the admin, among them the review of an affair, where values
// are confirmed, changed and rejected. The server hands every unknown path to the app, so deep links work.
// a screen of the administration other than its first: without the account it leads to the form to sign in
const signedIn = async () => {
    const account = inject( Account );
    const router = inject( Router );
    await account.load().catch( () => undefined );
    return account.user() ? true : router.parseUrl( '/admin' );
};

export const routes: Routes = [
    { path: '', component: Home, title: $localize`Docket · Geschäfte` },
    { path: 'affairs/:key', component: Item, title: $localize`Docket · Geschäft` },
    { path: 'documents/:name', component: DocumentItem, title: $localize`Docket · Dokument` },
    { path: 'persons/:name', component: Element, data: { kind: 'persons' }, title: $localize`Docket · Person` },
    { path: 'groups/:name', component: Element, data: { kind: 'groups' }, title: $localize`Docket · Gruppe` },
    { path: 'meetings/:name', component: Element, data: { kind: 'meetings' }, title: $localize`Docket · Sitzung` },
    { path: 'admin', component: Admin, title: $localize`Docket · Admin` },
    { path: 'admin/review/:key', component: AffairView, canActivate: [ signedIn ], title: $localize`Docket · Prüfen` },
    { path: '**', redirectTo: '' },
];
