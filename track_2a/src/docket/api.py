"""What the web server answers with: the affairs and their values with a place, the decisions and what they
set in motion (a rule proposed, a rule applied), the vocabulary, the runs of the admin. One object, shared by
the request handlers."""

from __future__ import annotations

import hmac
import json
import secrets
import threading
import time

from typing import Callable

from docket.affair.validator import Contract
from docket import public
from docket.config import Config
from docket.document.bridge import Knowledge
from docket.document.language import language_of
from docket.document.response import lift, whole
from docket.fields.fields import Fields, definition_of
from docket.fields.placer import blocks_of, day, find_block, get_at, read_at
from docket.jobs import Jobs
from docket.pipeline import load_field_file, load_knowledge
from docket.store.base import Store, stamp
from docket.store.entries import counts_of, entries_of
from docket.store.review import apply_decision, label_of, label_of_path, review_of
from docket.store.rows import (
    KIND, PLACED, blocks_of_document, find_value, follow, note_decision, place_of,
)
from docket.store.rules import Rules, apply, labels, shape
from docket.store.vocabulary import Vocabulary

SAME_EXAMPLES = 5


# the label the kind of a document stands under in a record of the affair schema, for an affair without rows
KIND_LABEL = "docs.article-type"


# how long a session of the administration lasts after its last request, in seconds
SESSION = 12 * 60 * 60


class _Unfit(ValueError):
    """A decision after which the record would no longer fit the contract, with what would not fit."""

    def __init__(self, violations: list[str]):
        super().__init__("the record would not fit the contract")
        self.violations = violations


