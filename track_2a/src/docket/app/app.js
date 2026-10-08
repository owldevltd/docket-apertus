// The review app: the list of affairs, one affair with its page images and every value with a place, and
// the three decisions. Plain browser JavaScript, no build step; the server answers under /api/.

const screens = { list: byId("list"), affair: byId("affair"), decisions: byId("decisions") };
const state = { affairs: [], affair: null, doc: 0, page: 1, focus: null, fields: {} };

const LABELS = {
    "number": "Nummer", "title": "Titel", "type_name": "Art", "begin_date": "Datum", "kwd-group": "Schlagwort",
    "abstract": "Zusammenfassung", "article-version": "Fassung", "contributors": "Beteiligte", "events": "Ereignis",
    "conference": "Sitzung", "related-article": "Verwandtes Geschäft", "related-object": "Verweis",
};
const HOW = { literal: "wörtlich", derived: "abgeleitet", cited: "vom Modell genannt", composed: "vom Modell formuliert" };
const DECISION = { confirmed: "bestätigt", changed: "geändert", rejected: "verworfen" };

function byId(id) { return document.getElementById(id); }

const SVG = "http://www.w3.org/2000/svg";

function el(tag, attrs = {}, ...children) {
    const node = tag === "rect" || tag === "text" ? document.createElementNS(SVG, tag) : document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
        if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
        else node.setAttribute(k, v);
    }
    for (const c of children) node.append(c instanceof Node ? c : document.createTextNode(String(c ?? "")));
    return node;
}

async function api(route, body) {
    const r = await fetch("/api/" + route, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || r.statusText);
    return data;
}

function who() {
    let by = localStorage.getItem("docket.by") || "";
    if (!by) {
        by = (prompt("Kürzel für Entscheidungen", "") || "").trim();
        if (by) localStorage.setItem("docket.by", by);
    }
    byId("who").textContent = by ? "als " + by : "Kürzel setzen";
    return by;
}

function show(name) {
    for (const [k, s] of Object.entries(screens)) s.classList.toggle("active", k === name);
    for (const a of document.querySelectorAll(".tabs a")) a.classList.toggle("active", a.dataset.tab === name);
}

// ---- list

async function renderList() {
    show("list");
    const root = screens.list;
    root.replaceChildren(byId("t-list").content.cloneNode(true));
    state.affairs = await api("affairs");
    const only = root.querySelector("#only-open");
    only.checked = localStorage.getItem("docket.onlyOpen") === "1";
    only.addEventListener("change", () => { localStorage.setItem("docket.onlyOpen", only.checked ? "1" : "0"); fillList(); });
    fillList();
}

function fillList() {
    const root = screens.list;
    const only = root.querySelector("#only-open").checked;
    const rows = state.affairs.filter((a) => !only || a.counts.open > 0);
    const body = root.querySelector("tbody");
    body.replaceChildren();
    for (const a of rows) {
        const tr = el("tr", { onclick: () => { location.hash = "#/affair/" + encodeURIComponent(a.key); } },
            el("td", {}, a.key), el("td", {}, a.number || "–"), el("td", {}, a.title || "–"), el("td", {}, a.type || "–"),
            el("td", {}, (a.documents || []).join(", ")),
            el("td", { class: "num" }, el("span", { class: a.counts.open ? "open-count" : "" }, a.counts.open)),
            el("td", { class: "num" }, a.counts.done));
        body.append(tr);
    }
    root.querySelector("#list-count").textContent = rows.length + " von " + state.affairs.length + " Geschäften";
    if (!rows.length) body.append(el("tr", {}, el("td", { colspan: 7, class: "empty" }, "Keine Geschäfte im Bestand.")));
}

// ---- affair

async function renderAffair(key) {
    show("affair");
    const root = screens.affair;
    root.replaceChildren(byId("t-affair").content.cloneNode(true));
    state.affair = await api("affairs/" + encodeURIComponent(key));
    state.doc = 0;
    state.page = 1;
    state.focus = null;
    state.fields = {};
    for (const d of state.affair.documents) {
        try { state.fields[d.name] = await api("documents/" + encodeURIComponent(d.name) + "/fields"); } catch { /* none */ }
    }
    const r = state.affair.record;
    root.querySelector(".title").textContent = (r.title && r.title.de) || key;
    root.querySelector(".key").textContent = (r.number ? r.number + " · " : "") + key;
    const select = root.querySelector(".doc");
    for (const [i, d] of state.affair.documents.entries()) select.append(el("option", { value: i }, d.name + " (" + d.pages + " S.)"));
    select.addEventListener("change", () => { state.doc = Number(select.value); state.page = 1; drawPage(); });
    root.querySelector(".prev").addEventListener("click", () => turn(-1));
    root.querySelector(".next").addEventListener("click", () => turn(1));
    root.querySelector(".sheet img").addEventListener("load", drawBlocks);
    drawPage();
    drawValues();
}

