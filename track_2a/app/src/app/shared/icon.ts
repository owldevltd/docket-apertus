import { Component, input } from '@angular/core';

// A handful of icons as inline SVG paths, so no icon font is loaded from anywhere (the app serves itself).
const PATHS: Record<string, string> = {
    affair: 'M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM3 11h18',
    zoom: 'M10 4a6 6 0 1 1 0 12 6 6 0 0 1 0-12zm4.5 10.5L20 20M8 10h4M10 8v4',
    back: 'M15 6l-6 6 6 6',
    next: 'M9 6l6 6-6 6',
    check: 'M5 12l4 4L19 7',
    close: 'M6 6l12 12M18 6L6 18',
    upload: 'M12 16V4m0 0l-4 4m4-4l4 4M4 20h16',
    cloud: 'M7 18a4 4 0 0 1-.5-7.97A6 6 0 0 1 18 8a4.5 4.5 0 0 1 .5 9z',
    rule: 'M4 6h16M4 12h10M4 18h6',
    runs: 'M4 6h16M4 12h16M4 18h16',
    look: 'M12 5c5 0 9 4 10 7-1 3-5 7-10 7S3 15 2 12c1-3 5-7 10-7zm0 4a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
    document: 'M7 3h7l5 5v13H7zM14 3v5h5M9 13h6M9 17h6',
    person: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9c1-4 4-6 7-6s6 2 7 6',
    list: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01',
    fields: 'M4 5h7v6H4zM13 5h7v6h-7zM4 13h7v6H4zM13 13h7v6h-7z',
    menu: 'M4 7h16M4 12h16M4 17h16',
    search: 'M10.5 4a6.5 6.5 0 1 1 0 13 6.5 6.5 0 0 1 0-13zm5 11.5L20 20',
    copy: 'M9 9h10v11H9zM5 15V4h10',
    tune: 'M4 7h9m4 0h3M4 17h3m4 0h9M15 5v4M9 15v4',
};

@Component( {
    selector: 'app-icon',
    template: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        + 'stroke-linejoin="round" [attr.width]="size()" [attr.height]="size()"><path [attr.d]="path()"/></svg>',
    styles: ':host { display: inline-flex; vertical-align: middle; line-height: 0; }',
} )
export class Icon {
    readonly name = input.required<string>();
    readonly size = input( 20 );

    path(): string {
        return PATHS[ this.name() ] || '';
    }
}
