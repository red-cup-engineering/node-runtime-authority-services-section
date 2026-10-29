"""Pytest configuration for the predication_categories package.

The `verifies`/`example_of`/`defines` decorators register only — they do
not execute. Pytest finds the verification functions via standard `test_*`
naming convention. This conftest file just ensures the package is importable
when pytest is run from this directory.
"""

import sys
from pathlib import Path

# Ensure the package's parent directory is on sys.path so `import
# predication_categories` works when pytest is run from inside this dir.
_PARENT = Path(__file__).parent.parent.resolve()
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))