function turn(step) {
    const pages = state.affair.documents[state.doc].pages;
    state.page = Math.min(pages, Math.max(1, state.page + step));
    drawPage();
}

function docRecord() {
    const d = state.affair.documents[state.doc];
    return state.affair.record.docs.data.find((x) => x.id === d.id) || state.affair.record.docs.data[state.doc];
}

function blocksOf(body) {
    const out = [];
    for (const b of body || []) { out.push(b); if (b.type === "sec") out.push(...(b.content || [])); }
    return out;
}

function drawPage() {
    const root = screens.affair;
    const d = state.affair.documents[state.doc];
    root.querySelector(".page-no").textContent = "Seite " + state.page + " von " + d.pages;
    const counts = state.affair.counts;
    const chip = root.querySelector(".chip.open");
    chip.textContent = counts.open + " offen · " + counts.done + " erledigt · " + counts.places + " Fundstellen";
    chip.classList.toggle("has", counts.open > 0);
    root.querySelector(".sheet img").src = "/api/documents/" + encodeURIComponent(d.name) + "/pages/" + state.page + ".png";
}

function drawBlocks() {
    const root = screens.affair;
    const img = root.querySelector(".sheet img");
    const svg = root.querySelector(".sheet svg");
    svg.setAttribute("viewBox", "0 0 " + img.naturalWidth + " " + img.naturalHeight);
    svg.replaceChildren();
    const doc = docRecord();
    const pointing = {};
    for (const s of state.affair.sources) {
        if (s.doc !== doc.id) continue;
        pointing[s.block] = pointing[s.block] || { open: false, any: false };
        pointing[s.block].any = true;
        pointing[s.block].open = pointing[s.block].open || s.open;
    }
    for (const b of blocksOf(doc.body)) {
        if (b.page !== state.page) continue;
        const cls = [b.type, b.approve ? "flag" : "", pointing[b.id] ? (pointing[b.id].open ? "look" : "hit") : "",
            state.focus === b.id ? "focus" : ""].filter(Boolean).join(" ");
        const rect = el("rect", { x: b.x, y: b.y, width: b.width, height: b.height, class: cls, "data-id": b.id });
        rect.addEventListener("click", () => focusBlock(b.id));
        svg.append(rect);
        const label = el("text", { x: Math.max(4, b.x - 110), y: b.y + 30 }, b.id);
        svg.append(label);
    }
}

function focusBlock(id) {
    state.focus = id;
    drawBlocks();
    const doc = docRecord();
    const b = blocksOf(doc.body).find((x) => x.id === id);
    const text = b ? (b.title || b.text || (b.rows ? b.rows.map((r) => r.join(" | ")).join("\n") : "")
        || (b.items ? b.items.map((i) => (typeof i === "string" ? i : i.term + ": " + i.def)).join("\n") : "")) : "";
    screens.affair.querySelector(".block-info").textContent = id + " · " + (b ? b.type : "") + (b && b.approve ? " · Lesung prüfen" : "") + "\n" + text;
    for (const v of screens.affair.querySelectorAll(".value")) v.classList.toggle("focus", v.dataset.block === id && v.dataset.doc === String(doc.id));
}

function labelOf(s) {
    const r = state.affair.record;
    const parts = s.path.split(".");
    if (parts[0] === "custom-meta") return (r["custom-meta"][Number(parts[1])] || {})["meta-name"] || "Angabe";
    if (parts[0] === "contributors") {
        const row = r.contributors.data[Number(parts[2])] || {};
        return ((row.role && row.role.de) || "Beteiligte") + (parts[3] === "party" ? " · Partei" : parts[3] === "on-behalf-of" ? " · im Namen von" : "");
    }
    if (parts[0] === "docs") return LABELS[parts[3]] || parts[3];
    const head = parts[0] === "events" ? "events" : parts[0];
    return (LABELS[head] || head) + (parts[0] === "events" && parts[3] === "date" ? " · Datum" : "");
}

function answerOf(s) {
    const d = state.affair.documents.find((x) => x.id === s.doc);
    const report = d ? state.fields[d.name] : null;
    if (!report || !report.fields) return "";
    const hit = Object.values(report.fields).find((f) => (f.items || []).some((i) => i.block === s.block && String(i.value) === String(s.value)));
    return hit ? hit.value : "";
}

