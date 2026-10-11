"""Learning from decisions: a change a person makes carries a pattern. When two changes by hand carry the same
pattern on the same field, the rule is proposed: the app says how many further values it fits and asks whether
they should be set right too. A person answers yes or no. Only an accepted rule changes values, each with a
review that names the rule, so every application can be seen and taken back one by one.

A rule a decision by hand speaks against is not proposed: a person kept a value the rule would change, or
changed it into something else. Played through on 10 October 2026 with 200 corrections on 60 documents: without
this check 54 right proposals came with 44 wrong ones, with it 50 with 3.

Patterns, every one that fits a change (the first six set by the project lead, 6 October 2026): prefix-off,
suffix-off, prefix-on, suffix-on, digits (a letter read for a digit), spelling (case only); and value: the same
value becomes the same value ("Standesinitiative" to "Antrag"), whatever else the change is. A person can
switch an accepted rule off and on by hand. When a rule stops being active nothing is turned back, only nothing
new is applied.

And label (11 October 2026): the value a person set stands in the document beside a printed label ("Vorstoss-
Nr.: M 185"), or is the label of a ticked box. Such a rule reads: the value of this field is what stands at
that label. Which label belongs to which field is written nowhere in the code; it is learnt from what people
correct, like every other rule. Unlike the others it does not turn one value into another by its form, it
needs the document: `labelled` is what the document prints with a label (see labels).
"""

from __future__ import annotations

import re

from docket.fields.placer import day, plain
from docket.store.base import stamp

# a rule is proposed from this many changes by hand
PROPOSE_AT = 2
DIGITS = {"o": "0", "O": "0", "l": "1", "I": "1", "i": "1", "s": "5", "S": "5", "B": "8"}
EXAMPLES = 3
# how a ticked box and an empty one stand in a text layer
TICKED = ("☒", "☑", "x", "X")
UNTICKED = ("☐", "□", "")


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


def label_key(term: str) -> str:
    """A printed label as it is compared: small letters, single spaces, without its colon."""
    return re.sub(r"\s+", " ", str(term or "").strip().rstrip(":").strip().lower())


def labels(blocks: list[dict]) -> dict[str, str]:
    """What a document prints with a label, by the label: the text beside it; for a ticked box the label
    itself, since the tick says that the label holds. A box left empty tells nothing, and of a label printed
    twice the first counts. `blocks` are the blocks of a document, the ones inside sections too."""
    out: dict[str, str] = {}
    for block in blocks:
        for item in block.get("items") or []:
            if not isinstance(item, dict) or not item.get("term"):
                continue
            key, value = label_key(item["term"]), " ".join(str(item.get("def") or "").split())
            if value in TICKED:
                value = str(item["term"]).strip().rstrip(":").strip()
            elif value in UNTICKED:
                continue
            if key and key not in out:
                out[key] = value
    return out


def _same(a: str, b: str) -> bool:
    """Whether two values say the same: the same day, or the same letters and digits."""
    return bool(plain(a)) and (plain(a) == plain(b) or (day(a) != "" and day(a) == day(b)))


def patterns(before: str, after: str, labelled: dict[str, str] | None = None) -> list[dict]:
    """Every pattern a change carries: the one of its form, when it has one, the value itself, and every
    label of the document beside which the new value stands."""
    if before == after or not before or not after:
        return []
    found = pattern(before, after)
    out = [found] if found else []
    # a change of spelling is the same value already; anything else also counts as this value becoming that one
    if found is None or found["kind"] != "spelling":
        out.append({"kind": "value", "parameter": before, "to": after})
    out += [{"kind": "label", "parameter": key} for key, value in (labelled or {}).items() if _same(value, after)]
    return out


