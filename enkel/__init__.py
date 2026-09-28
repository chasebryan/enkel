"""Enkel: explicit structure, one controlled-English rendering."""
from .context import Context, ContextError
from .lexicon import VERSION, digest
from .render import logic, render
from .semantics import lower
from .syntax import EnkelError, parse, serialize

__version__ = VERSION


def compile_sentence(source, context=None):
    """Parse, resolve, scope, and render one sentence. Raises on unsupported input."""
    ctx = context if isinstance(context, Context) else Context(context)
    syntax = parse(source)
    tree = lower(syntax, ctx, source)
    return {"version": VERSION, "lexicon_sha256": digest(), "context_sha256": ctx.digest(),
            "normalized": serialize(syntax), "syntax": syntax.to_dict(),
            "meaning": tree, "english": render(tree), "logic": logic(tree)}


__all__ = ["Context", "ContextError", "EnkelError", "compile_sentence", "parse", "serialize"]
