"""A bounded English front end that emits and validates real Enkel Core.

English recognition is separate from Core parsing. No word-replacement fallback
accepts a sentence this grammar cannot analyze. Known ambiguities need a choice.
"""
from dataclasses import dataclass
import re

from .context import Context
from .lexicon import ADJECTIVES, NOUNS, VERBS
from .render import _inflect
from .syntax import EnkelError, MAX_SOURCE

WORD = re.compile(r"@[A-Za-z][A-Za-z0-9_]*|[A-Za-z]+(?:'[A-Za-z]+)?|[,!.?]")
AUXILIARIES = frozenset(("do", "does", "did", "am", "is", "are", "was", "were", "has", "have", "had", "will"))
CONTRACTIONS = {
    "don't": "do not", "doesn't": "does not", "didn't": "did not", "won't": "will not",
    "isn't": "is not", "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "hasn't": "has not", "haven't": "have not", "hadn't": "had not",
    "i'm": "i am", "i've": "i have", "i'll": "i will", "you're": "you are",
    "you've": "you have", "you'll": "you will", "we're": "we are", "we've": "we have",
    "we'll": "we will", "they're": "they are", "they've": "they have", "they'll": "they will",
}
AMBIGUOUS_PRONOUNS = frozenset(("he", "him", "she", "her", "it", "they", "them"))
TIME_NOUNS = frozenset(("day", "night", "hour"))


class EnglishError(EnkelError):
    """Unsupported English or an unresolved English interpretation choice."""


@dataclass(frozen=True)
class Phrase:
    enkel: str
    number: str = "singular"
    person: int = 3
    quantifier: str = ""
    noun: str = ""

    def features(self):
        return {"number": self.number, "person": self.person}


def looks_like_enkel(source):
    """A reserved clause prefix selects the existing compiler, even if malformed."""
    return re.match(r"\s*(?:(?:no-)?(?:di|du|wi)-|ka(?:-|\s|$))", source) is not None