class App:
    def __init__(self, store: Store, contract: Contract, config: Config, jobs: Jobs | None = None):
        self.store = store
        self.contract = contract
        self.config = config
        self.jobs = jobs if jobs is not None else Jobs(config)
        self.locks: dict[str, threading.Lock] = {}
        # who is signed in to the administration: session to the name of the account and the time it ends
        self.sessions: dict[str, tuple[str, float]] = {}
        self._guard = threading.Lock()
        self._fields: Fields | None = None
        self._knowledge: Knowledge | None = None

    def lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self.locks.setdefault(key, threading.Lock())

    # ---- what the fields file says about the record

    def fields(self) -> Fields:
        if self._fields is None:
            self._fields = load_field_file(self.config, self.contract)
        return self._fields

    def knowledge(self) -> Knowledge:
        if self._knowledge is None:
            self._knowledge = load_knowledge(self.config)
        return self._knowledge

    def head(self, record: dict) -> dict:
        """Number, title, date and type of an affair for the list and the head of its view: found by what the
        fields are (the role, the entity), not by the keys this record happens to use."""
        fields = self.fields().fields
        by_role = self.fields().by_role()

        def at(role: str):
            f = fields.get(by_role.get(role, ""))
            return read_at(record, f) if f is not None and "[]" not in f.path else None

        kind = fields.get(by_role.get("type", ""))
        standard = get_at(record, kind.standard.split(".")) if kind is not None and kind.standard else None
        named = standard.get("de") if isinstance(standard, dict) else None
        return {"number": at("number"), "title": at("title"), "date": at("date"), "type": named or at("type")}

    def definition(self) -> dict:
        """The fields of the fields file with what each is, and against the store: in how many documents a
        field was asked and in how many never, since the document was read before the field existed. A field
        the documents were asked and the fields file no longer has is listed as gone."""
        counts = self.store.asked_counts()
        fields = self.fields()
        now = definition_of(fields)
        rows = [{"name": name, "entity": f.entity, "role": f.role, "lookup": f.lookup, "list": f.list_name,
                 "asked": counts["fields"].get(name, 0),
                 "never": counts["documents"] - counts["fields"].get(name, 0)}
                for name, f in fields.fields.items()]
        gone = [{"name": name, "asked": count} for name, count in sorted(counts["fields"].items())
                if name not in fields.fields]
        return {"version": now["version"], "documents": counts["documents"], "versions": counts["versions"],
                "entities": list(fields.entities.values()), "fields": rows, "gone": gone}

    def learnt(self) -> dict:
        """What the second opinion learnt from the store, way by way: the usual place per parliament and field,
        the network per field, each with how often it agreed and disagreed on documents held back and whether
        it is used. Nothing learnt gives no ways."""
        data = self.store.get_learnt() or {}
        ways = []
        for parliament, places in sorted((data.get("places") or {}).items()):
            for name, p in places.items():
                ways.append({"way": "place", "parliament": parliament, "field": name, "documents": p["documents"],
                             "share": p["share"], "cut": p["cut"], "agree": p["agree"], "disagree": p["disagree"],
                             "use": p["use"]})
        for net in (data.get("network"), data.get("lists")):
            for name, c in ((net or {}).get("cuts") or {}).items():
                ways.append({"way": "network", "parliament": "", "field": name, "cut": c["cut"], "agree": c["agree"],
                             "disagree": c["disagree"], "use": c["use"]})
        return {"documents": data.get("documents", 0), "ways": ways}

    def _field_of(self, label: str) -> str:
        """The field of the fields file whose values stand under this label in a record, when it is the only
        one; else the label itself."""
        names = [n for n, f in self.fields().fields.items() if label_of(f.path, f.fixed) == label]
        return names[0] if len(names) == 1 else label

    def _values(self, a: dict):
        """Every value with a place in an affair, the values of one entry each on its own: the entry, the path
        of the value, the value, its field and its label. The field is the one of the fields file, taken from
        the row that sits there; without a row, from the label."""
        at = {(p["source"], p["path"]): r["field"] for r in self._rows(a) for p in r.get("places") or []
              if p["part"] == ""}
        for e in self.entries(a):
            for path, value in (e.get("values") or {e["path"]: e["value"]}).items():
                label = e["label"] if path == e["path"] else label_of_path(path)
                yield e, path, value, at.get((e["source"], path)) or self._field_of(label), label

    # ---- what a visitor reads: the affairs in the affair schema, and the tables that follow from them

    def name_records(self) -> int:
        """Gives the records a store holds from before a record named itself the two fields it is known by:
        `id`, the key it is stored under, and `body_key`, the parliament its documents were told or read to
        come from. Everything a visitor is shown hangs on them, and a store is older than the code that reads
        it. A record that has both stays as it is. Returns how many were completed."""
        done = 0
        for a in self.store.list_affairs():
            record = a["record"]
            if "schema" not in record:
                continue
            body = record.get("body_key") or next(
                (k for k in (self._body_of(d.get("name")) for d in a.get("documents", [])) if k), "")
            named = {"schema": record["schema"], "id": record.get("id") or a["key"]}
            if body:
                named["body_key"] = body
            if all(record.get(k) == v for k, v in named.items()):
                continue
            with self.lock(a["key"]):
                rest = {k: v for k, v in record.items() if k not in named}
                self.store.put_affair(a["key"], {**named, **rest}, a["documents"])
            done += 1
        return done

    def records(self, asked: dict[str, str] | None = None) -> dict:
        """The affairs that fit a search, in the affair schema, without the blocks of their documents."""
        return public.listed([a["record"] for a in self.store.list_affairs()], asked, self.knowledge().bodies)

    def record(self, key: str) -> dict | None:
        """One affair in the affair schema, whole."""
        data = self.store.get_affair(key)
        return data["record"] if data else None

    def table(self, name: str, asked: dict[str, str] | None = None) -> dict:
        """Those who take part, the groups, the meetings or the events of the affairs that fit."""
        return public.table(name, [a["record"] for a in self.store.list_affairs()], asked, self.knowledge().bodies)

    # ---- documents

    def document(self, name: str) -> dict | None:
        """One document as the page view shows it, whatever shape the record of its affair has: its blocks in
        reading order, its language, and the answers within it with the block each begins at. None when the
        store does not know the document."""
        blocks = self.store.get_blocks(name)
        affair = held = None
        for a in self.store.list_affairs():
            held = next((d for d in a.get("documents", []) if d["name"] == name), None)
            if held is not None:
                affair = a
                break
        if blocks is None and affair is not None:
            # a store filled before the blocks were kept on their own: the record of the affair holds them
            entries = (affair["record"].get("docs") or {}).get("data", [])
            blocks = whole(next((e for e in entries if e.get("id") == held["id"]), None))
        if blocks is None:
            return None
        _, answers = lift(blocks, self.knowledge().answers)
        return {
            "name": name,
            "affair": affair["key"] if affair else None,
            "id": held["id"] if held else None,
            "pages": held.get("pages") if held else None,
            "language": language_of(blocks),
            "answers": [{"title": r["title"], "block": r["body"][0]["id"], "page": r["body"][0]["page"]}
                        for r in answers if r["body"]],
            "blocks": blocks,
        }

    def document_record(self, name: str) -> dict | None:
        """One document alone, in the affair schema: its entry in the record of its affair, with what the
        record says of it and its blocks. None when no affair holds the document."""
        for a in self.store.list_affairs():
            held = next((d for d in a.get("documents", []) if d["name"] == name), None)
            if held is not None:
                entries = (a["record"].get("docs") or {}).get("data", [])
                return next((e for e in entries if e.get("id") == held["id"]), None)
        return None

    # ---- affairs

    def _rows(self, a: dict) -> list[dict]:
        """The rows of the documents of an affair that name it."""
        return [r for d in a.get("documents", []) for r in self.store.get_rows(d["name"])
                if r.get("affair") == a["key"]]

    def entries(self, a: dict) -> list[dict]:
        """The values of an affair as the review shows them: built from the rows of its documents, each with
        the id of its row (docket.store.entries). What the record holds with a place and no row stands for
        comes with it, the place as its id."""
        numbers = {d["name"]: d["id"] for d in a.get("documents", [])}
        in_record = {e.get("id"): e for e in (a["record"].get("docs") or {}).get("data") or []}
        blocks: dict[str, list[dict]] = {}

        def block_of(name: str, ident: str) -> dict | None:
            if name not in blocks:
                blocks[name] = blocks_of_document(self.store, name, in_record.get(numbers.get(name)))
            return find_block(ident, blocks[name])

        return entries_of(self._rows(a), numbers, self.fields(), block_of, a["record"])

    def affair(self, key: str) -> dict | None:
        data = self.store.get_affair(key)
        if data is None:
            return None
        record = data["record"]
        sources = self.entries(data)
        if any(e["open"] for e in sources):
            self._same(key, sources)
        self._hints(data, sources)
        card = self._card(data, sources)
        return {
            "key": key,
            "head": self.head(record),
            "body": card["body"],
            "papers": card["papers"],
            "record": record,
            "documents": data.get("documents", []),
            "sources": sources,
            "counts": card["counts"],
            "updated_at": data.get("updated_at"),
        }

    def summaries(self, asked: dict[str, str] | None = None) -> list[dict]:
        """The affairs for the lists: number, title, date and type, the parliament, the documents with what
        each is and its language, and how many values are open. `asked` narrows them as a visitor searches:
        `q` (every word must stand in the title, the number, the type, the parliament or a document's name),
        `body` (the parliament's key), `type`, `kind` (of a document) and `language`."""
        asked = {k: v.strip() for k, v in (asked or {}).items() if v and v.strip()}
        out = []
        for a in self.store.list_affairs():
            one = self._card(a, self.entries(a))
            if self._asked_for(one, asked):
                out.append(one)
        return sorted(out, key=lambda s: (-s["counts"]["open"], s["key"]))

    def _card(self, a: dict, entries: list[dict]) -> dict:
        """One affair as a list shows it: its head, its parliament, its documents, its counts."""
        head = self.head(a["record"])
        # what each document is within the affair: a value like the others, told by its field
        kinds = {e["doc"]: e["value"] for e in entries if e.get("field") == KIND or e["label"] == KIND_LABEL}
        in_record = {e.get("id"): e for e in (a["record"].get("docs") or {}).get("data") or []}
        documents = a.get("documents", [])
        papers = [{"name": d.get("name"), "id": d.get("id"), "pages": d.get("pages"),
                   "kind": kinds.get(d.get("id")), "language": (in_record.get(d.get("id")) or {}).get("language")}
                  for d in documents]
        key = next((k for k in (self._body_of(d.get("name")) for d in documents) if k), "")
        body = self.knowledge().bodies.get(key) or {}
        return {
            "key": a["key"],
            "number": head["number"],
            "title": head["title"],
            "date": head["date"],
            "type": head["type"],
            "body": {"key": key, "name": body.get("name") or "", "level": body.get("level") or "",
                     "parliament": body.get("parliament") or ""} if key else None,
            "documents": [d.get("name") for d in documents],
            "kinds": [p["kind"] for p in papers],
            "papers": papers,
            "counts": counts_of(entries),
            "updated_at": a.get("updated_at"),
        }

    def _body_of(self, name: str | None) -> str:
        """The key of the parliament a document was told to come from, or was read to; empty when unknown."""
        report = self.store.get_fields(str(name or "")) or {}
        return str((report.get("identity") or {}).get("body") or "")

    @staticmethod
    def _asked_for(one: dict, asked: dict[str, str]) -> bool:
        """Whether an affair of the list is what a visitor searches for."""
        body = one["body"] or {}
        text = " ".join(str(v or "") for v in (one["title"], one["number"], one["type"], one["key"], body.get("name"),
                                              body.get("parliament"), *one["documents"])).lower()
        return (
            all(word in text for word in asked.get("q", "").lower().split())
            and asked.get("body", body.get("key")) == body.get("key")
            and asked.get("type", one["type"]) == one["type"]
            and ("kind" not in asked or asked["kind"] in one["kinds"])
            and ("language" not in asked or asked["language"] in [p["language"] for p in one["papers"]])
        )

    def _hints(self, data: dict, sources: list[dict]) -> None:
        """For the id of a person: the name the register holds for it, so a reviewer sees who is meant. The
        parliament comes from the identity in the document's fields report."""
        names = {d.get("id"): d.get("name") for d in data.get("documents", [])}
        by_body: dict[str, dict] = {}
        for e in sources:
            if e["label"] != "contributors.person_id" or e["value"] is None:
                continue
            report = self.store.get_fields(str(names.get(e["doc"]) or "")) or {}
            body = str((report.get("identity") or {}).get("body") or "")
            if body and body not in by_body:
                by_body[body] = {i: r for r in self.store.get_register(body) for i in r.get("ids") or []}
            person = by_body.get(body, {}).get(e["value"])
            if person is not None:
                e["hint"] = person["label"] + (f" ({person['party']})" if person.get("party") else "")

    def _affairs_with(self, wanted: list[tuple[str, Callable[[str], bool]]]) -> list[dict]:
        """The affairs that can hold a value of one of the fields (named as in the fields file, or by the label
        its values stand under) that fits its test, newest first: asked of the rows, so that only these
        records are read. An affair without rows is always among them, and so is every affair when a label is
        no field of the fields file (what a lookup put into the record, as the id of a person)."""
        fields = self.fields().fields
        keys: set[str] = set()
        for label, fits in wanted:
            names = [label] if label in fields else [n for n, f in fields.items() if label_of(f.path, f.fixed) == label]
            if not names:
                return self.store.list_affairs()
            for name in names:
                for row in self.store.find_rows(field=name):
                    # a date stands in the record as its day, whatever way it was printed
                    value = str(row["value"])
                    if row["state"] == PLACED and row.get("affair") and (fits(value) or fits(day(value))):
                        keys.add(row["affair"])
        without = set(self.store.affairs_without_rows())
        if without:
            return [a for a in self.store.list_affairs() if a["key"] in keys or a["key"] in without]
        found = [a for a in (self.store.get_affair(k) for k in sorted(keys)) if a is not None]
        return sorted(found, key=lambda a: a.get("updated_at", ""), reverse=True)

    def _same(self, key: str, sources: list[dict]) -> None:
        """For every open value: how many values of the same field, found the same way, with the same shape
        stand in the other affairs ("n further documents with the same error")."""
        shapes: dict[str, set[str]] = {}
        for e in sources:
            if e["open"]:
                shapes.setdefault(e["label"], set()).add(shape(str(e["value"])))
        # a value that is missing has no row to be found by
        wanted = [(label, (lambda v: True) if shape("None") in fit else (lambda v, fit=fit: shape(v) in fit))
                  for label, fit in shapes.items()]
        others = []
        for a in self._affairs_with(wanted) if wanted else []:
            if a["key"] == key:
                continue
            for e in self.entries(a):
                others.append((a["key"], e))
        for e in sources:
            if not e["open"]:
                continue
            want = (e["label"], e["how"], shape(str(e["value"])))
            hits = [(k, o) for k, o in others if (o["label"], o["how"], shape(str(o["value"]))) == want]
            e["same"] = {
                "count": len(hits),
                "examples": [{"key": k, "value": o["value"], "doc": o["doc"]} for k, o in hits[:SAME_EXAMPLES]],
            }

    # ---- decisions

    def decide(self, key: str, body: dict) -> tuple[int, dict]:
        with self.lock(key):
            data = self.store.get_affair(key)
            if data is None:
                return 404, {"error": "no such affair"}
            # the value is named by the id of its row; where it sits in the record, the row knows. A value no
            # row stands for, and a caller from before the ids, names the place in the record itself
            ident = str(body.get("id") or "")
            known = find_value(self._rows(data), ident) if ident else None
            source_path = known[1]["source"] if known else str(body.get("source") or ident)
            earlier = next((e for e in self.entries(data) if e["source"] == source_path), None)
            path = str((known[1]["path"] if known else body.get("path")) or (earlier or {}).get("path") or "")
            try:
                record = self._take(data, earlier, source_path, path, str(body.get("decision", "")),
                                    str(body.get("by", "")), body.get("after"), body.get("rule"))
            except _Unfit as e:
                return 409, {"error": "the record would not fit the contract", "violations": e.violations[:5]}
            except ValueError as e:
                return 400, {"error": str(e)}
            self.store.save_record(key, record)
            now = {**data, "record": record}
            entry = next(e for e in self.entries(now) if e["source"] == source_path)
            # the field of the value that was decided on: an entry can hold several (a name and its party)
            named = next(((f, lb) for e, p, _, f, lb in self._values(now)
                          if e["source"] == source_path and p == path), (entry["label"], entry["label"]))
            self._log(key, entry, path, *named)
            proposals = self._rules_after(key, entry, earlier, path, named[0], now)
        return 200, {**(self.affair(key) or {}), "proposals": proposals}

    def _take(self, a: dict, entry: dict | None, source: str, path: str, decision: str, by: str, after,
              rule: str | None) -> dict:
        """One decision on one value of an affair. Where a row stands for the value, the decision is written at
        the row and the record is the stored one with the decisions of the rows laid onto it: the row is what
        outlasts the record, a new run and a record of another shape take the decision from it. A value no row
        stands for is decided in the record itself. Returns the record as it then is, not yet saved; the row
        is stored. Raises ValueError when the decision or the place is not right, and when the record would no
        longer fit the contract."""
        for document in a.get("documents", []):
            rows = self.store.get_rows(document["name"])
            hit = place_of(rows, source, path)
            # only the rows that name this affair are its own
            if hit is None or hit[0].get("affair") != a["key"]:
                continue
            row, place = hit
            if entry is None:
                raise ValueError(f"no value for the source at {source}")
            review = review_of(decision, by, self._value_at(entry, path), after, rule)
            note_decision(row, place, review, after if decision == "changed" else None)
            others = [r for r in self._rows(a) if r["doc"] != document["name"]]
            record = follow(a["record"], [*[r for r in rows if r.get("affair") == a["key"]], *others])[0]
            # a record in which the value has no place stays as it is; what the decision changes must fit
            errors = self.contract.check(record) if record != a["record"] else []
            if errors:
                raise _Unfit(errors)
            self.store.put_rows(document["name"], rows)
            return record
        record = apply_decision(a["record"], source, decision, by, after, path or None, rule)
        errors = self.contract.check(record)
        if errors:
            raise _Unfit(errors)
        return record

    @staticmethod
    def _value_at(entry: dict, path: str):
        """The value of an entry at one of its paths."""
        return (entry.get("values") or {}).get(path, entry["value"]) if path != entry["path"] else entry["value"]

    def _log(self, key: str, entry: dict, path: str, field: str, label: str) -> None:
        review = entry["review"]
        self.store.add_decision({
            "affair": key, "doc": entry["doc"], "block": entry["block"], "path": path or entry["path"],
            "label": label, "field": field, "how": entry["how"], "approve": entry["approve"],
            "decision": review["decision"], "before": review.get("before"),
            "after": self._value_at(entry, path or entry["path"]),
            "by": review.get("by"), "at": review["at"], "rule": review.get("rule"),
        })

    def _labelled(self, a: dict) -> dict[str, dict[str, str]]:
        """What every document of an affair prints with a label, by the number the document has in the
        affair: from the blocks the store keeps for it, else from its entry in the record."""
        entries = {e.get("id"): e for e in (a["record"].get("docs") or {}).get("data") or []}
        known = {d["id"]: d["name"] for d in a.get("documents") or []}
        return {str(i): labels(blocks_of(blocks_of_document(self.store, known.get(i, ""), entries.get(i))))
                for i in {*entries, *known}}

    def _rules_after(self, key: str, entry: dict, earlier: dict | None, path: str, field: str,
                     a: dict) -> list[dict]:
        """Counts a decision by hand for the learning: on the rule it took back or confirmed, against the rules
        it contradicts, on the patterns its change carries. It counts for the field of the value that was
        decided on. Returns the rules that stand proposed for this field and would change something, the one
        that reaches furthest first; nothing is applied here."""
        review = entry["review"]
        if review.get("by") == "rule":
            return []
        rules = Rules(self.store.get_rules())
        labelled = self._labelled(a).get(str(entry["doc"]))
        changed = False
        # a person confirms or takes back what a rule had set
        if earlier and earlier.get("review") and earlier["review"].get("rule"):
            rules.tally(earlier["review"]["rule"], "confirmed" if review["decision"] == "confirmed" else "withdrawn")
            changed = True
        now = self._value_at(entry, path or entry["path"])
        value = None if now is None else str(now)
        before = review.get("before") if review["decision"] == "changed" else value
        if review["decision"] in ("confirmed", "changed") and before is not None:
            changed = rules.speak_against(field, before, value, review["decision"], labelled) or changed
        if review["decision"] == "changed" and "before" in review and value is not None:
            noted = rules.note(field, review["before"], value, key, review.get("by", ""), labelled)
            changed = bool(noted) or changed
        if changed:
            self.store.put_rules(rules.rows)
        return self._proposals(rules, field)

    def _proposals(self, rules: Rules, field: str | None = None) -> list[dict]:
        out = [{**r, "reach": self._reach(r)} for r in rules.proposed(field)]
        return sorted((r for r in out if r["reach"]["count"]), key=lambda r: -r["reach"]["count"])

    @staticmethod
    def _fits(rule: dict) -> Callable[[str], bool]:
        """Which values of its field a rule can touch at all, to find the affairs worth reading: a rule of a
        label can touch any, since it hangs on the document and not on the value."""
        if rule["kind"] == "label":
            return lambda value: True
        return lambda value: apply(rule, value) is not None

    def _reach(self, rule: dict) -> dict:
        """What a rule would change in the store: how many values in how many affairs, with examples. The same
        values _apply_rule changes: of the rule's field, without a review, fitting the rule."""
        count, affairs, examples = 0, set(), []
        for a in self._affairs_with([(rule["field"], self._fits(rule))]):
            labelled = self._labelled(a) if rule["kind"] == "label" else {}
            for e, _, value, field, label in self._values(a):
                # a rule from before the fields were named carries the label
                if rule["field"] not in (field, label) or e["review"] is not None or value is None:
                    continue
                after = apply(rule, str(value), labelled.get(str(e["doc"])))
                if after is None:
                    continue
                count += 1
                affairs.add(a["key"])
                if len(examples) < SAME_EXAMPLES:
                    examples.append({"key": a["key"], "before": str(value), "after": after})
        return {"count": count, "affairs": len(affairs), "examples": examples}

    def _apply_rule(self, rule: dict) -> int:
        """Changes every value of the rule's field in the store that fits and has no review yet; returns the
        count. Every change carries a review by "rule" with the rule's id."""
        count = 0
        for a in self._affairs_with([(rule["field"], self._fits(rule))]):
            record = a["record"]
            labelled = self._labelled(a) if rule["kind"] == "label" else {}
            touched = False
            for e, path, value, field, label in list(self._values(a)):
                if rule["field"] not in (field, label) or e["review"] is not None or value is None:
                    continue
                after = apply(rule, str(value), labelled.get(str(e["doc"])))
                if after is None:
                    continue
                try:
                    record = self._take({**a, "record": record}, e, e["source"], path, "changed", "rule", after,
                                        rule["id"])
                except ValueError:
                    continue
                touched = True
                count += 1
                done = next(x for x in self.entries({**a, "record": record}) if x["source"] == e["source"])
                self._log(a["key"], done, path, field, label)
            if touched:
                self.store.save_record(a["key"], record)
        return count

    # ---- rules

    def rules(self) -> list[dict]:
        """Every rule; a proposed one with what it would change."""
        rows = self.store.get_rules()
        return [{**r, "reach": self._reach(r)} if r.get("state") == "proposed" else r for r in rows]

    def answer_rule(self, rule_id: str, accept: bool, by: str) -> tuple[int, dict]:
        """A person's answer to a proposed rule. Yes applies it to every value that fits; no keeps it from
        being proposed again."""
        rules = Rules(self.store.get_rules())
        try:
            rule = rules.answer(rule_id, accept, by)
        except ValueError as e:
            return 409, {"error": str(e)}
        if rule is None:
            return 404, {"error": "no such rule"}
        if accept:
            rule["applied"] = rule.get("applied", 0) + self._apply_rule(rule)
        self.store.put_rules(rules.rows)
        return 200, rule

    def switch_rule(self, rule_id: str, active: bool, by: str) -> tuple[int, dict]:
        rules = Rules(self.store.get_rules())
        rule = rules.switch(rule_id, active, by)
        if rule is None:
            return 404, {"error": "no such rule"}
        if active:
            rule["applied"] = rule.get("applied", 0) + self._apply_rule(rule)
        self.store.put_rules(rules.rows)
        return 200, rule

    # ---- vocabulary

    def vocabulary(self, name_of_list: str | None, body: str | None) -> list[dict]:
        return Vocabulary(self.store.get_vocabulary()).names(name_of_list or None, body)

    def parliaments(self) -> dict:
        """The parliaments by OpenParlData's body key, with their names (data/knowledge/bodies.json): the
        vocabulary speaks of a parliament by its key, the screen by its name."""
        path = self.config.data_dir / "knowledge" / "bodies.json"
        return json.loads(path.read_text(encoding="utf-8"))["bodies"] if path.is_file() else {}

    def set_name(self, body: dict) -> tuple[int, dict]:
        """A person says what a name of a parliament stands for, or with "reset" takes that back. Without a
        parliament and with the wordings of a new standard name (`standard` as {de, fr, it, en}), the person
        adds that standard name to the list."""
        vocabulary = Vocabulary(self.store.get_vocabulary())
        where = (str(body.get("list", "")), str(body.get("body", "")).strip(), str(body.get("name", "")))
        if body.get("reset"):
            try:
                row, gone = vocabulary.reset(*where)
            except ValueError as e:
                return 409, {"error": str(e)}
            if row is None and gone is None:
                return 404, {"error": "no row a person changed"}
            if row is not None:
                self.store.put_vocabulary([row])
            else:
                self.store.drop_vocabulary([gone])
            return 200, row or {**gone, "removed": True}
        standard = body.get("standard")
        try:
            if not where[1] and isinstance(standard, dict):
                row = vocabulary.add(where[0], standard, str(body.get("by", "")))
            else:
                row = vocabulary.set(*where, None if standard is None else str(standard), str(body.get("by", "")))
        except ValueError as e:
            return 400, {"error": str(e)}
        self.store.put_vocabulary([row])
        return 200, row

    # ---- register

    def register(self, body: str | None) -> list[dict]:
        """The persons of one parliament; without one, what the register learnt and what it still counts, over
        all parliaments."""
        if body:
            return self.store.get_register(body)
        out = []
        for b in self.store.register_bodies():
            out.extend(r for r in self.store.get_register(b) if r.get("origin") != "stem")
        return out

    def forget(self, body: dict) -> tuple[int, dict]:
        """Takes a learnt person or a candidate out of the register. A person of OpenParlData's list stays."""
        where, key = str(body.get("body", "")), str(body.get("key", ""))
        row = next((r for r in self.store.get_register(where) if r["key"] == key), None) if where else None
        if row is None:
            return 404, {"error": "no such row"}
        if row.get("origin") == "stem":
            return 409, {"error": "a person of OpenParlData's list is not removed here"}
        self.store.drop_register([row])
        return 200, {**row, "removed": True}

    # ---- runs

    # ---- the account of the administration

    def sign_in(self, user: str, password: str) -> str | None:
        """A session for the account of the administration, or None when the name or the password is not
        the one set (ADMIN_USER, ADMIN_PASSWORD). Without a password set there is nothing to sign in to."""
        wanted = self.config.admin_password
        right = bool(wanted) and hmac.compare_digest(user.strip().encode(), self.config.admin_user.encode()) \
            and hmac.compare_digest(password.encode(), wanted.encode())
        if not right:
            return None
        now = time.time()
        self.sessions = {s: held for s, held in self.sessions.items() if held[1] > now}
        session = secrets.token_urlsafe(32)
        self.sessions[session] = (self.config.admin_user, now + SESSION)
        return session

    def sign_out(self, session: str | None) -> None:
        self.sessions.pop(session or "", None)

    def account(self, session: str | None) -> str | None:
        """The name of the account behind a request to the administration: the one signed in with this
        session; without a password set, the administration is open and everyone acts under the account's
        name. None when a password is set and the session is none or over."""
        if not self.config.admin_password:
            return self.config.admin_user
        held = self.sessions.get(session or "")
        if held is None or held[1] < time.time():
            self.sessions.pop(session or "", None)
            return None
        self.sessions[session] = (held[0], time.time() + SESSION)
        return held[0]

    def run_pdf(self, name: str, data: bytes, model: bool | None, body: str = "") -> tuple[int, dict]:
        """Queues a run over an uploaded PDF. `body` is the key of its parliament where the person tells it;
        only PDFs come in, nothing is fetched from anywhere."""
        if body and body not in load_knowledge(self.config).bodies:
            return 400, {"error": "no such parliament"}
        try:
            job = self.jobs.submit_pdf(name, data, self._model(model), body)
        except ValueError as e:
            return 400, {"error": str(e)}
        return 202, self.jobs.get(job.id) or {}

    def ask_again(self, name: str | None) -> tuple[int, dict]:
        """Queues the asking of the stored documents for a field they were never asked."""
        if not self.config.api_key:
            return 409, {"error": "no model configured"}
        if name is not None and name not in self.fields().fields:
            return 404, {"error": "no such field"}
        job = self.jobs.submit_ask(name)
        return 202, self.jobs.get(job.id) or {}

    def _model(self, model: bool | None) -> bool:
        return bool(self.config.api_key) if model is None else bool(model) and bool(self.config.api_key)

    def health(self) -> dict:
        return {"ok": True, "store": self.store.kind, "model": bool(self.config.api_key),
                "admin": "account" if self.config.admin_password else "open", "at": stamp()}
