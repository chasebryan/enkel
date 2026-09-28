"""Explicit discourse identities. Display names are never lookup keys."""
import hashlib
import json
import re
from dataclasses import dataclass

ID = re.compile(r"[A-Z][A-Za-z0-9_]*\Z")


class ContextError(ValueError):
    pass


@dataclass(frozen=True)
class Entity:
    label: str
    number: str
    members: tuple[str, ...] = ()


class Context:
    def __init__(self, data=None):
        data = {} if data is None else data
        if not isinstance(data, dict) or set(data) - {"entities", "speaker", "addressee", "group"}:
            raise ContextError("Context must contain only entities, speaker, addressee, and group.")
        raw = data.get("entities", {})
        if not isinstance(raw, dict):
            raise ContextError("entities must be an object keyed by explicit IDs.")
        self.entities = {}
        for ident, value in raw.items():
            if not isinstance(ident, str) or not ID.fullmatch(ident):
                raise ContextError(f"Invalid entity ID: {ident!r}.")
            if not isinstance(value, dict) or set(value) - {"label", "number", "members"}:
                raise ContextError(f"Invalid entity declaration: {ident}.")
            label = value.get("label")
            number = value.get("number", "singular")
            members = value.get("members", [])
            if not isinstance(label, str) or not label.strip() or len(label) > 120:
                raise ContextError(f"{ident} needs a nonempty label of at most 120 characters.")
            if number not in ("singular", "plural"):
                raise ContextError(f"{ident}: number must be singular or plural.")
            if not isinstance(members, list) or any(not isinstance(x, str) for x in members):
                raise ContextError(f"{ident}: members must be a list of IDs.")
            if len(set(members)) != len(members):
                raise ContextError(f"{ident}: group members must be distinct.")
            if (number == "singular" and members) or (number == "plural" and len(members) < 2):
                raise ContextError(f"{ident}: a plurality needs at least two members; a singular has none.")
            self.entities[ident] = Entity(label, number, tuple(sorted(members)))
        for ident, entity in self.entities.items():
            for member in entity.members:
                if member not in self.entities or self.entities[member].number != "singular":
                    raise ContextError(f"{ident}: member {member!r} must name a declared singular entity.")
        self.bindings = {}
        for key in ("speaker", "addressee", "group"):
            if key in data:
                ident = data[key]
                if not isinstance(ident, str) or ident not in self.entities:
                    raise ContextError(f"{key} must name a declared entity.")
                self.bindings[key] = ident
        if "speaker" in self.bindings and self.entities[self.bindings["speaker"]].number != "singular":
            raise ContextError("speaker must be singular.")
        if "group" in self.bindings:
            group = self.entities[self.bindings["group"]]
            speaker = self.bindings.get("speaker")
            if group.number != "plural" or speaker not in group.members:
                raise ContextError("group must be plural and explicitly include speaker.")

    def resolve(self, spelling):
        key = {"me": "speaker", "yu": "addressee", "we": "group"}.get(spelling)
        ident = self.bindings.get(key) if key else spelling[3:]
        if ident not in self.entities:
            raise ContextError(f"Unresolved reference {spelling!r}; declare its exact ID or pronoun binding.")
        entity = self.entities[ident]
        return {"type": "reference", "id": ident, "label": entity.label,
                "number": entity.number, "person": 1 if spelling in ("me", "we") else 2 if spelling == "yu" else 3,
                "pronoun": spelling if key else None}

    def to_dict(self):
        return {"entities": {k: {"label": v.label, "number": v.number, "members": list(v.members)}
                             for k, v in sorted(self.entities.items())}, **self.bindings}

    def digest(self):
        data = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(data.encode()).hexdigest()