def apply(rule: dict, value: str, labelled: dict[str, str] | None = None) -> str | None:
    """The value after the rule, or None when the rule does not fit it. A rule of a label fits where the
    document prints that label with another value than this one."""
    kind, p = rule["kind"], rule["parameter"]
    if kind == "label":
        told = (labelled or {}).get(p)
        if not told or _same(told, value):
            return None
        # a date stands in a record as its day, however it is printed
        return day(told) if day(value) and day(told) else told
    if kind == "value":
        return rule.get("to") if value == p and rule.get("to") not in (None, value) else None
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


def state_of(rule: dict) -> str:
    """Where a rule stands: counting (one change so far), proposed, active, declined (a person said no),
    contradicted (a decision by hand speaks against it), off (switched off by hand)."""
    if rule.get("active"):
        return "active"
    if rule.get("switched") and not rule["switched"].get("active"):
        return "off"
    if rule.get("answer") and not rule["answer"].get("accept"):
        return "declined"
    if rule.get("against"):
        return "contradicted"
    return "proposed" if rule.get("count", 0) >= PROPOSE_AT else "counting"


class Rules:
    """The rules of a store: counting, proposing, answering, switching. `rows` is the stored list."""

    def __init__(self, rows: list[dict]):
        self.rows = list(rows)

    def note(self, field: str, before: str, after: str, affair: str, by: str,
             labelled: dict[str, str] | None = None) -> list[dict]:
        """Counts a person's change on every pattern it carries; returns the rules it counted on. `labelled`
        is what the document of the value prints with a label."""
        counted = []
        for p in patterns(before, after, labelled):
            rule = next((r for r in self.rows if r["field"] == field and r["kind"] == p["kind"]
                         and r["parameter"] == p["parameter"] and r.get("to") == p.get("to")), None)
            if rule is None:
                rule = {
                    "id": f"r-{len(self.rows) + 1:04d}", "field": field, "kind": p["kind"],
                    "parameter": p["parameter"], "count": 0, "against": 0, "confirmed": 0, "withdrawn": 0,
                    "applied": 0, "active": False, "state": "counting", "since": None, "examples": [],
                }
                if "to" in p:
                    rule["to"] = p["to"]
                self.rows.append(rule)
            rule["count"] += 1
            if len(rule["examples"]) < EXAMPLES:
                rule["examples"].append({"affair": affair, "before": before, "after": after, "by": by})
            rule["state"] = state_of(rule)
            counted.append(rule)
        return counted

    def speak_against(self, field: str, before: str, after: str | None, decision: str,
                      labelled: dict[str, str] | None = None) -> bool:
        """A decision by hand held against the rules of its field that are not active yet: a person confirmed
        a value a rule would change, or changed it into something else than the rule would. Such a rule is
        not proposed. Returns whether a rule was touched."""
        touched = False
        for rule in self.rows:
            if rule["field"] != field or rule.get("active"):
                continue
            would = apply(rule, before, labelled)
            if would is None:
                continue
            if decision == "confirmed" or (decision == "changed" and not _same(str(after), would)):
                rule["against"] = rule.get("against", 0) + 1
                rule["state"] = state_of(rule)
                touched = True
        return touched

    def proposed(self, field: str | None = None) -> list[dict]:
        return [r for r in self.rows if state_of(r) == "proposed" and (field is None or r["field"] == field)]

    def answer(self, rule_id: str, accept: bool, by: str) -> dict | None:
        """A person's answer to a proposed rule: yes makes it active, no keeps it from being proposed again.
        None when there is no such rule; ValueError when the rule is not proposed."""
        rule = self.get(rule_id)
        if rule is None:
            return None
        if state_of(rule) != "proposed":
            raise ValueError(f"the rule is {state_of(rule)}, not proposed")
        rule["answer"] = {"by": by, "at": stamp(), "accept": bool(accept)}
        if accept:
            rule["active"] = True
            rule["since"] = stamp()
        rule["state"] = state_of(rule)
        return rule

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
        if active and not rule.get("since"):
            rule["since"] = stamp()
        rule["state"] = state_of(rule)
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
