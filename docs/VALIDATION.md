# Validation of Enkel 0.2.0

Local validation used Python 3.12.14. The complete suite passes:

```sh
python3 -m unittest discover -s tests -v
```

There are 78 test methods, including 120 generated normalization/meaning
round trips, all twelve tense/aspect combinations, all six question roles,
and explicit invalid-input cases. Parameterized cases run inside those test
methods; they are not counted as additional test methods.

The original 50 Core tests remain. Another 28 tests cover English input,
greeting conventions, all twelve tense/aspect patterns, questions, explicit
scope choices, reference context export, interpretation errors, and default
CLI routing. The exact requested `python3 -m enkel "hello world"` command is
checked for its output, success status, and empty stderr.

## What the evidence establishes

| Area | Evidence |
| --- | --- |
| Quantifier scope | A world in which each child eats a different cookie satisfies the subject-first sentence and falsifies the object-first one. |
| Three-place scope | A teacher giving different books to different children distinguishes recipient-before-object from object-before-recipient. |
| Negation | Concrete worlds separate narrow verb negation, universal-over-negation, and negation-over-universal. |
| Empty restrictions | Universal and existential readings retain their different empty-domain behavior. |
| Attachment | Instrument and head-relative telescope examples compile to different structural locations. |
| Relatives | Head restrictions filter a model domain; nested back-references identify their prescribed lexical head. |
| Reference | Two identities with the same label remain distinct; absent bindings, malformed groups, and duplicate JSON declarations fail. |
| English output | Expected agreement and irregular forms are checked; written `read` receives disambiguating tense annotations. |
| Normalization | 120 generated forms preserve both meaning tree and English rendering after normalization. |
| Command line | Example batches, JSON output, stdin, error status, and empty stdout on invalid input are checked. |
| Limits | Token size, input size, explicit negation count, and relative depth fail with controlled errors. |

The finite-world oracle is independent of the renderer and implements a
small specified fragment: present-simple singular existence, universals,
negation, and relative restrictions. It raises on unsupported operators. It
does not certify plural, definite, or temporal model evaluation, which the
production package does not provide.

## Installation smoke check

The package was built and installed into an isolated scratch target with
`pip install --no-index --no-deps --no-build-isolation`. From outside the source
directory, both the installed module and console entry point ran successfully.
This confirms the package includes the code it needs and the command entry
point resolves correctly with the installed target on Python's path.

## Continuous integration

The repository workflow runs the suite on Python 3.10, 3.12, and 3.14, then
installs the package and checks its console command, including an installed
`enkel 'hello world'` smoke check. Its declared permissions
are read-only. Action versions are pinned to full commit IDs from the official
`actions/checkout` and `actions/setup-python` repositories.

The workflow configuration is a reproducible check, not a claim that every
future run succeeds. Current results are available under the repository's
Actions tab. The structural uniqueness argument in SPEC.md remains an
informal argument; passing tests do not constitute a machine-checked proof.
