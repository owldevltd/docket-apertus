"""The fields file: built like the data, with the question wherever a value from the document belongs.

An object with "name" and "question" is a field; everything above it is its path. In a list the first entry is
the template; what in it is not a field goes into every new entry as it is (the role, the meta-name). Every
path is held against the contract: where the contract closes a place, the fields file may not provide
anything else there. Beside its place a field says what its value is (the entity: a person, a date, an
identifier), so that the same value is known as the same thing in whatever JSON it is placed. Fields that name
the same word under "together" are asked in one call of their own: each of them needs to see what the others take
(who submitted, who co-signed, in whose name), and asked apart the model gives the same names to each. A list
field that names another field under "paired" is asked for both in one line, entry by entry (an event: its day,
then what happened); asked as two lists the model has to keep in step, the entries did not belong together. A
field with "reader" is read by code and not asked: asked for the place, the model named one in documents that
print none. A field with "apart" leaves out a value that already stands under one of the fields named there: a
party is not the body the document is addressed to, and not the group that submitted it once more. A field with
"entry" gives its value to a list as well: the day an affair was submitted is its first event. Beside the
fields the task holds questions about the document itself ("ask"): what the document is in its affair, one word
out of a closed list. Such an answer is no value of the record and stands on no page; it is held against what
the code finds by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

from docket.affair.validator import Contract
from docket.config import ROOT

TASK = "$task"
LEAF = {"name", "question"}
# what a value can be, whatever JSON it goes into, and what stands behind each to hold a value against: data,
# so that a new entity is an entry and not code
ENTITIES = ROOT / "data" / "knowledge" / "entities.json"


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
    # fields with the same word here share a call of their own
    together: str = ""
    # the field whose value starts every entry of this one's answer (the day of an event); that field has no
    # line of its own then
    paired: str = ""
    # the way code reads this field from the pages itself; the model is not asked for it then
    reader: str = ""
    # fields whose values are not this field's: what already stands under one of them is left out here
    apart: list[str] = field(default_factory=list)
    # the day of this field is an entry of a list as well: {"of": the list field, "label": its name per language}
    entry: dict = field(default_factory=dict)
    when: list[str] = field(default_factory=list)
    free: bool = False
    block_text: bool = False
    # the value is in the language of the document and stands under that language's key, not under the one
    # the fields file happens to name ("abstract.fr" for a French document)
    own_language: bool = False
    # what the value is, one of the entities: lookups, learning and questions over documents go by it, not by
    # the key the target JSON happens to use
    entity: str = "text"
    # what stands behind the entity to hold the value against (bodies, vocabulary, register, or nothing), and
    # for the vocabulary the list
    lookup: str = ""
    list_name: str = ""
    # the word under the entity that tells which of several it is (the affair's own number, the author); the
    # affair's identity takes number, place, parliament, date and title by it
    role: str = ""
    # where what a lookup finds for the value goes: the path of the standard name from the root (a category
    # through the vocabulary), and the key of the id beside the value in its entry (a person in the register)
    standard: str = ""
    id_key: str = ""


@dataclass
class Fields:
    task: dict
    fields: dict[str, Field]
    # the entities the fields were held against, by name
    entities: dict[str, dict] = field(default_factory=dict)

    def by_role(self) -> dict[str, str]:
        """The field name per role."""
        return {f.role: name for name, f in self.fields.items() if f.role}


def definition_of(fields: Fields) -> dict:
    """What a document is asked under a fields file: the names of the fields, and a mark that changes when a
    question changes or what is checked of its answer. A document keeps it with its answers, so that it can
    be told later what it was never asked."""
    asked = {name: [f.question, f.form, f.min_words, f.max_words, f.choice, f.pages, f.when, f.free, f.block_text]
             for name, f in sorted(fields.fields.items())}
    mark = hashlib.sha1(json.dumps(asked, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return {"version": mark, "fields": sorted(asked)}


def load_entities(path: str | Path | None = None) -> dict[str, dict]:
    """The entities by name, from the file that lists them (the one of this checkout when none is given)."""
    data = json.loads(Path(path or ENTITIES).read_text(encoding="utf-8"))
    return {str(e["name"]): e for e in data["entities"]}


def load_fields(path: str | Path, contract: Contract, entities: dict[str, dict] | None = None) -> Fields:
    """Reads the fields file and checks every path against the contract and every entity against the
    entities; raises on a path the contract cannot hold and on an entity nobody listed."""
    entities = entities if entities is not None else load_entities()
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if TASK not in data:
        raise ValueError(f"{path}: no fields file, {TASK} is missing")
    task = data.pop(TASK)
    data.pop("schema", None)
    fields: dict[str, Field] = {}
    _walk(data, [], {}, "", fields)
    errors = []
    for f in fields.values():
        if not has_room(contract, f.path):
            errors.append(f"{f.name}: {'.'.join(f.path)} is not in the contract")
        if f.entity not in entities:
            errors.append(f"{f.name}: {f.entity} is no entity ({', '.join(entities)})")
        else:
            f.lookup = str(entities[f.entity].get("lookup") or "")
            f.list_name = str(entities[f.entity].get("list") or "")
        if f.standard and not has_room(contract, f.standard.split(".")):
            errors.append(f"{f.name}: the standard name at {f.standard} is not in the contract")
        if f.id_key and not has_room(contract, [*f.path[:-1], f.id_key]):
            errors.append(f"{f.name}: the id at {'.'.join([*f.path[:-1], f.id_key])} is not in the contract")
    if errors:
        raise ValueError("; ".join(errors))
    return Fields(task, fields, entities)


def has_room(contract: Contract, path: list[str]) -> bool:
    """Whether the contract can hold a value at this path."""
    for n in range(len(path), -1, -1):
        rule = contract.part(path[:n])
        if rule is not None:
            # up to here the contract knows the path; where it closes the place, it must know the next key
            return (
                n == len(path)
                or rule.get("additionalProperties", True) is not False
                or contract.part(path[:n + 1]) is not None
            )
    return True


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
            together=str(node.get("together", "")),
            paired=str(node.get("paired", "")),
            reader=str(node.get("reader", "")),
            apart=list(node.get("apart", [])),
            entry=dict(node.get("entry", {})),
            when=list(node.get("when", [])),
            free=bool(node.get("free", False)),
            block_text=bool(node.get("block-text", False)),
            own_language=bool(node.get("own-language", False)),
            entity=str(node.get("entity", "text")),
            role=str(node.get("role", "")),
            standard=str(node.get("standard", "")),
            id_key=str(node.get("id", "")),
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
