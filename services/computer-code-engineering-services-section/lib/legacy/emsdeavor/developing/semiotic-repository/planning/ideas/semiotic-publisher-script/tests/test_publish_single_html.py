from pathlib import Path

from ssc_universe.config import UniverseConfig
from ssc_universe.delta import compute_delta, delta_to_dict
from ssc_universe.eval_core import EvaluationOptions, Evaluator
from ssc_universe.projections.single_html import render_single
from ssc_universe.projections.styles import base_stylesheet

from support import EXAMPLES_ROOT, TEMPLATE_DIR


def test_single_html_contains_anchor(tmp_path):
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
    delta = delta_to_dict(compute_delta(None, instance))
    name, content = render_single(
        instance,
        TEMPLATE_DIR,
        mathjax=False,
        delta=delta,
        manifest_href="manifest.json",
    )
    html = content.decode("utf-8")
    assert name == "single.html"
    assert html.lower().count("<html") == 1
    assert "Document outline" in html
    assert "Build metadata" in html
    assert "manifest.json" in html
    assert "Equivalence classes" in html
    assert (
        "section id='a'" in html
        or "section id=\"a\"" in html
        or "article id='a'" in html
        or "article id=\"a\"" in html
    )
    assert "sscu-manifest" in html
    assert "Equivalent IDs" in html and "b-alias" in html
    assert "Delta summary" in html
    assert "baseline" in html.lower()
    assert "delta-a" in html
    assert "status-banner" in html
    assert "Adjacent concepts" in html
    assert "In-page navigation" in html
    assert "Backlinks pointing to b" in html
    assert "Unresolved references declared by b" in html
    assert ("role=\"region\" aria-labelledby=\"content-a\"" in html) or (
        "role='region' aria-labelledby='content-a'" in html
    )
    assert "Back to top" in html
    assert "@media print" in html
    assert ("id=\"content-a\"" in html) or ("id='content-a'" in html)
    assert "prefers-color-scheme" in html
    assert "viewport" in html
    assert "concept-chip" in html
    assert "Ann_X(k):" in html
    assert "Repo fingerprint" in html
    assert "T_{k,X} generators" in html
    assert "F_{k,X} fragment elements" in html
    assert "provenance-a" in html
    assert "Generator provenance" in html
    assert "Resolved references" in html
    assert "Reference graph" in html
    assert "concept-search" in html
    assert "search-status" in html
    assert "search-data" in html
    assert "search-status-filter" in html
    assert "search-target-filter" in html
    assert "reference-graph" in html


def test_single_html_manual_fallback_keeps_style(monkeypatch):
    from ssc_universe.projections import single_html

    original_env = single_html.Environment
    monkeypatch.setattr(single_html, "Environment", None)
    try:
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
        name, html_bytes = single_html.render_single(
            instance,
            TEMPLATE_DIR,
            mathjax=False,
            manifest_href="manifest.json",
        )
        html = html_bytes.decode("utf-8")
        assert name == "single.html"
        assert "prefers-color-scheme" in html
        assert "viewport" in html
        assert "skip-link" in html
        assert "Back to top" in html
        assert "@media print" in html
        assert "concept-chip" in html
        assert "Ann_X(k):" in html
        assert "Build metadata" in html
        assert "manifest.json" in html
        assert "Equivalence classes" in html
        assert "T_{k,X} generators" in html
        assert "F_{k,X} fragment elements" in html
        assert "provenance-a" in html or "provenance-b" in html
        assert "Generator provenance" in html
        assert "Resolved references" in html
        assert "Reference graph" in html
        assert "concept-search" in html
        assert "search-data" in html
        assert "search-status-filter" in html
        assert "search-target-filter" in html
    finally:
        monkeypatch.setattr(single_html, "Environment", original_env)


def test_single_html_minify_inline_styles():
    config = UniverseConfig.load(EXAMPLES_ROOT / "universe.yaml")
    config.data.setdefault("html", {}).setdefault("assets", {})["minify"] = True
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(EXAMPLES_ROOT)
    minified_css = base_stylesheet(minify=True)
    name, html_bytes = render_single(
        instance,
        TEMPLATE_DIR,
        mathjax=False,
        delta=delta_to_dict(compute_delta(None, instance)),
        assets_minify=True,
    )
    html = html_bytes.decode("utf-8")
    assert name == "single.html"
    assert f"<style>{minified_css}</style>" in html


def test_single_html_lang_from_config():
    config = UniverseConfig.load(EXAMPLES_ROOT / "universe.yaml")
    config.data.setdefault("html", {})["lang"] = "fr"
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(EXAMPLES_ROOT)
    name, html_bytes = render_single(instance, TEMPLATE_DIR, mathjax=False)
    html = html_bytes.decode("utf-8").lower()
    assert name == "single.html"
    assert "<html lang=\"fr\"" in html or "<html lang='fr'" in html
