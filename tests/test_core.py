"""Behavioral conformance and finite-world counterexamples; standard library only."""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import unittest

from enkel import Context, ContextError, EnkelError, compile_sentence, parse, serialize
from enkel.lexicon import VERBS

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = json.loads((ROOT / "examples/context.json").read_text())


def compiled(source, context=CONTEXT):
    return compile_sentence(source, context)


def atom(node):
    while node["type"] in ("bind", "not"):
        node = node["body"]
    return node


def finite_truth(source, domains, facts):
    """Independent test oracle for singular exists/every/not and relative restrictions.

    Facts are (verb root, sorted role/entity pairs). These fixtures use present,
    simple clauses; this is deliberately not a general temporal model checker.
    Unsupported forms raise instead of receiving invented semantics.
    """
    meaning = compile_sentence(source)["meaning"]
    if meaning["type"] != "statement":
        raise ValueError("Test oracle expects a statement")

    def evaluate(node, env):
        if node["type"] == "not":
            return not evaluate(node["body"], env)
        if node["type"] == "bind":
            q, r, variable = node["quantifier"], node["restriction"], node["variable"]["name"]
            if q not in ("every", "exists") or r["adjectives"]:
                raise ValueError("Unsupported oracle binder")
            candidates = []
            for value in domains.get(r["noun"], ()):
                nested = {**env, variable: value}
                if all(evaluate(relative, nested) for relative in r["relatives"]):
                    candidates.append(nested)
            values = [evaluate(node["body"], nested) for nested in candidates]
            return all(values) if q == "every" else any(values)
        verb = node["verb"]
        if verb["tense"] != "du" or verb["perfect"] or verb["progressive"]:
            raise ValueError("Unsupported oracle tense/aspect")
        roles = []
        for role, term in node["roles"].items():
            if term["type"] != "variable":
                raise ValueError("Unsupported oracle term")
            roles.append((role, env[term["name"]]))
        return (verb["root"], tuple(sorted(roles))) in facts
    return evaluate(meaning["body"], {})


def fact(verb, **roles):
    return verb, tuple(sorted(roles.items()))


