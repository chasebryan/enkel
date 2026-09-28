"""One canonical controlled-English output; no scope-changing stylistic pass."""
import json
from .lexicon import NOUNS, ROLES, VERBS


def term_text(term, subject=False):
    kind = term["type"]
    if kind == "variable":
        return "[" + term["name"] + "]"
    if kind == "kind":
        return 'the kind ' + json.dumps(term["noun"], ensure_ascii=True)
    pronoun = term.get("pronoun")
    if pronoun:
        label = {"me": "I" if subject else "me", "yu": "you", "we": "we" if subject else "us"}[pronoun]
    else:
        label = json.dumps(term["label"], ensure_ascii=True)
    return label + " [@" + term["id"] + "]"


def verb_text(verb, subject):
    forms = VERBS[verb["root"]]
    tense, perfect, progressive = verb["tense"], verb["perfect"], verb["progressive"]
    third_singular = subject["number"] == "singular" and subject["person"] == 3
    if perfect:
        auxiliary = "will have" if tense == "wi" else "had" if tense == "di" else "has" if third_singular else "have"
        return auxiliary + (" been " + forms.progressive if progressive else " " + forms.participle)
    if progressive:
        if tense == "wi":
            auxiliary = "will be"
        elif tense == "di":
            auxiliary = "was" if subject["number"] == "singular" and subject["person"] != 2 else "were"
        else:
            auxiliary = "is" if third_singular else "am" if subject["number"] == "singular" and subject["person"] == 1 else "are"
        return auxiliary + " " + forms.progressive
    return "will " + verb["root"] if tense == "wi" else forms.past if tense == "di" else forms.third if third_singular else verb["root"]


def body_text(node):
    kind = node["type"]
    if kind == "not":
        return "it is not the case that (" + body_text(node["body"]) + ")"
    if kind == "predicate":
        roles = node["roles"]
        words = term_text(roles["se"], True) + " " + verb_text(node["verb"], roles["se"])
        if "ob" in roles:
            words += " " + term_text(roles["ob"])
        for role, phrase in (("to", ", with recipient "), ("vi", ", using instrument "),
                             ("at", ", at place "), ("on", ", at time ")):
            if role in roles:
                words += phrase + term_text(roles[role])
        return words
    if kind != "bind":
        raise ValueError(f"Unknown meaning node: {kind}")
    restriction, variable = node["restriction"], term_text(node["variable"])
    noun = NOUNS[restriction["noun"]]
    q = node["quantifier"]
    plural = q in ("exists_plural", "definite_plural")
    description = " ".join(restriction["adjectives"] + [noun.plural if plural else noun.singular])
    relative = ""
    if restriction["relatives"]:
        relative = " satisfying " + " and ".join("(" + body_text(r) + ")" for r in restriction["relatives"])
    if q == "exists":
        # All initial sounds in the closed adjective/noun vocabulary follow this rule.
        article = "an" if description[0] in "aeiou" or description.startswith("hour") else "a"
        frame = f"there is {article} {description} {variable}{relative} such that"
    elif q == "every":
        frame = f"for every {description} {variable}{relative},"
    elif q == "definite":
        frame = f"for the unique {description} {variable}{relative},"
    elif q == "exists_plural":
        frame = f"there are at least two {description}, collectively designated {variable}{relative}, such that"
    else:
        frame = f"for the maximal plurality {variable} of at least two {description}{relative},"
    return frame + " (" + body_text(node["body"]) + ")"


def render(tree):
    body = body_text(tree["body"])
    if tree["type"] == "yes_no":
        return "Is it the case that (" + body + ")?"
    if tree["type"] == "wh":
        role = {"se": "subject", "ob": "object", "to": "recipient", "vi": "instrument", "at": "place", "on": "time"}[tree["role"]]
        return f"Which {role} [q0] makes the following true: ({body})?"
    return body[0].upper() + body[1:] + "."


def logic(tree):
    def term(t):
        return t["name"] if t["type"] == "variable" else "@" + t["id"] if t["type"] == "reference" else "kind(" + t["noun"] + ")"
    def visit(n):
        if n["type"] == "not":
            return "NOT(" + visit(n["body"]) + ")"
        if n["type"] == "bind":
            r = n["restriction"]
            restrict = r["noun"] + "".join(" & " + a for a in r["adjectives"])
            restrict += "".join(" & (" + visit(v) + ")" for v in r["relatives"])
            return f"{n['quantifier'].upper()} {term(n['variable'])}:({restrict}). ({visit(n['body'])})"
        v = n["verb"]
        tag = v["tense"] + "-" + v["root"] + ("-en" if v["perfect"] else "") + ("-ing" if v["progressive"] else "")
        return tag + "(" + ", ".join(role + "=" + term(n["roles"][role]) for role in ROLES if role in n["roles"]) + ")"
    answer = visit(tree["body"])
    return "ASK(" + answer + ")" if tree["type"] == "yes_no" else f"SELECT q0 AS {tree['role']}. ({answer})" if tree["type"] == "wh" else answer