function drawValues() {
    const box = screens.affair.querySelector(".values");
    box.replaceChildren();
    const sources = [...state.affair.sources].sort((a, b) => Number(b.open) - Number(a.open));
    if (!sources.length) box.append(el("div", { class: "empty" }, "Keine Werte mit Fundstelle."));
    for (const s of sources) {
        const card = el("div", { class: "value " + (s.open ? "open" : s.review ? "done" : ""), "data-block": s.block, "data-doc": s.doc });
        const docName = (state.affair.documents.find((d) => d.id === s.doc) || {}).name || ("Dokument " + s.doc);
        const where = el("span", { class: "where", onclick: () => jump(s) }, docName + " · " + s.block);
        card.append(el("div", { class: "head" }, s.open ? el("span", { class: "mark" }, "!") : "", el("span", { class: "label" }, labelOf(s)),
            el("span", { class: "how" }, HOW[s.how] || s.how || ""), where));
        const values = s.values || { [s.path]: s.value };
        for (const [p, v] of Object.entries(values)) {
            card.append(el("div", { class: "text" }, Object.keys(values).length > 1 ? p.split(".").slice(-1)[0] + ": " + v : String(v)));
        }
        const answer = answerOf(s);
        if (answer && String(answer) !== String(s.value)) card.append(el("div", { class: "answer" }, "Modell: " + answer));
        if (s.review) {
            const r = s.review;
            const text = DECISION[r.decision] + (r.before !== undefined && r.decision === "changed" ? " von „" + r.before + "“" : "")
                + (r.by ? " · " + r.by : "") + " · " + r.at.slice(0, 16).replace("T", " ") + (r.rule ? " · Regel " + r.rule : "");
            card.append(el("div", { class: "decided " + r.decision }, text));
        }
        card.append(actions(s, Object.keys(values)));
        box.append(card);
    }
}

function actions(s, paths) {
    const acts = el("div", { class: "acts" });
    const input = el("input", { type: "text", placeholder: "neuer Wert", value: String(s.value ?? "") });
    const select = paths.length > 1 ? el("select", {}, ...paths.map((p) => el("option", { value: p }, p.split(".").slice(-1)[0]))) : null;
    acts.append(
        el("button", { class: "primary", onclick: () => decide(s, "confirmed") }, "Bestätigen"),
        select || "", input,
        el("button", { onclick: () => decide(s, "changed", input.value, select ? select.value : s.path) }, "Ändern"),
        el("button", { class: "ghost", onclick: () => decide(s, "rejected") }, "Verwerfen"));
    return acts;
}

async function decide(s, decision, after, path) {
    const by = who();
    try {
        const body = { source: s.source, decision, by };
        if (decision === "changed") { body.after = after; body.path = path; }
        state.affair = await api("affairs/" + encodeURIComponent(state.affair.key) + "/decisions", body);
        drawValues();
        drawPage();
        drawBlocks();
    } catch (e) {
        alert(e.message);
    }
}

function jump(s) {
    const i = state.affair.documents.findIndex((d) => d.id === s.doc);
    if (i >= 0 && i !== state.doc) { state.doc = i; screens.affair.querySelector(".doc").value = i; }
    const doc = docRecord();
    const b = blocksOf(doc.body).find((x) => x.id === s.block);
    if (b) state.page = b.page;
    state.focus = s.block;
    drawPage();
    focusBlock(s.block);
    screens.affair.querySelector(".sheet").scrollIntoView({ behavior: "smooth", block: "start" });
}

// ---- decisions

async function renderDecisions() {
    show("decisions");
    const root = screens.decisions;
    root.replaceChildren(byId("t-decisions").content.cloneNode(true));
    const affairs = await api("affairs");
    const rows = [];
    for (const a of affairs) rows.push(...await api("affairs/" + encodeURIComponent(a.key) + "/decisions"));
    rows.sort((a, b) => (b.at || "").localeCompare(a.at || ""));
    const body = root.querySelector("tbody");
    for (const r of rows) {
        body.append(el("tr", { onclick: () => { location.hash = "#/affair/" + encodeURIComponent(r.affair); } },
            el("td", {}, (r.at || "").slice(0, 16).replace("T", " ")), el("td", {}, r.by || "–"), el("td", {}, r.affair),
            el("td", {}, r.label), el("td", {}, DECISION[r.decision] || r.decision), el("td", {}, r.before ?? "–"), el("td", {}, r.after ?? "–")));
    }
    root.querySelector("#decisions-count").textContent = rows.length + " Entscheidungen";
    if (!rows.length) body.append(el("tr", {}, el("td", { colspan: 7, class: "empty" }, "Noch keine Entscheidungen.")));
}

// ---- router

function route() {
    const hash = location.hash || "#/";
    const m = hash.match(/^#\/affair\/(.+)$/);
    if (m) renderAffair(decodeURIComponent(m[1])).catch(fail);
    else if (hash === "#/decisions") renderDecisions().catch(fail);
    else renderList().catch(fail);
}

function fail(e) {
    screens.list.classList.add("active");
    screens.list.replaceChildren(el("div", { class: "empty" }, "Fehler: " + e.message));
}

byId("who").addEventListener("click", () => { localStorage.removeItem("docket.by"); who(); });
byId("who").textContent = localStorage.getItem("docket.by") ? "als " + localStorage.getItem("docket.by") : "Kürzel setzen";
window.addEventListener("hashchange", route);
route();
