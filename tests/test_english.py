"""English input behavior, deliberate ambiguity errors, and CLI compatibility."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from enkel import Context, EnglishError, compile_sentence, translate_english

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = Context.from_json((ROOT / "examples/context.json").read_text())


def translation(text, **options):
    return translate_english(text, **options)["enkel"]


class EnglishTranslationTests(unittest.TestCase):
    def test_hello_world_exact_output(self):
        self.assertEqual(translation("hello world"), "du-greet se speaker-e ob world-e")

    def test_greetings_are_generalized_and_punctuation_tolerant(self):
        for text in ("Hello, world!", "HELLO WORLD", "hi world", "hey, world!!!"):
            with self.subTest(text=text):
                self.assertEqual(translation(text), "du-greet se speaker-e ob world-e")
        self.assertEqual(translation("hello"), "du-greet se speaker-e ob listener-e")
        self.assertEqual(translation("hello teacher"), "du-greet se speaker-e ob teacher-e")
        self.assertEqual(translation("hello everyone"), "du-greet se speaker-e ob person-u")

    def test_greeting_does_not_silently_ignore_flags(self):
        for options in ({"tense": "past"}, {"scope": "object-wide"}):
            with self.assertRaises(EnglishError):
                translation("hello world", **options)

    def test_basic_statements(self):
        examples = {
            "The cat eats a cookie.": "du-eat se cat-e ob cookie-a",
            "A dog chased the cat.": "di-chase se dog-a ob cat-e",
            "Every child sleeps.": "du-sleep se child-u",
            "The teacher gives the child a book.": "du-give se teacher-e to child-e ob book-a",
            "The teacher gives a book to the child.": "du-give se teacher-e ob book-a to child-e",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(translation(source), expected)

    def test_all_twelve_tense_aspect_combinations(self):
        examples = {
            "I ate": "di-eat", "I eat": "du-eat", "I will eat": "wi-eat",
            "I had eaten": "di-eat-en", "I have eaten": "du-eat-en", "I will have eaten": "wi-eat-en",
            "I was eating": "di-eat-ing", "I am eating": "du-eat-ing", "I will be eating": "wi-eat-ing",
            "I had been eating": "di-eat-en-ing", "I have been eating": "du-eat-en-ing", "I will have been eating": "wi-eat-en-ing",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(translation(source + " an apple"), expected + " se me ob apple-a")

    def test_negation_and_contractions(self):
        examples = {
            "The cat does not eat a cookie": "du-eat se cat-e ne ob cookie-a",
            "The cat didn't eat a cookie": "di-eat se cat-e ne ob cookie-a",
            "The cat won't eat a cookie": "wi-eat se cat-e ne ob cookie-a",
            "I'm eating an apple": "du-eat-ing se me ob apple-a",
            "I've eaten an apple": "du-eat-en se me ob apple-a",
            "I haven’t been eating an apple": "du-eat-en-ing se me ne ob apple-a",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(translation(source), expected)

    def test_adjectives_and_plural_nouns(self):
        self.assertEqual(translation("The small black cat sleeps"), "du-sleep se cat-e ma-small ma-black")
        self.assertEqual(translation("Some children sleep"), "du-sleep se child-i")
        self.assertEqual(translation("The children sleep"), "du-sleep se child-o")
        self.assertEqual(translation("No children sleep"), "du-sleep se no-child-a")

    def test_kinds_and_spatial_time_roles(self):
        self.assertEqual(translation("Water flows"), "du-flow se water")
        self.assertEqual(translation("Cats sleep"), "du-sleep se cat")
        self.assertEqual(translation("The cat sleeps in the house"), "du-sleep se cat-e at house-e")
        self.assertEqual(translation("The cat sleeps on a book"), "du-sleep se cat-e at book-a")
        self.assertEqual(translation("The cat sleeps at night"), "du-sleep se cat-e on night")

    def test_tense_homograph_requires_a_choice(self):
        with self.assertRaisesRegex(EnglishError, "more than one tense"):
            translation("I read a book")
        self.assertEqual(translation("I read a book", tense="past"), "di-read se me ob book-a")
        self.assertEqual(translation("I read a book", tense="present"), "du-read se me ob book-a")

    def test_quantifier_scope_requires_a_choice(self):
        source = "Every child eats a cookie"
        with self.assertRaisesRegex(EnglishError, "different quantifier"):
            translation(source)
        self.assertEqual(translation(source, scope="surface"), "du-eat se child-u ob cookie-a")
        self.assertEqual(translation(source, scope="object-wide"), "du-eat ob cookie-a se child-u")

    def test_negation_scope_can_be_written_explicitly(self):
        with self.assertRaises(EnglishError):
            translation("Every child does not eat a cookie")
        self.assertEqual(translation("Every child does not eat a cookie", scope="surface"), "du-eat se child-u ne ob cookie-a")
        self.assertEqual(translation("Not every child eats a cookie"), "du-eat ne se child-u ob cookie-a")

    def test_attachment_is_not_guessed(self):
        for source in ("I saw the man with the telescope", "I saw the man using a telescope", "I saw the man in the park", "I walk with the man"):
            with self.subTest(source=source), self.assertRaises(EnglishError):
                translation(source)
        self.assertEqual(translation("Using the telescope, I saw the man"), "di-see vi telescope-e se me ob man-e")
        self.assertEqual(translation("I saw the man with instrument the telescope"), "di-see se me ob man-e vi telescope-e")
        self.assertEqual(translation("At the park, I saw the man"), "di-see at park-e se me ob man-e")

    def test_pronouns_do_not_guess_groups_or_antecedents(self):
        for source in ("He sleeps", "They sleep", "We sleep", "You sleep"):
            with self.subTest(source=source), self.assertRaises(EnglishError):
                translation(source)
        self.assertEqual(translation("We sleep", context=CONTEXT), "du-sleep se we")
        self.assertEqual(translation("You sleep", context=CONTEXT), "du-sleep se yu")

    def test_speaker_context_is_exported_and_replayable(self):
        result = translate_english("I ate an apple")
        replay = compile_sentence(result["enkel"], result["context"])
        self.assertEqual(result["meaning"], replay["meaning"])
        self.assertEqual(result["context_sha256"], replay["context_sha256"])
        self.assertEqual(result["context"]["speaker"], "EnglishSpeaker")
        self.assertTrue(result["notes"])

    def test_default_speaker_never_reuses_an_unbound_entity_id(self):
        context = {"entities": {"EnglishSpeaker": {"label": "someone else"}}}
        result = translate_english("I sleep", context)
        self.assertEqual(result["context"]["speaker"], "EnglishSpeaker_")
        self.assertNotEqual(result["context"]["speaker"], "EnglishSpeaker")

    def test_duplicate_display_names_need_explicit_ids(self):
        with self.assertRaisesRegex(EnglishError, "several entities"):
            translation("John sleeps", context=CONTEXT)
        self.assertEqual(translation("@John sleeps", context=CONTEXT), "du-sleep se re-John")
        self.assertEqual(translation("@OtherJohn sleeps", context=CONTEXT), "du-sleep se re-OtherJohn")

    def test_question_forms(self):
        examples = {
            "What will the cat eat?": "ka-ob wi-eat se cat-e",
            "Does the cat eat a cookie?": "ka du-eat se cat-e ob cookie-a",
            "Didn't the cat eat a cookie?": "ka di-eat se cat-e ne ob cookie-a",
            "Has the cat eaten a cookie?": "ka du-eat-en se cat-e ob cookie-a",
            "Who saw the man?": "ka-se di-see ob man-e",
            "Who has eaten the cookie?": "ka-se du-eat-en ob cookie-e",
            "Who will eat the cookie?": "ka-se wi-eat ob cookie-e",
            "Who did the cat see?": "ka-ob di-see se cat-e",
            "Where does the cat sleep?": "ka-at du-sleep se cat-e",
            "When did the cat sleep?": "ka-on di-sleep se cat-e",
        }
        for source, expected in examples.items():
            with self.subTest(source=source):
                self.assertEqual(translation(source), expected)

    def test_generated_output_is_always_accepted_by_core(self):
        sources = ["hello world", "A cat sleeps", "The child ate the cookie", "I am eating an apple", "What will the cat eat?"]
        for source in sources:
            result = translate_english(source)
            self.assertEqual(compile_sentence(result["enkel"], result["context"])["english"], result["english"])

    def test_unsupported_english_is_rejected_without_replacement_guess(self):
        sources = ["", "hello xyzzy", "the unicorn teleports", "I am happy", "The cat fly", "a children sleep", "The cat eats cookie", "I sleep and walk", "The man who held the telescope sleeps", "The cat sleeps. The dog sleeps.", "I have a book", "I might sleep", "I sleep?"]
        for source in sources:
            with self.subTest(source=source), self.assertRaises((EnglishError, ValueError)):
                translation(source)


class EnglishCliTests(unittest.TestCase):
    def cli(self, *args, input=None):
        return subprocess.run([sys.executable, "-m", "enkel", *args], input=input, cwd=ROOT, capture_output=True, text=True)

    def test_requested_command(self):
        run = self.cli("hello world")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "du-greet se speaker-e ob world-e\n")
        self.assertEqual(run.stderr, "")

    def test_stdin_defaults_to_english_translation(self):
        run = self.cli(input="hello world")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "du-greet se speaker-e ob world-e\n")

    def test_explicit_modes_and_legacy_automatic_mode(self):
        self.assertEqual(self.cli("--from", "english", "hello world").stdout, "du-greet se speaker-e ob world-e\n")
        explicit = self.cli("--from", "enkel", "du-sleep se cat-a")
        automatic = self.cli("du-sleep se cat-a")
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertEqual(explicit.stdout, automatic.stdout)
        self.assertIn("a cat", explicit.stdout)
        self.assertEqual(self.cli("--from", "enkel", "hello world").returncode, 2)

    def test_json_contains_translation_and_context(self):
        run = self.cli("I eat an apple", "--format", "json")
        self.assertEqual(run.returncode, 0, run.stderr)
        data = json.loads(run.stdout)
        self.assertEqual(data["enkel"], "du-eat se me ob apple-a")
        self.assertIn("speaker", data["context"])
        self.assertEqual(data["input_language"], "english")

    def test_explicit_english_and_enkel_output_formats(self):
        self.assertIn("greets", self.cli("hello world", "--format", "english").stdout)
        self.assertEqual(self.cli("hello world", "--format", "enkel").stdout, "du-greet se speaker-e ob world-e\n")
        self.assertEqual(self.cli("du-sleep se cat-a", "--format", "enkel").stdout, "du-sleep se cat-a\n")

    def test_scope_error_has_no_success_output(self):
        run = self.cli("Every child eats a cookie")
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        self.assertIn("--scope surface", run.stderr)

    def test_scope_flag_selects_the_requested_translation(self):
        run = self.cli("Every child eats a cookie", "--scope", "object-wide")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "du-eat ob cookie-a se child-u\n")

    def test_batch_validation_does_not_emit_partial_results(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sentences.txt"
            path.write_text("hello world\nI might sleep\n")
            run = self.cli("--file", str(path))
        self.assertEqual(run.returncode, 2)
        self.assertEqual(run.stdout, "")
        self.assertIn(":2:", run.stderr)

    def test_malformed_enkel_never_falls_back_to_english(self):
        run = self.cli("du-eat se he")
        self.assertEqual(run.returncode, 2)
        self.assertIn("Expected a known noun", run.stderr)


if __name__ == "__main__":
    unittest.main()
