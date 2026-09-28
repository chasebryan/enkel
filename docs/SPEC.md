# Enkel Core 0.1.0

**A sentence states its structure. The renderer follows it.**

This document specifies the implemented Core language. The accompanying
[grammar](grammar.ebnf), [implementation](../enkel/), and
[conformance tests](../tests/test_core.py) define one bounded version that can
be run today. The original idea supplies the roots, tense morphology,
determiner vowels, role particles, relatives, and questions. Core makes the
previously implicit choices explicit.

## 1. Contract

Given a fixed Core version, its closed lexicon, and a valid discourse context,
every **accepted** input has one surface parse, one resolved scope tree, and one
canonical controlled-English rendering. Unsupported input is rejected. There
is no statistical parser, language-model fallback, or silent repair.

The contract is structural. It does not claim that an arbitrary reader cannot
misread English, that names identify real people without a supplied context,
or that English roots have no philosophical or lexical uncertainty. A world
interpretation must assign each root one predicate or kind denotation.
Enkel cannot decide whether that interpretation is true of the actual world.

The English output is a controlled notation: explicit binder labels,
parentheses, quoted reference labels, and prescribed scope frames are part of
the output. The JSON scope tree is the machine interface. This release has no
English-to-Enkel translator and no inverse English parser.

Different source spellings can have the same meaning. In particular, `re-1`
and `re` normalize together, and nominal negation has an explicit equivalent.
Canonical means a fixed rendering procedure; it does not mean a decision
procedure for logical equivalence between arbitrary sentences.

## 2. Lexical boundary

Core tokens use ASCII letters, digits, underscores, and hyphens. Word tokens
are separated by whitespace. A single final `.` or `?` may touch the final
word. Declaratives accept only `.`; questions accept only `?`. Punctuation is
optional and is removed by source normalization. Internal punctuation and
unrecognized characters are errors. The CLI file mode reads one sentence per
nonblank line and ignores lines beginning with `#` after indentation.

The pinned vocabulary contains 27 noun roots, 22 verb roots, and 18 adjective
roots. Run `python3 -m enkel --lexicon` for the complete inventory, English
forms, and verb role frames. Roots are not inferred from spelling. Adding a
root requires an explicit lexicon change and a new lexicon fingerprint.

The parser supports at most 65,536 source characters, 2,048 tokens, 128
characters per token, 24 nested relative clauses, and 128 standalone `ne`
tokens per sentence. These are implementation limits, not statements about
the expressive power of a future unbounded grammar.

## 3. Verb morphology

The verb begins each clause, after an optional sentence-level question marker.
It is a single token:

```text
[no-](di|du|wi)-ROOT[-en][-ing]
```

`di` marks past, `du` present, and `wi` future. `-en` marks perfect aspect and
`-ing` progressive aspect. When both occur, perfect comes first. The spelling
`du-eat-ing-en` is rejected.

| Form | English with singular third-person subject |
| --- | --- |
| `di-eat` | ate |
| `du-eat` | eats |
| `wi-eat` | will eat |
| `di-eat-en` | had eaten |
| `du-eat-en` | has eaten |
| `wi-eat-en` | will have eaten |
| `di-eat-ing` | was eating |
| `du-eat-ing` | is eating |
| `wi-eat-ing` | will be eating |
| `di-eat-en-ing` | had been eating |
| `du-eat-en-ing` | has been eating |
| `wi-eat-en-ing` | will have been eating |

Person and number select `am/is/are`, `was/were`, `have/has`, and the lexical
third-person present form. Irregular past, participle, and progressive forms
come from the lexicon. Core has no guessed inflection rules for unknown verbs.

If two legal tense/aspect combinations have identical written English for the
same subject, the renderer adds an explicit tense/aspect annotation. Thus
`di-read se me` and `du-read se me` cannot both collapse to unqualified
"I read." They produce `read (past tense, simple aspect)` and
`read (present tense, simple aspect)` respectively.

Tense and aspect remain explicit fields on the predicate node. They do not
move noun quantifiers. A model supplies the interpretation of each tagged
predicate at its reference time; the prototype does not implement a temporal
reasoner or English aspect entailments.

## 4. Nominals