class EnglishReader:
    def __init__(self, source, context=None, scope=None, tense=None):
        self.source, self.scope, self.tense, self.notes = source, scope, tense, []
        if not isinstance(source, str):
            raise TypeError("source must be a string")
        if len(source) > MAX_SOURCE:
            self.fail(f"English input exceeds {MAX_SOURCE} characters.")
        if scope not in (None, "surface", "object-wide"):
            self.fail("scope must be surface or object-wide.")
        if tense not in (None, "past", "present", "future"):
            self.fail("tense must be past, present, or future.")
        self.context = context if isinstance(context, Context) else Context(context)
        normalized = source.replace("\u2019", "'")
        tokens, end = [], 0
        for match in WORD.finditer(normalized):
            if normalized[end:match.start()] and not normalized[end:match.start()].isspace():
                self.fail("Unsupported English punctuation or token. Use a single sentence with known words.")
            word = match.group()
            if len(word) > 128:
                self.fail("An English token may contain at most 128 characters.")
            if tokens and match.start() == end and word not in (",", ".", "!", "?"):
                self.fail("English words must be separated by whitespace.")
            tokens.extend(CONTRACTIONS.get(word.lower(), word).split())
            end = match.end()
        if normalized[end:] and not normalized[end:].isspace():
            self.fail("Unsupported English punctuation or token.")
        if len(tokens) > 2048:
            self.fail("English input exceeds 2048 tokens.")
        self.punctuation = tokens[-1] if tokens and tokens[-1] in (".", "!", "?") else None
        while tokens and tokens[-1] in (".", "!", "?"):
            tokens.pop()
        if any(token in (".", "!", "?") for token in tokens):
            self.fail("Translate one sentence at a time, or use --file with one sentence per line.")
        self.words = tokens
        if not tokens:
            self.fail("Enter an English sentence, for example: hello world")

    def fail(self, message):
        raise EnglishError(message)

    def reference(self, spelling):
        if spelling == "me" and "speaker" not in self.context.bindings:
            data = self.context.to_dict()
            ident = "EnglishSpeaker"
            while ident in data["entities"]:
                ident += "_"
            data["entities"][ident] = {"label": "the speaker", "number": "singular", "members": []}
            data["speaker"] = ident
            self.context = Context(data)
            self.notes.append("I/me uses an explicit symbolic speaker in the exported context; no real-world identity is inferred.")
        key = {"me": "speaker", "yu": "addressee", "we": "group"}.get(spelling)
        if key and key not in self.context.bindings:
            self.fail(f"English {spelling!r} needs a {key} binding in --context; its referent or group is not inferred.")
        term = self.context.resolve(spelling)
        return Phrase(spelling, term["number"], term["person"])

    def nominal(self, start, vocative=False, time_context=False):
        if start >= len(self.words):
            self.fail("Expected an English noun phrase.")
        word = self.words[start].lower()
        if word in AMBIGUOUS_PRONOUNS:
            self.fail(f"{word!r} has no resolved antecedent. Use a declared name or @ID with --context.")
        pronoun = {"i": "me", "me": "me", "you": "yu", "we": "we", "us": "we"}.get(word)
        if pronoun:
            return self.reference(pronoun), start + 1
        if self.words[start].startswith("@"):
            return self.reference("re-" + self.words[start][1:]), start + 1
        if word == "everyone":
            return Phrase("person-u", quantifier="every", noun="person"), start + 1
        if word in ("someone", "somebody"):
            return Phrase("person-a", quantifier="exists", noun="person"), start + 1
        if word in ("nobody", "noone"):
            return Phrase("no-person-a", quantifier="none", noun="person"), start + 1

        # Names are looked up by declared label. Equal labels remain ambiguous.
        if word not in ("a", "an", "the", "every", "each", "some", "no"):
            matches = []
            for ident, entity in self.context.entities.items():
                label = entity.label.lower().split()
                if label and [w.lower() for w in self.words[start:start+len(label)]] == label:
                    matches.append((len(label), ident))
            if matches:
                length = max(n for n, _ in matches)
                candidates = [ident for n, ident in matches if n == length]
                if len(candidates) != 1:
                    self.fail("That display name identifies several entities. Use an explicit " + " or ".join("@" + x for x in candidates) + ".")
                return self.reference("re-" + candidates[0]), start + length

        determiner, i = "", start
        if word in ("a", "an", "the", "every", "each", "some", "no"):
            determiner, i = word, i + 1
        adjectives = []
        while i < len(self.words) and self.words[i].lower() in ADJECTIVES:
            adjectives.append(self.words[i].lower())
            i += 1
        if i >= len(self.words):
            self.fail("Expected a known noun after the determiner or adjectives.")
        noun_word = self.words[i].lower()
        matches = [(root, n, noun_word == n.plural) for root, n in NOUNS.items()
                   if noun_word == n.singular or (n.plural and noun_word == n.plural)]
        if len(matches) != 1:
            self.fail(f"Unsupported English noun {self.words[i]!r}. Run --lexicon to see the current vocabulary.")
        root, noun, plural = matches[0]
        if time_context and root in TIME_NOUNS and not determiner and not adjectives:
            self.notes.append(f"Bare time word {root!r} uses the Core kind reading.")
            return Phrase(root, noun=root), i + 1
        if not noun.count:
            if determiner or adjectives:
                self.fail("Mass amounts and modified mass nouns are not represented by the current Core; bare mass roots denote kinds.")
            self.notes.append(f"Bare {root!r} is represented as a kind, not as a quantified amount.")
            return Phrase(root, noun=root), i + 1
        if determiner in ("a", "an", "every", "each") and plural:
            self.fail(f"{determiner!r} needs a singular noun in this English grammar.")
        if determiner in ("a", "an"):
            ending, quantifier = "a", "exists"
        elif determiner in ("every", "each"):
            ending, quantifier = "u", "every"
        elif determiner == "the" or vocative:
            ending, quantifier = ("o" if plural else "e"), "definite"
        elif determiner == "some":
            ending, quantifier = ("i" if plural else "a"), "exists"
        elif determiner == "no":
            # 'no cats' quantifies over individual cats just as 'no cat' does.
            ending, quantifier = "a", "none"
        elif plural and not adjectives:
            self.notes.append(f"Bare plural {noun_word!r} uses the Core kind reading.")
            return Phrase(root, "plural", noun=root), i + 1
        else:
            self.fail(f"Give {noun_word!r} an explicit determiner: a, the, every, some, or no.")
        text = ("no-" if quantifier == "none" else "") + root + "-" + ending
        text += "".join(" ma-" + adjective for adjective in adjectives)
        return Phrase(text, "plural" if plural else "singular", quantifier=quantifier, noun=root), i + 1

    def verb(self, start, subject, inverted_aux=None, early_not=False):
        candidates = []
        remaining = tuple(w.lower() for w in self.words[start:])
        for root in VERBS:
            for tense in ("di", "du", "wi"):
                for perfect in (False, True):
                    for progressive in (False, True):
                        form = {"root": root, "tense": tense, "perfect": perfect, "progressive": progressive}
                        positive = _inflect(form, subject.features()).split()
                        has_aux = perfect or progressive or tense == "wi"
                        auxiliary = positive[0] if has_aux else "did" if tense == "di" else "does" if subject.person == 3 and subject.number == "singular" else "do"
                        rest = positive[1:] if has_aux else [root]
                        variants = []
                        for negative in (False, True):
                            if inverted_aux:
                                if inverted_aux != auxiliary or (early_not and not negative):
                                    continue
                                words = ([] if early_not or not negative else ["not"]) + rest
                            elif negative:
                                words = [auxiliary, "not"] + rest
                            else:
                                words = positive
                            variants.append((tuple(words), negative))
                        for words, negative in variants:
                            if remaining[:len(words)] == words:
                                if self.tense and tense != {"past": "di", "present": "du", "future": "wi"}[self.tense]:
                                    continue
                                token = tense + "-" + root + ("-en" if perfect else "") + ("-ing" if progressive else "")
                                candidates.append((len(words), token, root, negative))
        if not candidates:
            word = self.words[start] if start < len(self.words) else "end of input"
            self.fail(f"Cannot recognize a supported verb phrase at {word!r}. Check agreement, --tense, and --lexicon; copulas and modal verbs are not yet supported.")
        longest = max(c[0] for c in candidates)
        candidates = sorted(set(c for c in candidates if c[0] == longest))
        if len(candidates) != 1:
            self.fail("English verb spelling has more than one tense reading here. Choose --tense past or --tense present.")
        length, token, root, negative = candidates[0]
        return token, root, negative, start + length

    def greeting(self):
        if self.scope or self.tense:
            self.fail("Greetings use a fixed present-tense paraphrase; --scope and --tense apply to ordinary clauses.")
        i = 1
        if i < len(self.words) and self.words[i] == ",":
            i += 1
        if i == len(self.words):
            recipient = Phrase("listener-e", noun="listener")
        else:
            recipient, i = self.nominal(i, vocative=True)
            if i != len(self.words):
                self.fail("A greeting accepts one addressee noun phrase, for example 'hello world'.")
        self.notes.append("Greeting convention: hello/hi/hey is paraphrased as the speaker greeting the addressed entity; emotional tone is not encoded.")
        return "du-greet se speaker-e ob " + recipient.enkel

    def read(self):
        if self.words[0].lower() in ("hello", "hi", "hey"):
            return self.greeting()
        initial, items, i = [], [], 0
        mode, query, early_not, inverted = "statement", None, False, None
        # An explicitly fronted adjunct attaches to the clause, not an object noun.
        if self.words[0].lower() in ("using", "at", "in", "on"):
            marker = self.words[0].lower()
            nominal, i = self.nominal(1, time_context=marker in ("at", "in", "on"))
            if i >= len(self.words) or self.words[i] != ",":
                self.fail("A fronted adjunct must end with a comma, for example 'Using the telescope, I saw the man'.")
            role = "vi" if marker == "using" else "on" if nominal.noun in TIME_NOUNS else "at"
            initial.append((role, nominal))
            i += 1
        if i >= len(self.words):
            self.fail("Expected a clause after the fronted adjunct.")
        first = self.words[i].lower()
        if first in ("what", "who", "where", "when"):
            mode = "wh"
            query = {"where": "at", "when": "on"}.get(first)
            i += 1
            if i < len(self.words) and self.words[i].lower() in AUXILIARIES:
                next_word = self.words[i+1].lower() if i+1 < len(self.words) else ""
                verb_words = set(VERBS) | {v.progressive for v in VERBS.values()} | {v.participle for v in VERBS.values()} | {"been", "not"}
                query = query or ("se" if next_word in verb_words else "ob")
            else:
                if query:
                    self.fail("Where/when questions need an auxiliary followed by a subject.")
                query = "se"
            if first == "who":
                self.notes.append("Core wh variables are role-based; the English human-only implication of 'who' is not encoded.")
        explicit_outer_not = False
        if mode == "statement" and self.words[i].lower() == "not":
            if i + 1 >= len(self.words) or self.words[i + 1].lower() not in ("every", "each"):
                self.fail("Initial 'not' must precede every/each. Use an auxiliary for ordinary clause negation.")
            explicit_outer_not = True
            i += 1
        if i < len(self.words) and self.words[i].lower() in AUXILIARIES and query != "se":
            inverted = self.words[i].lower()
            mode = "yes_no" if mode == "statement" else mode
            i += 1
            if i < len(self.words) and self.words[i].lower() == "not":
                early_not, i = True, i + 1
        if query == "se":
            subject = Phrase("", person=3)
        else:
            subject, i = self.nominal(i)
        verb, root, negative, i = self.verb(i, subject, inverted, early_not)
        if explicit_outer_not:
            items.append(("ne", None))
        items.extend(initial)
        if query != "se":
            items.append(("se", subject))
        if negative:
            items.append(("ne", None))
        occupied = {role for role, _ in items if role != "ne"}
        if query:
            occupied.add(query)
        while i < len(self.words):
            word = self.words[i].lower()
            role, explicit = None, False
            if word in ("who", "that", "which"):
                self.fail("English relative clauses are not yet supported. Use --from enkel with ke ... ek to make the attachment explicit.")
            if word in ("with", "at") and i + 1 < len(self.words):
                pair = (word, self.words[i+1].lower())
                role = {("with", "instrument"): "vi", ("with", "recipient"): "to", ("at", "place"): "at", ("at", "time"): "on"}.get(pair)
                if role:
                    i, explicit = i + 2, True
            if role is None and word == "to":
                role, i, explicit = "to", i + 1, True
            if role is None and word in ("with", "using", "at", "in", "on"):
                if word == "with":
                    self.fail("'With' can mark an instrument or a companion. Use 'with instrument' for an instrument; companionship is outside this Core.")
                if "ob" in occupied:
                    self.fail("The trailing phrase could modify the object or the action. Front it with a comma, or use 'with instrument', 'at place', or 'at time'; use an Enkel relative for noun attachment.")
                role, i = ("vi" if word == "using" else "at"), i + 1
            phrase, i = self.nominal(i, time_context=role in ("at", "on"))
            if role is None:
                if "ob" not in occupied:
                    role = "ob"
                elif "to" in VERBS[root].permitted and "to" not in occupied and query != "ob":
                    # English double-object order: give [recipient] [object].
                    items = [("to" if r == "ob" else r, p) for r, p in items]
                    occupied.remove("ob")
                    occupied.add("to")
                    role = "ob"
                else:
                    self.fail("Unexpected extra noun phrase; use an explicit role preposition.")
            if role in ("at", "on") and not explicit and phrase.noun in TIME_NOUNS:
                role = "on"
            if role in occupied:
                self.fail(f"The English input fills role {role!r} twice.")
            occupied.add(role)
            items.append((role, phrase))
        if self.punctuation == "?" and mode == "statement":
            self.fail("Use question word order, for example 'Does the cat eat a cookie?'.")
        quantifiers = [p.quantifier for _, p in items if p and p.quantifier in ("every", "exists", "none")]
        ambiguous_scope = len(set(quantifiers)) > 1 or (negative and "every" in quantifiers)
        if ambiguous_scope and self.scope is None and not explicit_outer_not:
            self.fail("The English input permits different quantifier or negation scopes. Use --scope surface for written noun order (subject outside verb negation), or --scope object-wide for one shared object. 'Not every ...' explicitly selects wide negation.")
        if self.scope == "object-wide":
            targets = [(r, p) for r, p in items if r == "ob" and p.quantifier]
            if not targets:
                self.fail("--scope object-wide requires an overt quantified object.")
            items = targets + [(r, p) for r, p in items if r != "ob"]
            self.notes.append("The object takes widest scope, as requested.")
        elif self.scope == "surface":
            self.notes.append("Written noun order determines scope; a verbal not follows the subject binder.")
        prefix = "ka " if mode == "yes_no" else "ka-" + query + " " if mode == "wh" else ""
        return prefix + verb + " " + " ".join(r if p is None else r + " " + p.enkel for r, p in items)


def translate_english(source, context=None, *, scope=None, tense=None):
    """Return validated Enkel plus its compiler result and explicit context."""
    from . import compile_sentence
    reader = EnglishReader(source, context, scope, tense)
    enkel = reader.read().strip()
    result = compile_sentence(enkel, reader.context)
    return {**result, "source": source, "input_language": "english", "enkel": result["normalized"],
            "context": reader.context.to_dict(), "notes": reader.notes}
