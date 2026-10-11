"""
Relational Computer core package.

Proof engine and graph for relational mathematics programs, focused on
mathematical reasoning and proof production within a differential calculus
modulo syntax.

This package materializes the acts-specified structures using only canonical
JSON carriers, schema validation, and pure realizers operating over the AOG.
All helpers here are intentionally minimal; they exist only to enforce the
mathematical laws and serialization discipline described in the repository
documentation.
"""

__all__ = [
    "canonical",
    "schemas",
    "validation",
]
