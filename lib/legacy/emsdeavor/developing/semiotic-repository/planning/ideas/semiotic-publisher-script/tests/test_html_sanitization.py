from pathlib import Path

from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator
from ssc_universe.projections.single_html import render_single

from support import EXAMPLES_ROOT, TEMPLATE_DIR


def test_default_sanitization_strips_scripts():
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
    _, content = render_single(instance, TEMPLATE_DIR, mathjax=False)
    html = content.decode("utf-8")
    assert "<script>alert('xss')</script>" not in html


def test_sanitization_can_be_disabled():
    config = UniverseConfig.load(EXAMPLES_ROOT / "universe.yaml")
    config.data.setdefault("html", {})["sanitize"] = False
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=False,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(EXAMPLES_ROOT)
    _, content = render_single(instance, TEMPLATE_DIR, mathjax=False)
    html = content.decode("utf-8")
    assert "<script>alert('xss')</script>" in html
