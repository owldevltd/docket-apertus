"""The fields file: built like the data, with the question wherever a value from the document belongs.

An object with "name" and "question" is a field; everything above it is its path. In a list the first entry is
the template; what in it is not a field goes into every new entry as it is (the role, the meta-name). Every
path is held against the contract: where the contract closes a place, the fields file may not provide
anything else there.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from docket.affair.validator import Contract

TASK = "$task"
LEAF = {"name", "question"}


@dataclass
class Field:
    name: str
    path: list[str]
    question: str
    form: str = "text"
    min_words: int | None = None
    max_words: int | None = None
    choice: bool = False
    dynamic: bool = False
    fixed: dict = field(default_factory=dict)
    template: str = ""
    pages: str = "first"
    when: list[str] = field(default_factory=list)
    free: bool = False
    block_text: bool = False
    # what the value serves for beyond its place: the affair's identity (number, place, parliament, date, title)
    role: str = ""


@dataclass
class Fields:
    task: dict
    fields: dict[str, Field]

    def by_role(self) -> dict[str, str]:
        """The field name per role."""
        return {f.role: name for name, f in self.fields.items() if f.role}


def load_fields(path: str | Path, contract: Contract) -> Fields:
    """Reads the fields file and checks every path against the contract; raises on a path the contract
    cannot hold."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if TASK not in data:
        raise ValueError(f"{path}: no fields file, {TASK} is missing")
    task = data.pop(TASK)
    data.pop("schema", None)
    fields: dict[str, Field] = {}
    _walk(data, [], {}, "", fields)
    errors = []
    for f in fields.values():
        open_place = True
        for n in range(len(f.path), 0, -1):
            rule = contract.part(f.path[:n])
            if rule is not None:
                # up to here the contract knows the path; where it closes the place, it must know the next key
                open_place = (
                    n == len(f.path)
                    or rule.get("additionalProperties", True) is not False
                    or contract.part(f.path[:n + 1]) is not None
                )
                break
        if not open_place:
            errors.append(f"{f.name}: {'.'.join(f.path)} is not in the contract")
    if errors:
        raise ValueError("; ".join(errors))
    return Fields(task, fields)


def _walk(node, path: list[str], fixed: dict, template: str, fields: dict[str, Field]) -> None:
    if isinstance(node, dict) and LEAF <= set(node) and isinstance(node["name"], str):
        fields[node["name"]] = Field(
            name=node["name"],
            path=list(path),
            question=node["question"],
            form=node.get("form", "text"),
            min_words=node.get("min-words"),
            max_words=node.get("max-words"),
            choice=bool(node.get("choice", False)),
            dynamic=bool(node.get("dynamic", False)),
            fixed=fixed,
            template=template,
            pages="all" if node.get("pages") == "all" else "first",
            when=list(node.get("when", [])),
            free=bool(node.get("free", False)),
            block_text=bool(node.get("block-text", False)),
            role=str(node.get("role", "")),
        )
        return
    if isinstance(node, list):
        # every template gets an id, so that its fields later go into the same entries
        for i, one in enumerate(node):
            _walk(one, [*path, "[]"], _plain_part(one), ".".join(path) + f"#{i}", fields)
        return
    if isinstance(node, dict):
        for key, child in node.items():
            if isinstance(child, (dict, list)):
                _walk(child, [*path, str(key)], fixed, template, fields)


def _plain_part(template) -> dict:
    """What in a template is not a field: fixed values every entry gets."""
    out: dict = {}
    if not isinstance(template, dict):
        return out
    for key, v in template.items():
        if isinstance(v, dict) and LEAF <= set(v):
            continue
        if isinstance(v, dict):
            inner = _plain_part(v)
            if inner:
                out[key] = inner
        elif not isinstance(v, list):
            out[key] = v
    return out
