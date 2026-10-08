"""What the web server answers with: the affairs and their values with a place, the decisions and what they
set in motion (the general repair), the runs of the admin. One object, shared by the request handlers."""

from __future__ import annotations

import threading

from docket.affair.validator import Contract
from docket.config import Config
from docket.jobs import Jobs
from docket.store.base import Store, stamp
from docket.store.review import apply_decision, counts, sources_of
from docket.store.rules import Rules, apply, shape

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
                "counts": counts(r),
                "updated_at": a.get("updated_at"),
            })
        return sorted(out, key=lambda s: (-s["counts"]["open"], s["key"]))

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
            self._rules_after(key, entry, earlier)
        return 200, self.affair(key) or {}

    def _log(self, key: str, entry: dict) -> None:
        review = entry["review"]
        self.store.add_decision({
            "affair": key, "doc": entry["doc"], "block": entry["block"], "path": entry["path"],
            "label": entry["label"], "how": entry["how"], "approve": entry["approve"],
            "decision": review["decision"], "before": review.get("before"), "after": entry["value"],
            "by": review.get("by"), "at": review["at"], "rule": review.get("rule"),
        })

    def _rules_after(self, key: str, entry: dict, earlier: dict | None) -> None:
        """Counts the change for the general repair, and applies a rule that just became active."""
        rules = Rules(self.store.get_rules())
        review = entry["review"]
        changed = False
        # a person confirms or takes back what a rule had set
        if earlier and earlier.get("review") and earlier["review"].get("rule") and review.get("by") != "rule":
            rules.tally(earlier["review"]["rule"], "confirmed" if review["decision"] == "confirmed" else "withdrawn")
            changed = True
        if review["decision"] == "changed" and review.get("by") != "rule" and "before" in review:
            rule = rules.note(entry["label"], review["before"], str(entry["value"]), key, review.get("by", ""))
            changed = changed or rule is not None
            if rule is not None and rule["activated"]:
                rule["applied"] = rules.get(rule["id"]).get("applied", 0) + self._apply_rule(rules.get(rule["id"]))
                rules.get(rule["id"])["applied"] = rule["applied"]
        if changed:
            self.store.put_rules(rules.rows)

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
        return self.store.get_rules()

    def switch_rule(self, rule_id: str, active: bool, by: str) -> tuple[int, dict]:
        rules = Rules(self.store.get_rules())
        rule = rules.switch(rule_id, active, by)
        if rule is None:
            return 404, {"error": "no such rule"}
        if active:
            rule["applied"] = rule.get("applied", 0) + self._apply_rule(rule)
        self.store.put_rules(rules.rows)
        return 200, rule

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