class ScopeTests(unittest.TestCase):
    def test_original_scope_outputs(self):
        self.assertEqual(compiled("du-eat se child-u ob cookie-a")["english"],
                         "For every child [x1], (there is a cookie [x2] such that ([x1] eats [x2])).")
        self.assertEqual(compiled("du-eat ob cookie-a se child-u")["english"],
                         "There is a cookie [x1] such that (for every child [x2], ([x2] eats [x1])).")

    def test_different_cookies_and_one_shared_cookie_are_distinct(self):
        domains = {"child": ["Ada", "Bea"], "cookie": ["c1", "c2"]}
        facts = {fact("eat", se="Ada", ob="c1"), fact("eat", se="Bea", ob="c2")}
        self.assertTrue(finite_truth("du-eat se child-u ob cookie-a", domains, facts))
        self.assertFalse(finite_truth("du-eat ob cookie-a se child-u", domains, facts))

    def test_subject_first_does_not_erase_recipient_scope(self):
        domains = {"teacher": ["T"], "child": ["Ada", "Bea"], "book": ["b1", "b2"]}
        facts = {fact("give", se="T", to="Ada", ob="b1"), fact("give", se="T", to="Bea", ob="b2")}
        self.assertTrue(finite_truth("du-give se teacher-u to child-u ob book-a", domains, facts))
        self.assertFalse(finite_truth("du-give se teacher-u ob book-a to child-u", domains, facts))

    def test_all_three_binder_permutations_remain_in_source_order(self):
        pairs = (("se", "teacher-u"), ("ob", "book-a"), ("to", "child-u"))
        for order in itertools.permutations(pairs):
            source = "du-give " + " ".join(r + " " + n for r, n in order)
            body = compiled(source)["meaning"]["body"]
            actual = []
            while body["type"] == "bind":
                actual.append(body["restriction"]["noun"])
                body = body["body"]
            self.assertEqual(actual, [n.split("-")[0] for _, n in order])

    def test_no_prefix_is_inside_local_binders(self):
        body = compiled("no-du-eat se child-u ob cookie-a")["meaning"]["body"]
        self.assertEqual(body["quantifier"], "every")
        self.assertEqual(body["body"]["quantifier"], "exists")
        self.assertEqual(body["body"]["body"]["type"], "not")

    def test_narrow_negation_is_not_no_child(self):
        domains = {"child": ["Ada", "Bea"], "cookie": ["c1", "c2"]}
        facts = {fact("eat", se="Ada", ob="c1"), fact("eat", se="Bea", ob="c2")}
        self.assertTrue(finite_truth("no-du-eat se child-u ob cookie-a", domains, facts))
        self.assertFalse(finite_truth("du-eat se child-u ne ob cookie-a", domains, facts))

    def test_not_every_is_not_no_child(self):
        domains = {"child": ["Ada", "Bea"], "cookie": ["c1"]}
        facts = {fact("eat", se="Ada", ob="c1")}
        self.assertTrue(finite_truth("du-eat ne se child-u ob cookie-a", domains, facts))
        self.assertFalse(finite_truth("du-eat se child-u ne ob cookie-a", domains, facts))

    def test_nominal_no_expands_at_its_written_position(self):
        a = compiled("du-eat se child-u ob no-cookie-a")
        b = compiled("du-eat se child-u ne ob cookie-a")
        self.assertEqual(a["meaning"], b["meaning"])
        self.assertEqual(a["english"], b["english"])

    def test_empty_domains_obey_explicit_scope(self):
        domains = {"child": [], "cookie": []}
        self.assertTrue(finite_truth("du-eat se child-u ob cookie-a", domains, set()))
        self.assertFalse(finite_truth("du-eat ob cookie-a se child-u", domains, set()))

    def test_double_negation_is_explicit(self):
        source = "du-eat ne ne se child-u ob cookie-a"
        tree = compiled(source)["meaning"]["body"]
        self.assertEqual(tree["type"], "not")
        self.assertEqual(tree["body"]["type"], "not")


class AttachmentTests(unittest.TestCase):
    def test_instrument_and_relative_have_different_structures(self):
        instrument = compiled("di-see se me ob man-e vi telescope-e")["meaning"]["body"]
        relative = compiled("di-see se me ob man-e ke di-hold se re ob telescope-e ek")["meaning"]["body"]
        self.assertIn("vi", atom(instrument)["roles"])
        self.assertNotIn("vi", atom(relative)["roles"])
        restriction = relative["restriction"]["relatives"][0]
        self.assertEqual(atom(restriction)["verb"]["root"], "hold")
        self.assertEqual(atom(restriction)["roles"]["se"]["name"], relative["variable"]["name"])

    def test_relative_filters_the_head_domain(self):
        domains = {"man": ["M1", "M2"], "book": ["B"]}
        facts = {fact("hold", se="M1", ob="B"), fact("sleep", se="M2")}
        source = "du-sleep se man-a ke du-hold se re ob book-a ek"
        self.assertFalse(finite_truth(source, domains, facts))
        facts.add(fact("sleep", se="M1"))
        self.assertTrue(finite_truth(source, domains, facts))

    def test_nested_outer_binding_is_lexical(self):
        source = "di-see se me ob man-a ke di-see se re ob woman-a ke di-help se re ob re-2 ek ek"
        outer = compiled(source)["meaning"]["body"]
        woman = outer["restriction"]["relatives"][0]
        help_atom = woman["restriction"]["relatives"][0]
        self.assertEqual(help_atom["roles"]["se"]["name"], "x2")
        self.assertEqual(help_atom["roles"]["ob"]["name"], "x1")

    def test_relative_with_head_in_object_role(self):
        result = compiled("du-sleep se man-a ke di-see se me ob re ek")
        relative = result["meaning"]["body"]["restriction"]["relatives"][0]
        self.assertEqual(relative["roles"]["ob"]["name"], "x1")

    def test_repeated_relatives_attach_to_same_head(self):
        body = compiled("du-sleep se man-a ke du-read se re ek ke du-walk se re ek")["meaning"]["body"]
        self.assertEqual(len(body["restriction"]["relatives"]), 2)
        for relative in body["restriction"]["relatives"]:
            self.assertEqual(relative["roles"]["se"]["name"], "x1")

    def test_modifiers_stay_with_their_noun(self):
        body = compiled("di-see se me ob cat-a ma-small ma-black")["meaning"]["body"]
        self.assertEqual(body["restriction"]["adjectives"], ["small", "black"])
        self.assertIn("small black cat", compiled("du-sleep se cat-a ma-small ma-black")["english"])


