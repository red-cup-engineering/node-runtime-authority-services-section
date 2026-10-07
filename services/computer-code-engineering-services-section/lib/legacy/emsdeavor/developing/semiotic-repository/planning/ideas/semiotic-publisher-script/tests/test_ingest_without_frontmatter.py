from pathlib import Path

from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator


def test_ingests_markdown_without_frontmatter(tmp_path: Path):
    md = tmp_path / "concept.md"
    md.write_text("# Hello\n\nBody\n", encoding="utf-8")
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
    assert "concept" in instance.concepts
    concept = instance.concepts["concept"]
    assert concept.title == "Hello"
    assert concept.endogenous == {}
    assert concept.exogenous["path"] == "concept.md"

