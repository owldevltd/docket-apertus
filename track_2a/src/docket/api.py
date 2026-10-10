"""What the web server answers with: the affairs and their values with a place, the decisions and what they
set in motion (a rule proposed, a rule applied), the vocabulary, the runs of the admin. One object, shared by
the request handlers."""

from __future__ import annotations

import json
import threading

from typing import Callable

from docket.affair.validator import Contract
from docket.config import Config
from docket.fields.fields import Fields, definition_of
from docket.fields.placer import day, get_at
from docket.jobs import Jobs
from docket.pipeline import load_field_file
from docket.store.base import Store, stamp
from docket.store.review import apply_decision, counts, label_of, label_of_path, sources_of
from docket.store.rows import PLACED, note_decision, place_of
from docket.store.rules import Rules, apply, shape
from docket.store.vocabulary import Vocabulary

SAME_EXAMPLES = 5


class App:
    def __init__(self, store: Store, contract: Contract, config: Config, jobs: Jobs | None = None):
        self.store = store
        self.contract = contract
        self.config = config
        self.jobs = jobs if jobs is not None else Jobs(config)
        self.locks: dict[str, threading.Lock] = {}
        self._guard = threading.Lock()
        self._fields: Fields | None = None

    def lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self.locks.setdefault(key, threading.Lock())

    # ---- what the fields file says about the record

    def fields(self) -> Fields:
        if self._fields is None:
            self._fields = load_field_file(self.config, self.contract)
        return self._fields

    def head(self, record: dict) -> dict:
        """Number, title, date and type of an affair for the list and the head of its view: found by what the
        fields are (the role, the entity), not by the keys this record happens to use."""
        fields = self.fields().fields
        by_role = self.fields().by_role()

        def at(role: str):
            f = fields.get(by_role.get(role, ""))
            return get_at(record, f.path) if f is not None and "[]" not in f.path else None

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
        rows = [r for d in a.get("documents", []) for r in self.store.get_rows(d["name"])
                if r.get("affair") == a["key"]]
        at = {(p["source"], p["path"]): r["field"] for r in rows for p in r.get("places") or [] if p["part"] == ""}
        for e in sources_of(a["record"]):
            for path, value in (e.get("values") or {e["path"]: e["value"]}).items():
                label = e["label"] if path == e["path"] else label_of_path(path)
                yield e, path, value, at.get((e["source"], path)) or self._field_of(label), label

    # ---- affairs

    def affair(self, key: str) -> dict | None:
        data = self.store.get_affair(key)
        if data is None:
            return None
        record = data["record"]
        sources = sources_of(record)
        if any(e["open"] for e in sources):
            self._same(key, sources)
        self._hints(data, sources)
        return {
            "key": key,
            "head": self.head(record),
            "record": record,
            "documents": data.get("documents", []),
            "sources": sources,
            "counts": counts(record),
            "updated_at": data.get("updated_at"),
        }

    def summaries(self) -> list[dict]:
        out = []
        for a in self.store.list_affairs():
            r = a["record"]
            head = self.head(r)
            out.append({
                "key": a["key"],
                "number": head["number"],
                "title": head["title"],
                "type": head["type"],
                "documents": [d.get("name") for d in a.get("documents", [])],
                "kinds": [d.get("article-type") for d in (r.get("docs") or {}).get("data", [])],
                "counts": counts(r),
                "updated_at": a.get("updated_at"),
            })
        return sorted(out, key=lambda s: (-s["counts"]["open"], s["key"]))

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
            for e in sources_of(a["record"]):
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
            source_path = str(body.get("source", ""))
            earlier = next((e for e in sources_of(data["record"]) if e["source"] == source_path), None)
            try:
                record = apply_decision(
                    data["record"], source_path, str(body.get("decision", "")),
                    str(body.get("by", "")), body.get("after"), body.get("path"), body.get("rule"),
                )
            except ValueError as e:
                return 400, {"error": str(e)}
            errors = self.contract.check(record)
            if errors:
                return 409, {"error": "the record would not fit the contract", "violations": errors[:5]}
            path = str(body.get("path") or (earlier or {}).get("path") or "")
            self._to_row(data, source_path, path, record)
            self.store.save_record(key, record)
            entry = next(e for e in sources_of(record) if e["source"] == source_path)
            # the field of the value that was decided on: an entry can hold several (a name and its party)
            named = next(((f, lb) for e, p, _, f, lb in self._values({**data, "record": record})
                          if e["source"] == source_path and p == path), (entry["label"], entry["label"]))
            self._log(key, entry, path, *named)
            proposals = self._rules_after(key, entry, earlier, path, named[0])
        return 200, {**(self.affair(key) or {}), "proposals": proposals}

    def _to_row(self, data: dict, source_path: str, value_path: str, record: dict) -> bool:
        """Writes the decision the record now shows at a source to the row whose value sits there, so that it
        outlasts the record: a new run and a record of another shape take it from the row. False when no row
        sits there (the affair has none, or the place is not a value read from a document)."""
        for document in data.get("documents", []):
            rows = self.store.get_rows(document["name"])
            hit = place_of(rows, source_path, value_path)
            # only the rows that name this affair are its own
            if hit is None or hit[0].get("affair") != data["key"]:
                continue
            row, place = hit
            review = get_at(record, source_path.split("."))["review"]
            value = get_at(record, value_path.split(".")) if review["decision"] == "changed" else None
            note_decision(row, place, review, value)
            self.store.put_rows(document["name"], rows)
            return True
        return False

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

    def _rules_after(self, key: str, entry: dict, earlier: dict | None, path: str, field: str) -> list[dict]:
        """Counts a decision by hand for the learning: on the rule it took back or confirmed, against the rules
        it contradicts, on the patterns its change carries. It counts for the field of the value that was
        decided on. Returns the rules that stand proposed for this field and would change something, the one
        that reaches furthest first; nothing is applied here."""
        review = entry["review"]
        if review.get("by") == "rule":
            return []
        rules = Rules(self.store.get_rules())
        changed = False
        # a person confirms or takes back what a rule had set
        if earlier and earlier.get("review") and earlier["review"].get("rule"):
            rules.tally(earlier["review"]["rule"], "confirmed" if review["decision"] == "confirmed" else "withdrawn")
            changed = True
        now = self._value_at(entry, path or entry["path"])
        value = None if now is None else str(now)
        before = review.get("before") if review["decision"] == "changed" else value
        if review["decision"] in ("confirmed", "changed") and before is not None:
            changed = rules.speak_against(field, before, value, review["decision"]) or changed
        if review["decision"] == "changed" and "before" in review and value is not None:
            changed = bool(rules.note(field, review["before"], value, key, review.get("by", ""))) or changed
        if changed:
            self.store.put_rules(rules.rows)
        return self._proposals(rules, field)

    def _proposals(self, rules: Rules, field: str | None = None) -> list[dict]:
        out = [{**r, "reach": self._reach(r)} for r in rules.proposed(field)]
        return sorted((r for r in out if r["reach"]["count"]), key=lambda r: -r["reach"]["count"])

    def _reach(self, rule: dict) -> dict:
        """What a rule would change in the store: how many values in how many affairs, with examples. The same
        values _apply_rule changes: of the rule's field, without a review, fitting the rule."""
        count, affairs, examples = 0, set(), []
        for a in self._affairs_with([(rule["field"], lambda v: apply(rule, v) is not None)]):
            for e, _, value, field, label in self._values(a):
                # a rule from before the fields were named carries the label
                if rule["field"] not in (field, label) or e["review"] is not None or value is None:
                    continue
                after = apply(rule, str(value))
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
        for a in self._affairs_with([(rule["field"], lambda v: apply(rule, v) is not None)]):
            record = a["record"]
            touched = False
            for e, path, value, field, label in list(self._values(a)):
                if rule["field"] not in (field, label) or e["review"] is not None or value is None:
                    continue
                after = apply(rule, str(value))
                if after is None:
                    continue
                try:
                    changed = apply_decision(record, e["source"], "changed", "rule", after, path, rule["id"])
                except ValueError:
                    continue
                if self.contract.check(changed):
                    continue
                record = changed
                touched = True
                count += 1
                self._to_row(a, e["source"], path, record)
                done = next(x for x in sources_of(record) if x["source"] == e["source"])
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
        """A person says what a name of a parliament stands for, or with "reset" takes that back."""
        vocabulary = Vocabulary(self.store.get_vocabulary())
        where = (str(body.get("list", "")), str(body.get("body", "")).strip(), str(body.get("name", "")))
        if body.get("reset"):
            row, gone = vocabulary.reset(*where)
            if row is None and gone is None:
                return 404, {"error": "no row a person changed"}
            if row is not None:
                self.store.put_vocabulary([row])
            else:
                self.store.drop_vocabulary([gone])
            return 200, row or {**gone, "removed": True}
        standard = body.get("standard")
        try:
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

    def allowed(self, token: str | None) -> bool:
        return not self.config.admin_token or token == self.config.admin_token

    def run_pdf(self, name: str, data: bytes, model: bool | None) -> tuple[int, dict]:
        try:
            job = self.jobs.submit_pdf(name, data, self._model(model))
        except ValueError as e:
            return 400, {"error": str(e)}
        return 202, self.jobs.get(job.id) or {}

    def run_document(self, doc_id: int, model: bool | None) -> tuple[int, dict]:
        try:
            job = self.jobs.submit_document(doc_id, self._model(model))
        except (ValueError, OSError) as e:
            return 400, {"error": f"OpenParlData: {e}"}
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
                "admin": "token" if self.config.admin_token else "open", "at": stamp()}
