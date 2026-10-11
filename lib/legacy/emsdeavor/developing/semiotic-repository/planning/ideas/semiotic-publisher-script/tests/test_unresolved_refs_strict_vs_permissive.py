from pathlib import Path
import pytest

from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator

from support import EXAMPLES_ROOT


def test_permissive_allows_unresolved():
    config = UniverseConfig.load(EXAMPLES_ROOT / "universe.yaml")
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(EXAMPLES_ROOT)
    assert instance.unresolved


def test_strict_rejects_unresolved():
    config = UniverseConfig.load(EXAMPLES_ROOT / "universe.yaml")
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="strict",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    with pytest.raises(ValueError) as excinfo:
        evaluator.evaluate(EXAMPLES_ROOT)
    assert "content/b.md" in str(excinfo.value)
