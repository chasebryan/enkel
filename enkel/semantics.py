"""Compile surface order into an explicitly scoped, JSON-safe meaning tree."""
from .context import Context, ContextError
from .lexicon import ROLES
from .syntax import EnkelError

QUANTIFIERS = {"a": "exists", "e": "definite", "i": "exists_plural",
               "o": "definite_plural", "u": "every"}


class Lowerer:
    def __init__(self, context, source):
        self.context, self.source, self.counter = context, source, 0

    def variable(self, number):
        self.counter += 1
        return {"type": "variable", "name": f"x{self.counter}", "number": number, "person": 3}

    def clause(self, clause, stack=(), question=None):
        roles, operators = {}, []
        if question:
            role, term = question
            roles[role] = term
        for item in clause.items:
            if item.role == "ne":
                operators.append(("not", None))
                continue
            n = item.nominal
            if n.kind == "noun":
                number = "plural" if n.determiner in ("i", "o") else "singular"
                term = self.variable(number)
                relatives = []
                for relative in n.relatives:
                    body = self.clause(relative, stack + (term,))
                    if not mentions(body, term["name"]):
                        raise EnkelError("A relative clause must use its own head (re, or an explicit outer reference inside a nested relative).", self.source, n.offset)
                    relatives.append(body)
                restriction = {"noun": n.value, "adjectives": list(n.adjectives), "relatives": relatives}
                if n.negative:
                    operators.append(("not", None))
                operators.append(("bind", {"quantifier": QUANTIFIERS[n.determiner],
                                           "variable": term, "restriction": restriction}))
            elif n.kind == "reference":
                try:
                    term = self.context.resolve(n.value)
                except ContextError as error:
                    raise EnkelError(str(error), self.source, n.offset) from error
            elif n.kind == "bound":
                term = stack[-n.depth]
            else:
                term = {"type": "kind", "noun": n.value, "number": "singular", "person": 3}
            roles[item.role] = term
        v = clause.verb
        body = {"type": "predicate", "verb": {"root": v.root, "tense": v.tense,
                "perfect": v.perfect, "progressive": v.progressive},
                "roles": {role: roles[role] for role in ROLES if role in roles}}
        if v.negative:
            body = {"type": "not", "body": body}
        for kind, operator in reversed(operators):
            body = {"type": kind, **(operator or {}), "body": body}
        return body

    def sentence(self, sentence):
        question = None
        result = {"type": sentence.mode}
        if sentence.mode == "wh":
            variable = {"type": "variable", "name": "q0", "number": "singular", "person": 3}
            result.update(role=sentence.query_role, variable=variable)
            question = (sentence.query_role, variable)
        result["body"] = self.clause(sentence.clause, question=question)
        return result


def mentions(value, name):
    if isinstance(value, dict):
        if value.get("type") == "variable" and value.get("name") == name:
            return True
        return any(mentions(v, name) for k, v in value.items() if k != "variable")
    if isinstance(value, list):
        return any(mentions(v, name) for v in value)
    return False


def lower(sentence, context=None, source=""):
    return Lowerer(context or Context(), source).sentence(sentence)
