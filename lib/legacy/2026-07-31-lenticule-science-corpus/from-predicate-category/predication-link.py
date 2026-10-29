"""Decorator + registry layer linking Python objects to corpus markdown notes.

Three decorators establish bidirectional Python ↔ markdown links:

- `@defines("objects/X.md")` — Python class/function realizes the mathematical
  content of an object/morphism note.
- `@verifies("examples/X.md", **kw)` — function computationally verifies a
  claim in a note. Function should also be named `test_*` for pytest discovery.
- `@example_of("theorems/X.md", **kw)` — function computes a concrete instance
  of a theorem.

Decorators register-only. They do not run, validate, or modify their target.
Execution is via pytest discovery; metadata coherence is via `validate.py`.

The registry is a process-global list; importing a module triggers registration
of its decorated functions/classes. To force registration of every link,
import every per-note module — `validate.py` does this by walking the package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class Link:
    """A single registered Python ↔ markdown link.

    Attributes:
        kind: One of "defines", "verifies", "example_of".
        target: Markdown note slug, e.g. "examples/per-fiber-d-frame-curry-on-belnap-fiber.md".
        obj: The Python object (class or function) that was decorated.
        metadata: Frozen tuple of extra kwargs from the decorator (e.g. pass_=1).
    """

    kind: str
    target: str
    obj: Any
    metadata: tuple[tuple[str, Any], ...]


_REGISTRY: list[Link] = []


def _register(kind: str, target: str, obj: Any, **kwargs: Any) -> Any:
    metadata = tuple(sorted(kwargs.items()))
    _REGISTRY.append(Link(kind=kind, target=target, obj=obj, metadata=metadata))
    return obj


def defines(target: str, **kwargs: Any) -> Callable[[Any], Any]:
    """Mark a Python class/function as defining the mathematical content of a note.

    Typically applied to primitive classes (Bilattice, Frame, DFrame) whose
    target is an `objects/X.md` or `morphisms/X.md` note.
    """

    def decorator(obj: Any) -> Any:
        return _register("defines", target, obj, **kwargs)

    return decorator


def verifies(target: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a function as computationally verifying a claim in a note.

    For pytest discovery to pick the function up automatically, name it
    `test_*`. The decorator only registers metadata; it does not modify
    the function or affect execution.

    Useful kwargs: `pass_=N` for multi-pass examples, `claim="..."` for
    a one-line description of what's being verified.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return _register("verifies", target, func, **kwargs)

    return decorator


def example_of(target: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a function as computing a concrete instance of a theorem.

    Useful kwargs: `instance="triangle_graph"` to identify which instance.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return _register("example_of", target, func, **kwargs)

    return decorator


def all_links() -> list[Link]:
    """Return a snapshot of every registered link."""

    return list(_REGISTRY)


def links_for(target: str) -> list[Link]:
    """Return all links targeting a given markdown note slug."""

    return [link for link in _REGISTRY if link.target == target]


def reset_registry() -> None:
    """Clear the registry. Used by tests; not for production use."""

    _REGISTRY.clear()
