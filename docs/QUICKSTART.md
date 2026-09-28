# Translate English or write Enkel

Start with ordinary English:

```sh
python3 -m enkel "hello world"
```

```text
du-greet se speaker-e ob world-e
```

The greeting has a fixed paraphrase: the speaker greets the world. Statements
such as `The cat eats a cookie` and questions such as `What will the cat eat?`
also translate directly. See [the English input guide](ENGLISH.md) for its
supported grammar, context handling, and explicit ambiguity choices.

Input beginning with an Enkel tense or question prefix continues to compile
to English automatically. Use `--from english` or `--from enkel` to select
the input language yourself. The examples below show that Core compilation
direction, including how to write scope directly.

Run the examples from the repository root with Python 3.10 or newer. Nothing
needs to be installed to use `python3 -m enkel`.

```sh
python3 -m enkel 'du-eat se child-u ob cookie-a'
```

```text
For every child [x1], (there is a cookie [x2] such that ([x1] eats [x2])).
```

Read `[x1]` as "that child" and `[x2]` as "that cookie." The labels matter
when several descriptions use the same noun. Each pair of parentheses closes
the scope of the frame immediately before it.

## Change the meaning by moving a phrase

```sh
python3 -m enkel 'du-eat ob cookie-a se child-u'
```

```text
There is a cookie [x1] such that (for every child [x2], ([x2] eats [x1])).
```

The first version permits a different cookie for each child. The second
requires a cookie shared by the description of every child's eating. Swapping
phrases changes scope even though the final subject and object roles remain
the same.

## Put negation where you mean it

```text
no-du-eat se child-u ob cookie-a
```

Every child has a cookie the child does not eat. The verb prefix is narrow.

```text
du-eat se child-u ne ob cookie-a
```

For every child, it is false that there is a cookie the child eats.

```text
du-eat ne se child-u ob cookie-a
```

It is false that every child eats some cookie. At least one child fails that
description. These glosses explain the distinction; the labeled output is the
canonical rendering.

## Say who is speaking

```sh
python3 -m enkel 'di-see se me ob man-e vi telescope-e' --context examples/context.json
```

```text
For the unique man [x1], (for the unique telescope [x2], (I [@Speaker] saw [x1], using instrument [x2])).
```

`me` resolves to the context's explicit speaker. `vi` attaches the telescope
to the act of seeing. To describe the man as holding the telescope instead:

```sh
python3 -m enkel 'di-see se me ob man-e ke di-hold se re ob telescope-e ek' --context examples/context.json
```

```text
For the unique man [x1] satisfying (for the unique telescope [x2], ([x1] held [x2])), (I [@Speaker] saw [x1]).
```

Here `re` is the man, because the relative follows the man's noun phrase.
Every `ke` must have a matching `ek`. Nested relatives can use `re-2` to name
the next outer head explicitly.

## Ask a question

```sh
python3 -m enkel 'ka-ob wi-eat se cat-e'
```

```text
Which object [q0] makes the following true: (for the unique cat [x1], ([x1] will eat [q0]))?
```

Use `ka` alone for yes/no questions. Use `ka-se`, `ka-ob`, `ka-to`, `ka-vi`,
`ka-at`, or `ka-on` to ask for one role. The queried role must be omitted from
the rest of the clause.

## Inspect the structure

```sh
python3 -m enkel 'du-give se teacher-u to child-u ob book-a' --format logic
python3 -m enkel 'du-give se teacher-u to child-u ob book-a' --format json
python3 -m enkel --file examples/sentences.enk --context examples/context.json
```

`logic` exposes nested operators in a compact notation. `json` includes the
surface tree, resolved meaning tree, English output, normalized source,
grammar version, and input fingerprints. The example
[scope tree](../examples/scope-tree.json) is generated from the same command.

## Use the API or install the command

```python
from enkel import Context, compile_sentence

context = Context.from_json(open('examples/context.json', encoding='utf-8').read())
result = compile_sentence('du-eat-en-ing se me ob apple-a', context)
print(result['english'])
```

```text
There is an apple [x1] such that (I [@Speaker] have been eating [x1]).
```

For an optional installed `enkel` command, use a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
enkel 'du-sleep se cat-a ma-small ma-black'
```

The runtime uses only the Python standard library. Building an installable
package uses setuptools; pip may fetch that build dependency. Running from
the repository requires neither installation nor network access.

## Vocabulary and errors

```sh
python3 -m enkel --lexicon
python3 -m unittest discover -s tests -v
```

Unknown roots and undeclared references are errors. For example,
`du-eat se he` is rejected because `he` does not identify an antecedent. Use
`re-ID` with a declaration. An error exits the CLI with status 2 and prints a
source location to stderr. File mode validates the whole batch before
printing results, so an invalid line does not produce a success-looking
partial translation.

Read [SPEC.md](SPEC.md) for the exact rules and intentional limits.
