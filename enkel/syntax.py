"""Predictive parser for Enkel Core 0.1. No ambiguity resolution heuristics."""
from dataclasses import asdict, dataclass
import re
from .lexicon import ADJECTIVES, NOUNS, ROLES, VERBS

TOKEN = re.compile(r"[A-Za-z0-9_-]+|[.?]")
VERB = re.compile(r"(?P<negative>no-)?(?P<tense>di|du|wi)-(?P<root>[a-z]+)(?P<perfect>-en)?(?P<progressive>-ing)?\Z")
NOUN = re.compile(r"(?P<negative>no-)?(?P<root>[a-z]+)-(?P<det>[aeiou])\Z")
NAME = re.compile(r"re-[A-Z][A-Za-z0-9_]*\Z")
BACKREF = re.compile(r"re(?:-([1-9][0-9]*))?\Z")
MAX_TOKENS = 2048
MAX_DEPTH = 24
MAX_SOURCE = 65536
MAX_NEGATIONS = 128


class EnkelError(ValueError):
    def __init__(self, message, source="", offset=0):
        self.message, self.source, self.offset = message, source, offset
        super().__init__(message)

    def __str__(self):
        if not self.source:
            return self.message
        line = self.source.count("\n", 0, self.offset) + 1
        start = self.source.rfind("\n", 0, self.offset) + 1
        end = self.source.find("\n", self.offset)
        fragment = self.source[start:end if end >= 0 else len(self.source)]
        return f"{self.message} (line {line}, column {self.offset-start+1})\n{fragment}\n{' '*(self.offset-start)}^"


@dataclass(frozen=True)
class VerbForm:
    root: str
    tense: str
    perfect: bool
    progressive: bool
    negative: bool


@dataclass(frozen=True)
class Nominal:
    kind: str
    value: str
    determiner: str = ""
    negative: bool = False
    depth: int = 0
    adjectives: tuple[str, ...] = ()
    relatives: tuple["Clause", ...] = ()
    offset: int = 0


@dataclass(frozen=True)
class Item:
    role: str  # 'ne' is a scope operator, otherwise a role.
    nominal: Nominal | None = None


@dataclass(frozen=True)
class Clause:
    verb: VerbForm
    items: tuple[Item, ...]


@dataclass(frozen=True)
class Sentence:
    mode: str
    query_role: str | None
    clause: Clause

    def to_dict(self):
        return asdict(self)


