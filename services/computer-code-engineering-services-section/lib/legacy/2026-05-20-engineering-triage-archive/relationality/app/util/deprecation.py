from __future__ import annotations

"""Shared helpers for runtime deprecation signalling.

These functions centralise how we emit deprecation warnings so that legacy
paths in the runtime are easy to spot and can be removed systematically.
"""

from typing import Optional
import warnings


def warn_legacy_feature(name: str, detail: Optional[str] = None, *, stacklevel: int = 3) -> None:
    """Emit a deprecation warning for a legacy feature.

    Args:
        name: Short name of the deprecated feature (e.g., 'TracePoint').
        detail: Optional explanatory text.
        stacklevel: Where the warning should appear in stack traces.
    """
    message = f"{name} is deprecated and will be removed in a future revision."
    if detail:
        message = f"{message} {detail}"
    warnings.warn(message, DeprecationWarning, stacklevel=stacklevel)

