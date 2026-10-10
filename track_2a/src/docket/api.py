"""What the web server answers with: the affairs and their values with a place, the decisions and what they
set in motion (a rule proposed, a rule applied), the vocabulary, the runs of the admin. One object, shared by
the request handlers."""

from __future__ import annotations

import json
import threading

from docket.affair.validator import Contract
from docket.config import Config
from docket.jobs import Jobs
from docket.store.base import Store, stamp
from docket.store.review import apply_decision, counts, sources_of
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

    def lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self.locks.setdefault(key, threading.Lock())

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
            out.append({
                "key": a["key"],
                "number": r.get("number"),
                "title": (r.get("title") or {}).get("de"),
                "type": (r.get("type_harmonized") or {}).get("de") or (r.get("type_name") or {}).get("de"),
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

    def _same(self, key: str, sources: list[dict]) -> None:
        """For every open value: how many values of the same field, found the same way, with the same shape
        stand in the other affairs ("n further documents with the same error")."""
        others = []
        for a in self.store.list_affairs():
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
            self.store.save_record(key, record)
            entry = next(e for e in sources_of(record) if e["source"] == source_path)
            self._log(key, entry)
            proposals = self._rules_after(key, entry, earlier)
        return 200, {**(self.affair(key) or {}), "proposals": proposals}

    def _log(self, key: str, entry: dict) -> None:
        review = entry["review"]
        self.store.add_decision({
            "affair": key, "doc": entry["doc"], "block": entry["block"], "path": entry["path"],
            "label": entry["label"], "how": entry["how"], "approve": entry["approve"],
            "decision": review["decision"], "before": review.get("before"), "after": entry["value"],
            "by": review.get("by"), "at": review["at"], "rule": review.get("rule"),
        })

    def _rules_after(self, key: str, entry: dict, earlier: dict | None) -> list[dict]:
        """Counts a decision by hand for the learning: on the rule it took back or confirmed, against the rules
        it contradicts, on the patterns its change carries. Returns the rules that stand proposed for this
        field and would change something, the one that reaches furthest first; nothing is applied here."""
        review = entry["review"]
        if review.get("by") == "rule":
            return []
        rules = Rules(self.store.get_rules())
        changed = False
        # a person confirms or takes back what a rule had set
        if earlier and earlier.get("review") and earlier["review"].get("rule"):
            rules.tally(earlier["review"]["rule"], "confirmed" if review["decision"] == "confirmed" else "withdrawn")
            changed = True
        value = None if entry["value"] is None else str(entry["value"])
        before = review.get("before") if review["decision"] == "changed" else value
        if review["decision"] in ("confirmed", "changed") and before is not None:
            changed = rules.speak_against(entry["label"], before, value, review["decision"]) or changed
        if review["decision"] == "changed" and "before" in review and value is not None:
            changed = bool(rules.note(entry["label"], review["before"], value, key, review.get("by", ""))) or changed
        if changed:
            self.store.put_rules(rules.rows)
        return self._proposals(rules, entry["label"])

    def _proposals(self, rules: Rules, field: str | None = None) -> list[dict]:
        out = [{**r, "reach": self._reach(r)} for r in rules.proposed(field)]
        return sorted((r for r in out if r["reach"]["count"]), key=lambda r: -r["reach"]["count"])

    def _reach(self, rule: dict) -> dict:
        """What a rule would change in the store: how many values in how many affairs, with examples. The same
        values _apply_rule changes: of the rule's field, without a review, fitting the rule."""
        count, affairs, examples = 0, set(), []
        for a in self.store.list_affairs():
            for e in sources_of(a["record"]):
                if e["label"] != rule["field"] or e["review"] is not None or e["value"] is None:
                    continue
                after = apply(rule, str(e["value"]))
                if after is None:
                    continue
                count += 1
                affairs.add(a["key"])
                if len(examples) < SAME_EXAMPLES:
                    examples.append({"key": a["key"], "before": str(e["value"]), "after": after})
        return {"count": count, "affairs": len(affairs), "examples": examples}

    def _apply_rule(self, rule: dict) -> int:
        """Changes every value of the rule's field in the store that fits and has no review yet; returns the
        count. Every change carries a review by "rule" with the rule's id."""
        count = 0
        for a in self.store.list_affairs():
            record = a["record"]
            touched = False
            for e in sources_of(record):
                if e["label"] != rule["field"] or e["review"] is not None or e["value"] is None:
                    continue
                after = apply(rule, str(e["value"]))
                if after is None:
                    continue
                try:
                    record = apply_decision(record, e["source"], "changed", "rule", after, e["path"], rule["id"])
                except ValueError:
                    continue
                if self.contract.check(record):
                    continue
                touched = True
                count += 1
                done = next(x for x in sources_of(record) if x["source"] == e["source"])
                self._log(a["key"], done)
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

    def _model(self, model: bool | None) -> bool:
        return bool(self.config.api_key) if model is None else bool(model) and bool(self.config.api_key)

    def health(self) -> dict:
        return {"ok": True, "store": self.store.kind, "model": bool(self.config.api_key),
                "admin": "token" if self.config.admin_token else "open", "at": stamp()}