class ReferenceTests(unittest.TestCase):
    def test_same_display_name_does_not_merge_ids(self):
        a = compiled("di-see se re-John ob re-OtherJohn")["meaning"]["body"]
        self.assertEqual(a["roles"]["se"]["label"], a["roles"]["ob"]["label"])
        self.assertNotEqual(a["roles"]["se"]["id"], a["roles"]["ob"]["id"])

    def test_unresolved_name_is_rejected(self):
        with self.assertRaises(EnkelError):
            compiled("du-sleep se re-Unknown")

    def test_pronoun_needs_a_context(self):
        with self.assertRaises(EnkelError):
            compile_sentence("du-sleep se me")

    def test_we_has_explicit_membership(self):
        body = compiled("du-sleep se we")["meaning"]["body"]
        self.assertEqual(body["roles"]["se"]["id"], "Team")
        self.assertEqual(body["roles"]["se"]["number"], "plural")

    def test_group_must_include_speaker(self):
        context = copy.deepcopy(CONTEXT)
        context["entities"]["Team"]["members"] = ["John", "Reader"]
        with self.assertRaises(ContextError):
            Context(context)

    def test_context_rejects_malformed_declarations(self):
        invalid = [[], {"mystery": 1}, {"entities": []}, {"speaker": "Absent"},
                   {"entities": {"john": {"label": "John"}}},
                   {"entities": {"A": {"label": "A", "number": "plural", "members": ["B"]}}}]
        for context in invalid:
            with self.subTest(context=context), self.assertRaises(ContextError):
                Context(context)

    def test_context_hash_is_insensitive_to_json_key_order(self):
        reordered = dict(reversed(list(CONTEXT.items())))
        self.assertEqual(Context(CONTEXT).digest(), Context(reordered).digest())

    def test_json_context_rejects_duplicate_ids_and_fields(self):
        for source in ('{"speaker":"John","speaker":"OtherJohn"}',
                       '{"entities":{"John":{"label":"John"},"John":{"label":"Other"}}}',
                       '{"entities":{"John":{"label":"John","label":"Other"}}}'):
            with self.subTest(source=source), self.assertRaises(ContextError):
                Context.from_json(source)

    def test_quoted_display_labels_cannot_inject_scope(self):
        context = {"entities": {"A": {"label": 'John) such that ("'}}}
        output = compiled("du-sleep se re-A", context)["english"]
        self.assertIn(json.dumps(context["entities"]["A"]["label"]), output)


