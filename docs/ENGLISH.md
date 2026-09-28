# English input

Enkel 0.2 accepts plain English at the command line. The output is validated
Enkel Core, ready for its parser; it is not a sequence of substituted words.

```sh
python3 -m enkel "hello world"
```

```text
du-greet se speaker-e ob world-e
```

The greeting has a documented paraphrase: **the speaker greets the world**.
`hello`, `hi`, and `hey` use that convention with an addressed noun phrase.
`hello` alone addresses `listener-e`; `hello everyone` addresses `person-u`.
Greeting mood, emotional tone, and emphasis are not encoded as additional
Core operators. The resulting assertion is a conventional representation of
the greeting act, not a claim that all greeting pragmatics reduce to an
ordinary assertion.

## Choose input and output

The default `--from auto` recognizes an Enkel tense prefix or `ka` question
prefix. Such input goes to the Core compiler. Other input goes to the English
front end. Malformed Enkel does not silently fall back to English recognition.

| Command | Result |
| --- | --- |
| `python3 -m enkel "hello world"` | English to Enkel |
| `python3 -m enkel --from english "hello world"` | Explicit English input |
| `python3 -m enkel --from enkel "du-sleep se cat-a"` | Explicit Core compilation to English |
| `python3 -m enkel "hello world" --format english` | Inspect the canonical English paraphrase |
| `python3 -m enkel "hello world" --format json` | Translation, source, notes, context, syntax, and meaning |

Other output formats are `enkel`, `normalized`, and `logic`. English input
defaults to Enkel output; Enkel input defaults to canonical English output.
Omitting the sentence reads stdin. `--file` takes one sentence per nonblank
line. Lines beginning with `#` after indentation are comments. The whole batch
is checked before any successful output is printed.

## Supported patterns

| English | Enkel |
| --- | --- |
| The cat eats a cookie. | `du-eat se cat-e ob cookie-a` |
| A dog chased the cat. | `di-chase se dog-a ob cat-e` |
| I will eat an apple. | `wi-eat se me ob apple-a` |
| I have been eating an apple. | `du-eat-en-ing se me ob apple-a` |
| The small black cat sleeps. | `du-sleep se cat-e ma-small ma-black` |
| Some children sleep. | `du-sleep se child-i` |
| No children sleep. | `du-sleep se no-child-a` |
| The cat does not eat a cookie. | `du-eat se cat-e ne ob cookie-a` |
| The teacher gives the child a book. | `du-give se teacher-e to child-e ob book-a` |
| The teacher gives a book to the child. | `du-give se teacher-e ob book-a to child-e` |
| What will the cat eat? | `ka-ob wi-eat se cat-e` |
| Does the cat eat a cookie? | `ka du-eat se cat-e ob cookie-a` |
| Where does the cat sleep? | `ka-at du-sleep se cat-e` |

Recognition uses the closed Core lexicon and its explicit irregular forms.
All twelve tense/aspect combinations are supported. Common contractions,
including don't, didn't, won't, I'm, I've, and haven't, expand before parsing.
ASCII case does not affect ordinary English words. Sentence-final punctuation
is optional. The explicit form `@ID` retains case-sensitive context IDs.

Supported noun phrases have a determiner, zero or more known adjectives, and
a known noun, or use a resolved reference. `every` and `each` map to `-u`;
`a/an` to `-a`; `the` to `-e` or `-o`; `some` to `-a` or `-i`.
`no cats` quantifies negatively over individual cats, so it maps to `no-cat-a`.
Bare plural and mass roots use the Core kind interpretation, not an implicit
universal or an amount. Bare temporal nouns in adjuncts, such as `at night`,
also use kind terms. Explicit pluralities retain the Core collective reading.

## Make ambiguous choices explicit

The front end detects specific known ambiguities. This is not an exhaustive
natural-language ambiguity detector. Its supported grammar and the following
conventions define what it translates.

```sh
python3 -m enkel "Every child eats a cookie" --scope surface
python3 -m enkel "Every child eats a cookie" --scope object-wide
```

```text
du-eat se child-u ob cookie-a
du-eat ob cookie-a se child-u
```

Mixed existential/universal/negative quantifiers require a scope choice.
`surface` preserves the noun phrase order; ordinary verbal negation is placed
after the subject and before the following arguments. `object-wide` moves an
overt object binder to the front. It does not enumerate every possible scope
of a three-place sentence. Write Core explicitly for another ordering.

`Not every child eats a cookie` explicitly selects clause-wide negation over
the surface-order clause. It translates to `du-eat ne se child-u ob cookie-a`.
Greetings have a fixed present-tense convention and reject scope/tense flags.

Written `I read a book` does not determine past versus present. Select it with
`--tense past` or `--tense present`; this option filters grammatical candidates
and never changes an explicitly incompatible English tense.

`I saw the man with the telescope` is rejected because attachment is unclear.
Use `Using the telescope, I saw the man` for an instrument of seeing, or
`I saw the man with instrument the telescope`. To describe the man's
relationship to the telescope, write a Core relative with `ke ... ek`.
Trailing location phrases after an object similarly require explicit
attachment. Bare `with` is not assumed to mean instrument; it can also express
companionship, which this Core does not encode.

Fronted `Using`, `At`, `In`, and `On` phrases must end with a comma. Locations
are projected to the general Core place role, so finer spatial distinctions
such as inside versus on top are not preserved. The explicit patterns
`with instrument`, `with recipient`, `at place`, and `at time` select roles
directly. English who/what questions select a role variable; Core does not
encode the human-only implication of `who`.

## Preserve reference context

English `I` or `me` uses the supplied speaker binding. When none is supplied,
the translator adds a fresh symbolic speaker to its returned context. The ID
starts as `EnglishSpeaker` and gains underscores to avoid an existing entity
ID. It is a discourse placeholder, not an inferred real-world identity.

```python
from enkel import compile_sentence, translate_english

result = translate_english('I ate an apple')
print(result['enkel'])
replayed = compile_sentence(result['enkel'], result['context'])
assert replayed['meaning'] == result['meaning']
```

Use `--format json` to export that context with the translation. A bare output
containing `me` still needs its context when later passed to the Core compiler.
Greetings use ordinary definite `speaker-e`, so `hello world` needs no
pronoun context to translate or compile.

English `you` and `we/us` require declared `addressee` and `group` bindings in
`--context`. Group membership and number are never guessed. Third-person
pronouns such as he/she/it/they are rejected unless rewritten with a declared
name or explicit `@ID`.

Names resolve against declared display labels. A label shared by several IDs
causes an error; use `@John` or `@OtherJohn` to choose the actual declared ID.
New proper names are not automatically minted as known entities.

## Boundary

This release is an offline, deterministic English front end for the supported
patterns, not an unrestricted translator. Unknown vocabulary, copulas such as
`is happy`, modal verbs, coordination, English relative clauses, and arbitrary
paragraphs are rejected with a diagnostic. The Core still accepts its own
explicit relatives and the rest of its documented syntax through
`--from enkel`.

All successful translations are compiled and reference-checked before they
are returned. Formal uniqueness applies to that resulting Core structure.
English interpretation follows the documented projections above; it does not
gain the stronger guarantee merely by being accepted as source text.