| Form | Binder or term | Fixed Core reading |
| --- | --- | --- |
| `cat-a` | `exists` | at least one individual cat |
| `cat-e` | `definite` | the unique individual cat in the contextual domain |
| `cat-i` | `exists_plural` | a finite plurality of at least two cats |
| `cat-o` | `definite_plural` | the unique greatest qualifying cat plurality by membership inclusion |
| `cat-u` | `every` | each individual cat |
| `no-cat-a` | `not(exists(...))` | no individual cat satisfies the remaining scoped body |
| `cat` | kind term | cats as a kind, without an instance quantifier |
| `water` | kind term | water as a kind |

Nominal `no-` is supported only with `-a`. Forms such as `no-cat-u` are
rejected, since their intended scope would otherwise need another rule.
Write the desired universal and `ne` placement instead.

Mass roots (`water`, `music`) are kind terms only in 0.1. Neither `water-a`
nor `water-e` is implemented. Amounts, portions, and mass quantification need
their own future design. Bare count roots are also kind terms; `cat` does not
mean "every cat" or "most cats."

Plural predicates apply to the designated plurality **collectively**. There
is no automatic distributive reading. `du-eat se cat-i` predicates eating of
one cat plurality; `du-eat se cat-u` distributes over individual cats. A model
may assign a collective predicate however its domain requires, but the parser
never chooses between collective and distributive readings.

Definites require uniqueness, not a parser guess. Failure of uniqueness is a
semantic definedness failure, not an alternative parse. Core does not look up
which cat a user has in mind. The domain supplied by an interpretation must
make the description usable.

## 5. Roles and verb frames

Every overt nominal has exactly one role particle.

| Role | Meaning | Canonical predicate position |
| --- | --- | --- |
| `se` | subject | before the verb |
| `ob` | object | immediately after the verb |
| `to` | recipient | `with recipient ...` |
| `vi` | instrument | `using instrument ...` |
| `at` | place | `at place ...` |
| `on` | time | `at time ...` |

Each role occurs at most once per clause. A queried role counts as present.
All verbs require a subject. Some require additional roles: `give` and `show`
require both object and recipient; `see` and `hold` require an object; `eat`
allows an object but does not require one. `sleep` does not take an object.
The lexicon records every required and permitted role. All current verbs
permit the three adjunct roles `vi`, `at`, and `on`.

Role membership determines argument attachment. Thus `vi telescope-e` is an
instrument of the current predication. It cannot silently become a modifier
of the preceding man. Surface order affects scope, while role names determine
the final predicate argument order.

## 6. Modifiers and relatives

Adjectives have an explicit `ma-` prefix:

```text
cat-a ma-small ma-black
```

All adjectives in this immediate postfix bundle modify that noun head. They
are intersective properties in the Core interpretation. `small` is therefore
one supplied predicate on individuals; context-sensitive comparative standards
are outside this prototype. Bare adjective words are rejected.

This formalizes the original adjacency idea as adjacency to the current
nominal head, rather than to the last whitespace token. Without that
refinement, `small` could modify `black` in an adjective sequence. The Core
grammar has one production: head, adjective bundle, relative bundle. Adjectives
after a relative are rejected. References and kind terms do not take modifiers
in this release.

Each `ke ... ek` is a restrictive relative attached to the immediately
preceding determined nominal. It has its own verb and role frame. It cannot
contain a question prefix. Multiple consecutive relatives restrict the same
head by conjunction.

`re` refers to the closest enclosing relative's noun head. `re-1` is the same
reference; `re-2` refers to the next outer head, and so on. These are lexical
depths, not searches for a likely antecedent. An out-of-range reference is an
error. Each relative must actually mention its own head, possibly from within
a nested relative through an explicit outer depth.

```text
di-see se me ob man-a
  ke di-see se re ob woman-a
    ke di-help se re ob re-2 ek
  ek
```

The inner `re` is the woman. `re-2` is the man. The outer `re` is the man.
New quantifiers inside a relative stay inside that relative's restriction;
they never escape to the surrounding clause. References to free discourse
IDs are also permitted inside relatives.

The renderer expresses relatives as explicit `satisfying (...)` restrictions.
This replaces the informal who/that projection in the initial sketch: a
relative may use its head in any role or several roles, so a fixed visible
binding is more reliable than trying to infer an English gap construction.

## 7. Reference context

