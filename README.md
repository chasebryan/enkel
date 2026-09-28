# Enkel

**Explicit structure. One controlled-English rendering.**

Enkel is a formal layer beneath English. Tense is mandatory, arguments have
explicit roles, and written quantifier order determines scope. A strict parser
compiles each accepted sentence into a scoped meaning tree and a deterministic
English rendering. It never asks a language model to guess a reading.

This is **Enkel Core 0.1.0**, an executable, deliberately bounded prototype.
The canonical rendering uses parentheses and bound-variable labels so English
word order cannot silently erase a distinction made in Enkel.

Start with the [usage guide](docs/QUICKSTART.md), then inspect the
[formal specification](docs/SPEC.md) and [validation notes](docs/VALIDATION.md).

## Run

Python 3.10 or newer. No runtime dependencies or network access required.
Run these commands from the repository root:

```sh
python3 -m enkel 'du-eat se child-u ob cookie-a'
python3 -m enkel 'du-eat ob cookie-a se child-u' --format logic
python3 -m enkel 'ka-ob wi-eat se cat-e' --format json
python3 -m enkel --file examples/sentences.enk --context examples/context.json
python3 -m enkel --lexicon
python3 -m unittest discover -s tests -v
```

```text
du-eat se child-u ob cookie-a
For every child [x1], (there is a cookie [x2] such that ([x1] eats [x2])).

du-eat ob cookie-a se child-u
There is a cookie [x1] such that (for every child [x2], ([x2] eats [x1])).
```

`ne` negates everything following it within the current clause's scope spine.
Verb `no-` negates only the final predication, inside all local noun binders.
These are intentionally different:

```text
no-du-eat se child-u ob cookie-a
Every child has some cookie that the child does not eat.

du-eat se child-u ne ob cookie-a
No child eats any cookie.

du-eat ne se child-u ob cookie-a
Not every child eats a cookie.
```

The three explanations above are informal glosses; the CLI's labeled output
is canonical.

## Python API

```python
from enkel import compile_sentence

result = compile_sentence('du-eat se child-u ob cookie-a')
print(result['english'])
print(result['meaning'])
```

Pass an explicit context dictionary for `me`, `yu`, `we`, or `re-ID`.
Two IDs may share the display label "John" without becoming the same referent.
`examples/context.json` contains synthetic demonstration identities.

## Current boundary

The implementation supports declarations, yes/no and single-role questions,
all five determiner vowels, kind terms, fixed tense/aspect forms, explicit
negation, adjective modifiers, nested restrictive relatives, and declared
references. Vocabulary is closed and inspectable with `--lexicon`.

It does not translate arbitrary English, infer intended reference, decide
real-world truth, or resolve the philosophical meanings of its English roots.
The formal guarantee concerns a unique scoped structure under the pinned
grammar, vocabulary, and context.

Read the [complete specification](docs/SPEC.md) for the scoping algorithm,
reference rules, plural semantics, canonical rendering procedure, and an
informal uniqueness argument. The [EBNF grammar](docs/grammar.ebnf) gives the
syntax. The [test suite](tests/test_core.py) checks all original examples,
scope counterexamples in finite worlds, relative binding, reference identity,
English agreement, invalid forms, and 120 generated normalization round trips.

## License

Apache-2.0. See [LICENSE](LICENSE).
