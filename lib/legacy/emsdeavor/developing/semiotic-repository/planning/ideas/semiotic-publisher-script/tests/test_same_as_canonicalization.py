from pathlib import Path

from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator
from ssc_universe.projections.site_static import render_site

from support import TEMPLATE_DIR


def _write_concept(path: Path, frontmatter: str, body: str = ""):
    path.write_text(frontmatter + "\n\n" + body, encoding="utf-8")


def test_same_as_concepts_merge_to_representative(tmp_path):
    content_dir = tmp_path / "content"
    content_dir.mkdir()
    _write_concept(
        content_dir / "a.md",
        "---\nid: a\ntitle: Primary A\ntags: [alpha]\nann:\n  - {key: level, value: 1}\nsame_as: [a-alt]\n---",
        "Primary body",
    )
    _write_concept(
        content_dir / "a-alt.md",
        "---\nid: a-alt\ntitle: Alt A\ntags: [beta]\nann:\n  - tag:alt\nsame_as: [a]\n---",
        "Alternate body should not override",
    )
    config_path = tmp_path / "universe.yaml"
    config_path.write_text("sources: content/*.md\n", encoding="utf-8")

    config = UniverseConfig.load(config_path)
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(tmp_path)

    # Representatives should collapse to the lexicographic leader "a".
    assert set(instance.canonical_concepts.keys()) == {"a"}
    canonical = instance.canonical_concepts["a"]
    assert canonical.tags == ["alpha", "beta"]
    # Both annotation lists should be preserved for fragment generation.
    assert len(canonical.ann) == 2
    # The primary representative's body and title should anchor the aggregate concept.
    assert canonical.title == "Primary A"
    assert "Primary body" in canonical.body

    # Fragments and reference graph should be keyed by the representative only.
    assert set(instance.fragments.keys()) == {"a"}
    assert set(instance.reference_graph.keys()) == {"a"}

    files, _ = render_site(instance, TEMPLATE_DIR, mathjax=False)
    anchors = [p.name for p, _ in files if p.suffix == ".html" and p.name not in {"index.html"}]
    assert anchors.count("a.html") == 1