`re-John` means the entity with the **declared ID** `John`. The capitalized
suffix is case-sensitive. It does not mean "whichever person is named John."
An ID begins with an uppercase ASCII letter and continues with ASCII letters,
digits, or underscores. Numeric suffixes belong exclusively to relative depth
references. This keeps the two mechanisms syntactically disjoint.

```json
{
  "entities": {
    "Speaker": {"label": "the speaker", "number": "singular"},
    "John": {"label": "John", "number": "singular"},
    "OtherJohn": {"label": "John", "number": "singular"},
    "Team": {
      "label": "the speaker and John",
      "number": "plural",
      "members": ["Speaker", "John"]
    }
  },
  "speaker": "Speaker",
  "addressee": "John",
  "group": "Team"
}
```

`me` uses `speaker`, `yu` uses `addressee`, and `we` uses `group`. A singular
entity cannot list members. A plural entity needs at least two distinct,
declared singular members. The `group` binding must be plural and include the
declared singular speaker. The addressee can be singular or an explicit
plurality. No binding is supplied implicitly. `Context.from_json` and the CLI
reject duplicate JSON keys at every level, including repeated entity IDs;
a later declaration cannot silently overwrite an earlier one. API callers
supplying an already-decoded dictionary are responsible for preserving that
same input condition.

Display labels are never identity keys. The renderer JSON-quotes named labels
and retains `[@ID]`, so two entities both labeled John remain distinguishable.
Context membership is fixed by the supplied context and its fingerprint.
The meaning tree resolves reference IDs but does not duplicate the complete
context in every reference node. Preserve the context alongside exported
trees when interpreting group membership.

Quantified variables do not become discourse IDs. There is no automatic
cross-sentence anaphora or dynamic "last person mentioned" rule. A later
sentence that needs an entity must receive an explicit context binding.

## 8. Scope construction

The compiler assigns fresh variables in source traversal order: `x1`, `x2`,
and so on. It assigns the head before visiting that head's relative
restrictions. The counter is shared across the sentence. Wh questions reserve
`q0`, which is distinct from every noun binder.

For a clause, process items from left to right:

1. A determined nominal creates a variable, a restriction, and a binder at
   that position in the scope spine. Its role points to the variable.
2. A reference or kind term fills its role directly; it creates no binder.
3. `ne` inserts a negation operator at that exact position.
4. `no-NOUN-a` inserts negation followed by an existential binder.
5. Build the tagged predicate with role slots in fixed order.
6. If the verb has `no-`, negate that predicate.
7. Fold the recorded scope operators from right to left around the result.

For operators `O1 ... On` and predicate `P`, the result is
`O1(O2(...On(P)...))`. Each clause performs this operation independently.
Negation in a relative does not negate its enclosing main clause.

This is the operative meaning of "leftmost scopes widest." It applies to the
entire local scope spine, not just to the first phrase. Definite binders retain
their positions too; no implicit raising or scope optimization occurs.

### The three negation readings

| Source | Exact scope | Informal gloss |
| --- | --- | --- |
| `no-du-eat se child-u ob cookie-a` | every child, exists cookie, not eat | Each child leaves at least one cookie uneaten. |
| `du-eat se child-u ne ob cookie-a` | every child, not exists cookie, eat | No child eats any cookie. |
| `du-eat ne se child-u ob cookie-a` | not every child, exists cookie, eat | Not every child eats a cookie. |

The verb prefix has narrow scope by explicit definition. Use `ne` for another
position. Writing `ne` after the last role has the same meaning as verb `no-`.
Successive `ne` tokens represent successive negations; they are not silently
simplified. Nominal negation has the scope of its place in this same spine.

### A subject-first counterexample

```text
du-give se teacher-u to child-u ob book-a
```

The tree is `every teacher -> every child -> exists book -> give`. Reordering
to "Every teacher gives a book to every child" would obscure the dependency.
The renderer therefore retains every scope frame:

```text
For every teacher [x1], (for every child [x2], (there is a book [x3] such that ([x1] gives [x3], with recipient [x2]))).
```

Moving `ob book-a` before `to child-u` instead produces
`every teacher -> exists book -> every child -> give`. These differ in a
world where a teacher gives a different book to each child and gives no book
to both children. That world is a regression test.

## 9. Meaning tree

