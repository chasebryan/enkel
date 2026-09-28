"""Standard-library-only CLI; errors go to stderr and never produce a guess."""
import argparse
import json
import sys
from pathlib import Path
from . import Context, ContextError, EnkelError, __version__, compile_sentence
from .lexicon import description


def main(argv=None):
    parser = argparse.ArgumentParser(description="Compile Enkel Core 0.1 to explicitly scoped English.")
    parser.add_argument("sentence", nargs="?", help="one quoted Enkel sentence; stdin if omitted")
    parser.add_argument("--file", type=Path, help="UTF-8 file: one sentence per nonblank, non-comment line")
    parser.add_argument("--context", type=Path, help="JSON entity declarations and pronoun bindings")
    parser.add_argument("--format", choices=("english", "logic", "json", "normalized"), default="english")
    parser.add_argument("--lexicon", action="store_true", help="print the pinned vocabulary and paradigms")
    parser.add_argument("--version", action="version", version="Enkel " + __version__)
    args = parser.parse_args(argv)
    if args.sentence is not None and args.file is not None:
        parser.error("choose a sentence or --file, not both")
    if args.lexicon:
        print(json.dumps(description(), indent=2, sort_keys=True))
        return 0
    try:
        context = Context(json.loads(args.context.read_text(encoding="utf-8"))) if args.context else Context()
        if args.file:
            sources = [(i, line.strip()) for i, line in enumerate(args.file.read_text(encoding="utf-8").splitlines(), 1)
                       if line.strip() and not line.lstrip().startswith("#")]
            if not sources:
                raise ValueError("Input file contains no sentences.")
        else:
            sources = [(None, args.sentence if args.sentence is not None else sys.stdin.read())]
        # Compile the complete batch before printing; a bad line cannot look like a successful partial run.
        results = []
        for line, source in sources:
            try:
                results.append(compile_sentence(source, context))
            except EnkelError as error:
                if line is not None:
                    print(f"{args.file}:{line}:", file=sys.stderr)
                raise error
        if args.format == "json":
            print(json.dumps(results if args.file else results[0], indent=2, sort_keys=True, ensure_ascii=True))
        else:
            print("\n".join(result[args.format] for result in results))
        return 0
    except (EnkelError, ContextError, OSError, ValueError, RecursionError) as error:
        print(f"enkel: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
