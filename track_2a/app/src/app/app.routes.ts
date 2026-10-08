import { Routes } from '@angular/router';
import { AffairsList } from './affairs/affairs-list';
import { AffairView } from './affairs/affair-view';
import { Decisions } from './decisions/decisions';
import { Admin } from './admin/admin';

// The four screens. The server hands every unknown path to the app, so deep links work.
export const routes: Routes = [
    { path: '', component: AffairsList, title: 'Docket · Geschäfte' },
    { path: 'affairs/:key', component: AffairView, title: 'Docket · Geschäft' },
    { path: 'decisions', component: Decisions, title: 'Docket · Entscheidungen' },
    { path: 'admin', component: Admin, title: 'Docket · Admin' },
    { path: '**', redirectTo: '' },
];