class MorphologyTests(unittest.TestCase):
    def test_all_twelve_tense_aspect_forms(self):
        expected = {
            "di-eat": "ate", "du-eat": "eat", "wi-eat": "will eat",
            "di-eat-en": "had eaten", "du-eat-en": "have eaten", "wi-eat-en": "will have eaten",
            "di-eat-ing": "was eating", "du-eat-ing": "am eating", "wi-eat-ing": "will be eating",
            "di-eat-en-ing": "had been eating", "du-eat-en-ing": "have been eating", "wi-eat-en-ing": "will have been eating",
        }
        for form, english in expected.items():
            with self.subTest(form=form):
                self.assertEqual(compiled(form + " se me")["english"], "I [@Speaker] " + english + ".")

    def test_third_singular_and_plural_agreement(self):
        self.assertIn("[x1] eats", compiled("du-eat se cat-a")["english"])
        self.assertIn("[x1] eat)", compiled("du-eat se cat-i")["english"])
        self.assertIn("[x1] has eaten", compiled("du-eat-en se cat-a")["english"])
        self.assertEqual(compiled("du-eat-en se we")["english"], "We [@Team] have eaten.")

    def test_second_person_progressive(self):
        self.assertEqual(compiled("di-eat-ing se yu")["english"], "You [@Reader] were eating.")

    def test_subject_and_object_pronoun_forms(self):
        self.assertEqual(compiled("di-see se me ob we")["english"], "I [@Speaker] saw us [@Team].")

    def test_irregular_plural(self):
        self.assertIn("children", compiled("du-sleep se child-i")["english"])

    def test_a_an_uses_initial_sound(self):
        self.assertIn("an apple", compiled("du-eat se me ob apple-a")["english"])
        self.assertIn("an hour", compiled("du-sleep se me on hour-a")["english"])
        self.assertIn("a young", compiled("du-sleep se child-a ma-young")["english"])

    def test_read_homograph_keeps_tense_visible(self):
        past = compiled("di-read se me")["english"]
        present = compiled("du-read se me")["english"]
        self.assertNotEqual(past, present)
        self.assertIn("past tense", past)
        self.assertIn("present tense", present)

    def test_kind_term_does_not_create_a_quantifier(self):
        body = compiled("du-flow se water")["meaning"]["body"]
        self.assertEqual(body["type"], "predicate")
        self.assertEqual(body["roles"]["se"]["type"], "kind")

    def test_definites_and_pluralities_have_distinct_operators(self):
        for suffix, kind in (("a", "exists"), ("e", "definite"), ("i", "exists_plural"), ("o", "definite_plural"), ("u", "every")):
            self.assertEqual(compiled("du-sleep se cat-" + suffix)["meaning"]["body"]["quantifier"], kind)


class QuestionTests(unittest.TestCase):
    def test_yes_no_wraps_the_whole_scoped_clause(self):
        tree = compiled("ka du-eat se child-u ob cookie-a")["meaning"]
        self.assertEqual(tree["type"], "yes_no")
        self.assertEqual(tree["body"]["quantifier"], "every")

    def test_object_question_fills_the_missing_role(self):
        result = compiled("ka-ob wi-eat se cat-e")
        self.assertEqual(result["meaning"]["role"], "ob")
        self.assertEqual(atom(result["meaning"]["body"])["roles"]["ob"]["name"], "q0")

    def test_subject_question_needs_no_overt_subject(self):
        self.assertEqual(compiled("ka-se du-sleep")["meaning"]["body"]["roles"]["se"]["name"], "q0")

    def test_wh_scope_is_outside_local_quantifiers(self):
        tree = compiled("ka-ob du-eat se child-u")["meaning"]
        self.assertEqual(tree["type"], "wh")
        self.assertEqual(tree["body"]["quantifier"], "every")

    def test_all_six_query_roles(self):
        for role in ("se", "ob", "to", "vi", "at", "on"):
            source = "ka-" + role + " du-give " + " ".join(r + " re-John" for r in ("se", "ob", "to") if r != role)
            self.assertEqual(compiled(source)["meaning"]["role"], role)