class Parser:
    def __init__(self, source):
        if not isinstance(source, str):
            raise TypeError("source must be a string")
        self.source, self.tokens, self.i = source, [], 0
        if len(source) > MAX_SOURCE:
            self.fail(f"Sentence exceeds the {MAX_SOURCE}-character implementation limit.", 0)
        end = 0
        for match in TOKEN.finditer(source):
            if len(match.group()) > 128:
                self.fail("A token may contain at most 128 characters.", match.start())
            gap = source[end:match.start()]
            if gap and not gap.isspace():
                self.fail("Unsupported character; Core uses ASCII word tokens, spaces, and final . or ?.", end)
            if self.tokens and match.start() == end and match.group() not in (".", "?"):
                self.fail("Word tokens must be separated by whitespace.", match.start())
            self.tokens.append((match.group(), match.start()))
            end = match.end()
        if source[end:] and not source[end:].isspace():
            self.fail("Unsupported character.", end)
        if len(self.tokens) > MAX_TOKENS:
            self.fail(f"Sentence exceeds the {MAX_TOKENS}-token implementation limit.")
        if sum(token == "ne" for token, _ in self.tokens) > MAX_NEGATIONS:
            self.fail(f"Sentence exceeds the {MAX_NEGATIONS} explicit-negation implementation limit.")

    def fail(self, message, offset=None):
        if offset is None:
            offset = self.tokens[self.i][1] if self.i < len(self.tokens) else len(self.source)
        raise EnkelError(message, self.source, offset)

    def peek(self):
        return self.tokens[self.i][0] if self.i < len(self.tokens) else None

    def take(self):
        value = self.peek()
        if value is None:
            self.fail("Unexpected end of sentence.")
        self.i += 1
        return value

    def parse(self):
        mode, query = "statement", None
        if self.peek() == "ka":
            mode = "yes_no"
            self.take()
        elif self.peek() in {"ka-" + r for r in ROLES}:
            mode, query = "wh", self.take()[3:]
        clause = self.clause(0, query)
        if self.peek() in (".", "?"):
            expected = "." if mode == "statement" else "?"
            if self.peek() != expected:
                self.fail(f"This sentence requires {expected!r} if terminal punctuation is supplied.")
            self.take()
        if self.peek() is not None:
            self.fail("Unexpected token after the sentence.")
        return Sentence(mode, query, clause)

    def clause(self, depth, query=None):
        if depth > MAX_DEPTH:
            self.fail(f"Relative nesting exceeds {MAX_DEPTH}.")
        token = self.peek() or ""
        match = VERB.fullmatch(token)
        if not match:
            self.fail("Expected [no-](di|du|wi)-VERB[-en][-ing]; perfect must precede progressive.")
        if match["root"] not in VERBS:
            self.fail(f"Unknown verb root {match['root']!r}.")
        self.take()
        verb = VerbForm(match["root"], match["tense"], bool(match["perfect"]),
                        bool(match["progressive"]), bool(match["negative"]))
        seen = {query} if query else set()
        items = []
        while self.peek() not in (None, "ek", ".", "?"):
            role = self.peek()
            if role == "ne":
                self.take()
                items.append(Item("ne"))
                continue
            if role not in ROLES:
                self.fail("Expected a role particle or the scope-negation marker ne.")
            if role in seen:
                self.fail(f"Duplicate role {role!r}; a wh prefix already fills its queried role.")
            seen.add(role)
            self.take()
            items.append(Item(role, self.nominal(depth)))
        frame = VERBS[verb.root]
        missing = set(frame.required) - seen
        forbidden = seen - set(frame.permitted)
        if missing:
            self.fail(f"Verb {verb.root!r} is missing required role(s): {', '.join(sorted(missing))}.")
        if forbidden:
            self.fail(f"Verb {verb.root!r} does not permit role(s): {', '.join(sorted(forbidden))}.")
        return Clause(verb, tuple(items))

    def nominal(self, depth):
        token = self.peek() or ""
        offset = self.tokens[self.i][1] if self.i < len(self.tokens) else len(self.source)
        match = NOUN.fullmatch(token)
        if match:
            root, det, negative = match["root"], match["det"], bool(match["negative"])
            if root not in NOUNS:
                self.fail(f"Unknown noun root {root!r}.")
            if negative and det != "a":
                self.fail("Nominal no- is defined only for -a: no-cat-a.")
            if not NOUNS[root].count:
                self.fail("Mass nouns are kind terms in Core 0.1; use the bare root.")
            self.take()
            adjectives, relatives = [], []
            while self.peek() and self.peek().startswith("ma-"):
                adjective = self.peek()[3:]
                if adjective not in ADJECTIVES:
                    self.fail(f"Unknown adjective {adjective!r}.")
                adjectives.append(adjective)
                self.take()
            while self.peek() == "ke":
                self.take()
                relatives.append(self.clause(depth + 1))
                if self.peek() != "ek":
                    self.fail("Unclosed relative clause; expected ek.")
                self.take()
            return Nominal("noun", root, det, negative, adjectives=tuple(adjectives),
                           relatives=tuple(relatives), offset=offset)
        if token in ("me", "yu", "we") or NAME.fullmatch(token):
            self.take()
            return Nominal("reference", token, offset=offset)
        back = BACKREF.fullmatch(token)
        if back:
            self.take()
            level = int(back[1] or 1)
            if level > depth:
                self.fail("Relative reference escapes its enclosing noun heads.", offset)
            return Nominal("bound", "re", depth=level, offset=offset)
        if token in NOUNS:
            self.take()
            return Nominal("kind", token, offset=offset)
        self.fail("Expected a known noun, kind term, declared reference, or relative re.")


def parse(source):
    return Parser(source).parse()


def serialize(sentence):
    def clause_text(clause):
        v = clause.verb
        words = [("no-" if v.negative else "") + v.tense + "-" + v.root
                 + ("-en" if v.perfect else "") + ("-ing" if v.progressive else "")]
        for item in clause.items:
            words.append(item.role)
            n = item.nominal
            if n is None:
                continue
            if n.kind == "noun":
                words.append(("no-" if n.negative else "") + n.value + "-" + n.determiner)
                words.extend("ma-" + a for a in n.adjectives)
                for relative in n.relatives:
                    words.extend(("ke", clause_text(relative), "ek"))
            elif n.kind == "bound":
                words.append("re" if n.depth == 1 else f"re-{n.depth}")
            else:
                words.append(n.value)
        return " ".join(words)
    prefix = "ka " if sentence.mode == "yes_no" else f"ka-{sentence.query_role} " if sentence.mode == "wh" else ""
    return prefix + clause_text(sentence.clause)
