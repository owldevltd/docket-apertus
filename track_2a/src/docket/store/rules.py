"""General repair from decisions: a change a person makes carries a pattern, the same pattern on the same field
three times becomes a rule, and an active rule changes every value of that field in the store that fits, each
with a review that names the rule, so every application can be seen and taken back one by one.

Patterns, the first that fits (set by the project lead, 6 October 2026): prefix-off, suffix-off, prefix-on,
suffix-on, digits (a letter read for a digit), spelling (case only); anything else is a single case and does not
count. A rule is active from three changes; a person can switch it off and on by hand. When a rule becomes
inactive nothing is turned back, only nothing new is applied.
"""

from __future__ import annotations

import re

from docket.store.base import stamp

ACTIVE_AT = 3
DIGITS = {"o": "0", "O": "0", "l": "1", "I": "1", "i": "1", "s": "5", "S": "5", "B": "8"}
EXAMPLES = 3


def pattern(before: str, after: str) -> dict | None:
    """The pattern of a change, or None when it is a single case."""
    if before == after or not before or not after:
        return None
    if after == before[len(before) - len(after):] and before.endswith(after):
        return {"kind": "prefix-off", "parameter": before[: len(before) - len(after)]}
    if before.startswith(after):
        return {"kind": "suffix-off", "parameter": before[len(after):]}
    if after.endswith(before):
        return {"kind": "prefix-on", "parameter": after[: len(after) - len(before)]}
    if after.startswith(before):
        return {"kind": "suffix-on", "parameter": after[len(before):]}
    if len(before) == len(after):
        pairs = {}
        for a, b in zip(before, after):
            if a == b:
                continue
            if DIGITS.get(a) != b:
                pairs = None
                break
            pairs[a] = b
        if pairs:
            return {"kind": "digits", "parameter": "".join(f"{a}{b}" for a, b in sorted(pairs.items()))}
    if before.lower() == after.lower():
        return {"kind": "spelling", "parameter": after}
    return None


def apply(rule: dict, value: str) -> str | None:
    """The value after the rule, or None when the rule does not fit it."""
    kind, p = rule["kind"], rule["parameter"]
    if kind == "prefix-off":
        return value[len(p):] if value.startswith(p) and len(value) > len(p) else None
    if kind == "suffix-off":
        return value[: -len(p)] if value.endswith(p) and len(value) > len(p) else None
    if kind == "prefix-on":
        return p + value if not value.startswith(p) else None
    if kind == "suffix-on":
        return value + p if not value.endswith(p) else None
    if kind == "digits":
        pairs = {p[i]: p[i + 1] for i in range(0, len(p) - 1, 2)}
        chars = [pairs[ch] if ch in pairs and _between_digits(value, i) else ch for i, ch in enumerate(value)]
        out = "".join(chars)
        return out if out != value else None
    if kind == "spelling":
        return p if value.lower() == p.lower() and value != p else None
    return None


def _between_digits(value: str, i: int) -> bool:
    """A letter counts as a misread digit only next to digits."""
    left = value[i - 1] if i > 0 else ""
    right = value[i + 1] if i + 1 < len(value) else ""
    return left.isdigit() or right.isdigit()


class Rules:
    """The rules of a store: counting, activation, switching. `rows` is the stored list."""

    def __init__(self, rows: list[dict]):
        self.rows = list(rows)

    def note(self, field: str, before: str, after: str, affair: str, by: str) -> dict | None:
        """Counts a person's change; returns the rule when the change had a pattern, with "activated" when
        this change made it active."""
        p = pattern(before, after)
        if p is None:
            return None
        rule = next((r for r in self.rows if r["field"] == field and r["kind"] == p["kind"]
                     and r["parameter"] == p["parameter"]), None)
        if rule is None:
            rule = {
                "id": f"r-{len(self.rows) + 1:04d}", "field": field, "kind": p["kind"], "parameter": p["parameter"],
                "count": 0, "confirmed": 0, "withdrawn": 0, "applied": 0, "active": False,
                "since": None, "examples": [],
            }
            self.rows.append(rule)
        rule["count"] += 1
        if len(rule["examples"]) < EXAMPLES:
            rule["examples"].append({"affair": affair, "before": before, "after": after, "by": by})
        activated = False
        if not rule["active"] and rule["count"] >= ACTIVE_AT and not rule.get("switched"):
            rule["active"] = True
            rule["since"] = stamp()
            activated = True
        return {**rule, "activated": activated}

    def active(self, field: str) -> list[dict]:
        return [r for r in self.rows if r["active"] and r["field"] == field]

    def get(self, rule_id: str) -> dict | None:
        return next((r for r in self.rows if r["id"] == rule_id), None)

    def switch(self, rule_id: str, active: bool, by: str) -> dict | None:
        rule = self.get(rule_id)
        if rule is None:
            return None
        rule["active"] = bool(active)
        rule["switched"] = {"by": by, "at": stamp(), "active": bool(active)}
        return rule

    def tally(self, rule_id: str, what: str) -> None:
        """A person confirmed or withdrew a value a rule had set."""
        rule = self.get(rule_id)
        if rule is not None and what in ("confirmed", "withdrawn"):
            rule[what] += 1
            rule["applied"] = rule.get("applied", 0)


def shape(value: str) -> str:
    """The pattern of a value for "n further documents with the same error": digits 9, capitals A, small
    letters a, runs shortened to one, separators and spaces stay ("Kanton Zürich" to "A a A a")."""
    t = re.sub(r"\d+", "9", str(value))
    t = re.sub(r"[A-ZÄÖÜ]+", "A", t)
    t = re.sub(r"[a-zäöüß]+", "a", t)
    return re.sub(r"\s+", " ", t).strip()