The JSON representation uses the following node forms. Field names below are
literal. `Body` means a `bind`, `not`, or `predicate` node.

```text
Sentence = {type: statement | yes_no, body: Body}
         | {type: wh, role: Role, variable: Term, body: Body}

Body = {type: not, body: Body}
     | {type: bind, quantifier: Quantifier, variable: Term,
        restriction: Restriction, body: Body}
     | {type: predicate, verb: Verb, roles: {Role: Term, ...}}

Quantifier = exists | every | definite | exists_plural | definite_plural
Restriction = {noun: Root, adjectives: [Root, ...], relatives: [Body, ...]}
Verb = {root: Root, tense: di | du | wi, perfect: Boolean, progressive: Boolean}

Term = {type: variable, name: xN | q0, number: singular | plural, person: 3}
     | {type: kind, noun: Root, number: singular, person: 3}
     | {type: reference, id: ID, label: String, number: singular | plural,
        person: 1 | 2 | 3, pronoun: me | yu | we | null}
```

A `bind` variable is in scope in its restriction's relative bodies and in its
continuation body. Only relative back-references can introduce that variable
into the restriction from source text. The `wh` variable scopes over the
whole clause. Other variable uses are created from role arguments, not from
arbitrary textual names. All bound-variable uses are resolved during lowering.

The exported `syntax` tree additionally retains source order, morphology,
nominal spelling, and nominal character offsets for diagnostics. Source
normalization removes whitespace and punctuation variation; diagnostic
offsets naturally change when the same sentence is respaced. The `meaning`
tree and `english` rendering do not.

The compilation envelope includes the grammar version and SHA-256
fingerprints of the lexicon and normalized context. Fingerprints identify
inputs; they are not signatures, attestations, or proofs of correctness.

## 10. Interpretation boundary

For a supplied world, let `R(x)` mean membership in a binder's restriction and
`B(x)` its continuation. Singular quantifiers have the usual explicit forms:

```text
exists x:R. B    = some x satisfies both R(x) and B(x)
every x:R. B     = every x satisfying R(x) satisfies B(x)
not B           = Boolean negation of B, when B is defined
definite x:R. B  = B(d), when exactly one d satisfies R; otherwise undefined
```

Noun and adjective restrictions on singular binders are conjunctive. Relative
bodies are further conjuncts evaluated with the head variable assigned.
Universals over empty restrictions are true; existentials are false. The
compiler never inserts an existence assertion for a universal.

For plural binders, candidates are finite sets of at least two individuals.
Each member satisfies the noun and adjective predicates. Relative bodies are
evaluated on the entire candidate plurality. `exists_plural` existentially
binds such a candidate. `definite_plural` requires a **greatest** qualifying
candidate under set inclusion, then evaluates the body on it. Merely having
two incomparable maximal groups is insufficient. No greatest candidate means
undefined. An infinite qualifying population may also have no greatest finite
plurality. This explicitly fixes a boundary that "the cats" alone leaves
unstated.

Definedness is not a claim about conversational presupposition projection.
For a precise strict interpretation of this Core, evaluate all restriction
candidates and all required continuations; an undefined subevaluation makes
the enclosing evaluation undefined. Negation preserves undefinedness. Boolean
short-circuiting does not hide it. Empty candidate sets need no continuation
evaluation. A future alternative projection policy would need a versioned
semantic extension, not a renderer change.

Root meanings and tense/aspect truth conditions are interpretation parameters.
The production package compiles and renders; it does not evaluate arbitrary
worlds. The independent finite-world oracle in the tests implements only
present-simple singular `exists`, `every`, negation, and relative restrictions.
It raises on unsupported operators. Its purpose is to demonstrate scope
counterexamples, not to imply that a full theorem prover is included.

## 11. Questions

`ka` wraps the completed scoped clause in a yes/no question. It does not alter
quantifier order or negation placement.

`ka-ROLE` creates one distinguished query variable `q0` in that role. The
clause must not also contain an overt phrase with that role. Core permits only
one query role and no simultaneous `ka` prefix. Questions cannot occur inside
relatives.

The wh operator is outside all local binders. Thus
`ka-ob du-eat se child-u` asks for objects that every child eats, rather than a
separate possibly different answer for each child. Answers range over one
individual at a time in Core 0.1; no plural-answer coercion or pair-list
reading is inferred. A question's truth or answer set is undefined when its
required body interpretation is undefined.

