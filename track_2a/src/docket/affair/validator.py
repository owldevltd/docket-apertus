"""A validator for the contract, without a library: exactly the keywords of JSON Schema the contract uses.

type, const, enum, required, properties, additionalProperties, items, oneOf and $ref are checked; $schema,
$defs, title, description and dynamic are notes. A schema that uses any other keyword is refused, so nothing
is silently left unchecked. In a oneOf, a variant that already fails at a fixed value (the block's type) is
taken as not meant, so the message names the meant block instead of "fits no variant".
"""

from __future__ import annotations

import json
from pathlib import Path

CHECKS = {"type", "const", "enum", "required", "properties", "additionalProperties", "items", "oneOf", "$ref"}
NOTES = {"$schema", "$defs", "title", "description", "dynamic"}

TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


class Contract:
    def __init__(self, schema: dict):
        self.schema = schema
        unknown = sorted(self._unknown(schema, "#"))
        if unknown:
            raise ValueError("the contract uses keywords this validator does not check: " + ", ".join(unknown))

    @classmethod
    def load(cls, path: str | Path) -> "Contract":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def check(self, data) -> list[str]:
        """The violations of the data against the contract, each with its path; empty when it fits."""
        return self._check(data, self.schema, "$")

    def _unknown(self, s, at: str) -> set[str]:
        out = set()
        if not isinstance(s, dict):
            return out
        for word, inner in s.items():
            if word in NOTES or word in CHECKS:
                if word == "properties" and isinstance(inner, dict):
                    for key, rule in inner.items():
                        out |= self._unknown(rule, f"{at}/properties/{key}")
                elif word in ("items", "additionalProperties"):
                    out |= self._unknown(inner, f"{at}/{word}")
                elif word == "oneOf":
                    for i, rule in enumerate(inner):
                        out |= self._unknown(rule, f"{at}/oneOf/{i}")
                elif word == "$defs":
                    for key, rule in inner.items():
                        out |= self._unknown(rule, f"{at}/$defs/{key}")
                elif word == "$ref" and not self._resolve(inner):
                    out.add(f"$ref {inner} leads nowhere")
            else:
                out.add(f"{word} at {at}")
        return out

    def _resolve(self, ref: str) -> dict | None:
        if not ref.startswith("#/"):
            return None
        node = self.schema
        for part in ref[2:].split("/"):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node if isinstance(node, dict) else None

    def _check(self, v, s: dict, path: str) -> list[str]:
        errors: list[str] = []
        if "$ref" in s:
            target = self._resolve(s["$ref"])
            return self._check(v, target, path) if target else [f"{path}: $ref {s['$ref']} leads nowhere"]
        if "type" in s:
            allowed = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(TYPES[t](v) for t in allowed):
                return [f"{path}: expected {' or '.join(allowed)}, got {type(v).__name__}"]
        if "const" in s and v != s["const"]:
            errors.append(f"{path}: expected {s['const']!r}, got {v!r}")
        if "enum" in s and v not in s["enum"]:
            errors.append(f"{path}: {v!r} is not one of {s['enum']}")
        if "oneOf" in s:
            errors.extend(self._one(v, s["oneOf"], path))
        if isinstance(v, dict):
            for key in s.get("required", []):
                if key not in v:
                    errors.append(f"{path}.{key}: missing")
            props = s.get("properties", {})
            for key, value in v.items():
                if key in props:
                    errors.extend(self._check(value, props[key], f"{path}.{key}"))
                elif s.get("additionalProperties") is False:
                    errors.append(f"{path}.{key}: not in the contract")
                elif isinstance(s.get("additionalProperties"), dict):
                    errors.extend(self._check(value, s["additionalProperties"], f"{path}.{key}"))
        if isinstance(v, list) and isinstance(s.get("items"), dict):
            for i, item in enumerate(v):
                errors.extend(self._check(item, s["items"], f"{path}[{i}]"))
        return errors

    def _one(self, v, variants: list[dict], path: str) -> list[str]:
        """Exactly one variant must fit. A variant that fails at a const (the block's type) is not meant."""
        meant = []
        for rule in variants:
            target = self._resolve(rule["$ref"]) if "$ref" in rule else rule
            if target is None:
                continue
            properties = target.get("properties", {}).items()
            fixed = {k: r["const"] for k, r in properties if isinstance(r, dict) and "const" in r}
            if isinstance(v, dict) and any(k in v and v[k] != c for k, c in fixed.items()):
                continue
            meant.append(target)
        if not meant:
            return [f"{path}: fits no variant"]
        fitting = [rule for rule in meant if not self._check(v, rule, path)]
        if len(fitting) == 1:
            return []
        if not fitting:
            return self._check(v, meant[0], path)
        return [f"{path}: fits {len(fitting)} variants"]