class RejectionTests(unittest.TestCase):
    def test_invalid_forms_fail_closed(self):
        invalid = ["", "eat se cat-a", "du-eat", "du-eat se cat-a se dog-a",
                   "du-eat se cat-a ob", "du-eat se unicorn-a", "du-teleport se cat-a",
                   "du-eat-ing-en se cat-a", "du-eat se no-cat-u", "du-eat se he",
                   "du-eat se re", "du-eat se re-1", "du-eat se cat-a red",
                   "du-eat se cat-a ma-invisible", "du-eat se water-a", "du-eat se water-e",
                   "ka-ob du-eat se cat-a ob cookie-a", "ka ka-ob du-eat se cat-a",
                   "du-give se cat-a ob book-a", "du-sleep se cat-a ob dog-a",
                   "du-eat se cat-a ek", "du-eat se cat-a ke du-sleep se re",
                   "du-eat se cat-a ke du-sleep se me ek",
                   "du-eat se cat-a ke du-sleep se re-2 ek",
                   "du-eat se cat-a ke ka du-sleep se re ek",
                   "du-eat se cat-a ke du-sleep se re ek ma-black",
                   "du-eat se re-John ma-black", "du-eat se cat-a?", "ka du-eat se cat-a.",
                   "du-eat se cat-a. du-sleep se dog-a", "du-eat se cat-a;", "du-eat se cat–a"]
        for source in invalid:
            with self.subTest(source=source), self.assertRaises(EnkelError):
                compiled(source)

    def test_diagnostics_locate_the_error(self):
        with self.assertRaises(EnkelError) as caught:
            compiled("du-eat\nse unknown-a")
        self.assertIn("line 2, column 4", str(caught.exception))

    def test_resource_limits_have_controlled_errors(self):
        for source in ("du-eat " + "ne " * 129 + "se cat-a", "a" * 129, " " * 65537):
            with self.assertRaises(EnkelError):
                compiled(source)

    def test_nesting_limit(self):
        source = "du-sleep se cat-a " + "ke du-see se re ob cat-a " * 25 + "ek " * 25
        with self.assertRaises(EnkelError):
            compiled(source)


class DeterminismAndCliTests(unittest.TestCase):
    def test_generated_roundtrips_preserve_meaning(self):
        count = 0
        for tense, suffix, det in itertools.product(("di", "du", "wi"), ("", "-en", "-ing", "-en-ing"), "aeiou"):
            for order in (("se child-" + det, "ob cookie-a"), ("ob cookie-a", "se child-" + det)):
                source = tense + "-eat" + suffix + " " + " ".join(order)
                first = compiled(source)
                second = compiled(serialize(parse("  " + source + " .  ")))
                self.assertEqual(first["meaning"], second["meaning"])
                self.assertEqual(first["english"], second["english"])
                count += 1
        self.assertEqual(count, 120)

    def test_same_input_has_identical_json(self):
        source = "di-see se me ob man-a ke du-sleep se re ek"
        self.assertEqual(json.dumps(compiled(source), sort_keys=True), json.dumps(compiled(source), sort_keys=True))

    def test_lexicon_and_context_fingerprints(self):
        result = compiled("du-sleep se me")
        for key in ("lexicon_sha256", "context_sha256"):
            self.assertRegex(result[key], r"^[0-9a-f]{64}$")

    def test_examples_compile_as_a_batch(self):
        run = subprocess.run([sys.executable, "-m", "enkel", "--file", "examples/sentences.enk", "--context", "examples/context.json", "--format", "json"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(len(json.loads(run.stdout)), 18)

    def test_cli_invalid_input_has_exit_two_and_no_stdout(self):
        run = subprocess.run([sys.executable, "-m", "enkel", "du-eat se he"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        self.assertIn("Expected", run.stderr)

    def test_cli_stdin(self):
        run = subprocess.run([sys.executable, "-m", "enkel"], input="du-sleep se cat-a", cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("a cat", run.stdout)

    def test_terminal_punctuation_and_re_one_normalize(self):
        source = "  du-sleep se cat-a ke du-walk se re-1 ek.  "
        self.assertEqual(serialize(parse(source)), "du-sleep se cat-a ke du-walk se re ek")


if __name__ == "__main__":
    unittest.main()