```text
ka-ob wi-eat se cat-e
Which object [q0] makes the following true: (for the unique cat [x1], ([x1] will eat [q0]))?
```

"Which subject" is used for `ka-se`, avoiding an implicit human-only domain.
The initial sketch's natural "who" and "what" are useful informal glosses,
but do not replace the typed role in the canonical output.

## 12. Rendering algorithm

The renderer consumes the resolved meaning tree, never the unparsed input.

1. Render binder labels and references without renaming or inference.
2. Render each restriction's adjectives in source order and each relative as
   `satisfying (...)`. Join multiple relative bodies with `and`.
3. Render every binder with its fixed English frame. Always retain frames,
   even when a shorter sentence might happen to be safe.
4. Render each negation as `it is not the case that (...)` at its tree position.
5. Render the atomic clause in `se, verb, ob, to, vi, at, on` order. Explicit
   adjunct phrases identify instrument, place, time, and recipient roles.
6. Inflect from the pinned lexicon and subject features. Add an explicit
   tense/aspect annotation if English spelling would collapse two forms.
7. Add the sentence-level question frame if needed, capitalize the first
   character, and append exactly one final `.` or `?`.

Binder frames are fixed by `render.py`: singular existence uses "there is
a/an ... such that (...)"; universal uses "for every ..., (...)"; singular
definite uses "for the unique ..., (...)". Plural frames explicitly identify
the bound plurality. A/an is chosen from the closed vocabulary's initial
sounds, including the silent h in `hour`; adding vocabulary must revisit that
rule if its initial sound is exceptional.

Instrument fronting is not a discretionary style rule. All instruments
remain in the atomic instrument slot. There is no final pass that drops
parentheses, replaces IDs with guessed pronouns, fronts a phrase, or exchanges
quantifiers. Such a pass could erase the distinctions the language records.

## 13. Why parsing is unique

This is an informal structural argument, not a machine-checked proof.

The tokenizer has one prescribed tokenization. The closed root vocabulary and
reserved particle forms are disjoint where a production must choose: a verb
has a tense prefix, an adjective has `ma-`, and a determined noun has a final
determiner vowel. Named references begin with an uppercase ID; relative depth
references have a positive decimal suffix; bare roots are kind terms. The
question prefix is recognized only at the sentence boundary.

Within a clause, one role token selects exactly one following nominal, and
`ne` selects a scope operator. Within a nominal, all immediately following
`ma-` tokens form its adjective bundle, then immediately following `ke`
tokens open relatives. Each `ek` closes the most recently opened relative.
The parser neither backtracks nor searches for a preferred attachment.

Induction on relative nesting gives one nominal and clause parse for every
accepted token sequence. Duplicate or forbidden roles, absent required roles,
and unresolved references cause rejection; they never select an alternative
parse. Variable allocation and the right fold of the scope spine are then
deterministic functions of that parse. Rendering is structural recursion with
one branch per node kind and one fixed inflection lookup.

This argument establishes the intended uniqueness construction. The test
suite supplies executable evidence for its implementation. It is not a
formal verification of the Python runtime or an exhaustive proof of all code.

## 14. Explicit exclusions and compatibility

Core 0.1 excludes coordination, disjunction, conditionals, modals, comparative
adjectives, proper nouns outside declared references, unrestricted adverbs,
complement clauses, quotation, dynamic discourse binding, mass amounts,
multiple overt phrases with the same role, and arbitrary English input.
Future syntax must preserve disjoint parsing choices and explicit scope.

All five initial example sentences parse. The example using `me` requires a
context. Their **canonical English strings change deliberately** to retain
scope and referent labels. Core also makes these choices explicit:

- `ne` is the new general scope-negation particle.
- Verb `no-` has narrow scope inside local binders.
- `ma-` makes adjective boundaries explicit and targets the noun head.
- `re-ID` requires a declaration; numeric `re-N` is lexical relative depth.
- Canonical relatives use visible restrictions rather than inferred English gaps.
- Bare nouns denote kinds, and plural quantification is collective.
- Questions have one widest-scope individual answer variable.

Those are design decisions, not facts that were already implied by the
informal sketch. They are versioned here so a later implementation can agree
with this one or explicitly change the language.
