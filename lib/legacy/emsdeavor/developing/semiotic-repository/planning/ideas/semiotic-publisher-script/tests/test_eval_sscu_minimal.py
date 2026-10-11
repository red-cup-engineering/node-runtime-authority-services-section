from pathlib import Path

from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator


def test_failure_fragment_collapse(tmp_path):
    md = tmp_path / "concept.md"
    md.write_text(
        "---\nid: x\ntitle: X\nann:\n  - {unexpected: true}\n---\n\nBody\n",
        encoding="utf-8",
    )
    config = UniverseConfig.load(None)
    config.data["sources"] = "**/*.md"
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(tmp_path)
    fragment = list(instance.fragments.values())[0]
    assert fragment.is_failure
    assert {"⊥_fail"} <= set(fragment.elements)
