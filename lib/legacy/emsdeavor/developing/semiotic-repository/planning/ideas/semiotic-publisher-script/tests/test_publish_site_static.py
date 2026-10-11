import json
from pathlib import Path

from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator
from ssc_universe.delta import compute_delta, delta_to_dict
from ssc_universe.projections import canonical_order
from ssc_universe.projections.site_static import render_site

from support import EXAMPLES_ROOT, TEMPLATE_DIR


def test_site_static_outputs(tmp_path):
    root = EXAMPLES_ROOT
    config = UniverseConfig.load(root / "universe.yaml")
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(root)
    files, _ = render_site(instance, TEMPLATE_DIR, mathjax=False)
    names = [str(p) for p, _ in files]
    assert "index.html" in names
    assert "a.html" in names
    assert "sitemap.xml" in names
    assert any(name.startswith("tags/") for name in names)
    index_html = next(content for path, content in files if path.name == "index.html").decode("utf-8")
    assert "Page sections" in index_html
    assert "Equivalence classes" in index_html
    assert "Build metadata" in index_html
    assert "Diagnostics" in index_html
    assert "T generators" in index_html
    assert "F elements" in index_html
    assert "Ann_X(k):" in index_html
    assert "Reference graph" in index_html
    assert "Backlinks:" in index_html
    assert "unresolved-b" in index_html
    assert "b.html#unresolved-b" in index_html
    assert "Repo fingerprint" in index_html
    assert "manifest.json" in index_html
    assert "sitemap.xml" in index_html
    tag_file = next(content for path, content in files if str(path).startswith("tags/"))
    tag_html = tag_file.decode("utf-8")
    assert "T generators" in tag_html
    assert "F elements" in tag_html
    assert "Ann_X(k):" in tag_html
    b_file = next(content for path, content in files if path.name == "b.html")
    html = b_file.decode("utf-8")
    assert "b-alias" in html
    assert "status-banner" in html
    assert "build-info-b" in html
    assert "Adjacent concepts" in html
    assert "In-page navigation" in html
    assert "provenance-b" in html
    assert "Generator provenance" in html
    assert "Fragment provenance" in html
    assert "Backlinks pointing to b" in html
    assert "Unresolved references declared by b" in html
    assert ("role=\"region\" aria-labelledby=\"content-b\"" in html) or (
        "role='region' aria-labelledby='content-b'" in html
    )
    assert "Back to top" in html
    assert "@media print" in html
    assert ("id=\"content-b\"" in html) or ("id='content-b'" in html)
    assert "prefers-color-scheme" in html
    assert "viewport" in html
    assert "T_{k,X}" in html
    assert "F_{k,X}" in html
    assert "('ref', 'c')" in html or "ref', 'c'" in html
    a_file = next(content for path, content in files if path.name == "a.html")
    a_html = a_file.decode("utf-8")
    assert "Resolved references" in a_html
    assert "aria-label=\"Resolved references declared by a\"" in a_html or "resolved-a" in a_html
    assert "Backlinks: 1" in index_html
    assert "Aliases for b" in index_html or "aliases: b-alias" in index_html
    sitemap = next(content for path, content in files if path.name == "sitemap.xml").decode("utf-8")
    assert "<urlset" in sitemap
    assert "a.html" in sitemap


def test_site_static_includes_delta_panel():
    root = EXAMPLES_ROOT
    config = UniverseConfig.load(root / "universe.yaml")
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(root)
    delta = delta_to_dict(compute_delta(None, instance))
    files, _ = render_site(instance, TEMPLATE_DIR, mathjax=False, delta=delta)
    index_html = next(content for path, content in files if path.name == "index.html")
    html = index_html.decode("utf-8")
    assert "Delta summary" in html
    assert "Baseline present" in html
    assert "math-object-a" in html
    concept_html = next(content for path, content in files if path.name == "a.html").decode("utf-8")
    assert "delta-a" in concept_html
    assert "Unresolved added" in concept_html


def test_site_static_manual_fallback_keeps_style(monkeypatch):
    from ssc_universe.projections import site_static

    original_env = site_static.Environment
    monkeypatch.setattr(site_static, "Environment", None)
    try:
        root = EXAMPLES_ROOT
        config = UniverseConfig.load(root / "universe.yaml")
        evaluator = Evaluator(
            config,
            EvaluationOptions(
                mode="permissive",
                sanitize_html=True,
                html_lang=config.data.get("html", {}).get("lang", "en"),
            ),
        )
        instance = evaluator.evaluate(root)
        files, _ = site_static.render_site(instance, TEMPLATE_DIR, mathjax=False)
        html = next(content for path, content in files if path.name == "index.html").decode("utf-8")
        assert "prefers-color-scheme" in html
        assert "viewport" in html
        assert "skip-link" in html
        assert "Back to top" in html
        assert "@media print" in html
        assert "T generators" in html
        assert "F elements" in html
        assert "Ann_X(k):" in html
        assert "Equivalence classes" in html
        assert "Reference graph" in html
        assert "Page sections" in html
        assert "Build metadata" in html
        assert "manifest.json" in html
        assert "sitemap.xml" in html
        b_page = next(content for path, content in files if path.name == "b.html").decode("utf-8")
        assert "T_{k,X}" in b_page
        assert "build-info-b" in b_page
        assert "provenance-b" in b_page
        assert "Generator provenance" in b_page
        assert "manifest.json" in b_page
        a_page = next(content for path, content in files if path.name == "a.html").decode("utf-8")
        assert "Resolved references" in a_page
    finally:
        monkeypatch.setattr(site_static, "Environment", original_env)


def test_site_static_ordering_and_aliases():
    root = EXAMPLES_ROOT
    config = UniverseConfig.load(root / "universe.yaml")
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(root)

    canonical = canonical_order(instance)
    expected_order = [entry["rep"] for entry in canonical]

    files, _ = render_site(instance, TEMPLATE_DIR, mathjax=False)
    tag_files = [str(path) for path, _ in files if str(path).startswith("tags/")]
    assert tag_files == sorted(tag_files)

    index_html = next(content for path, content in files if path.name == "index.html").decode("utf-8")
    assert "aliases: b-alias" in index_html
    title_positions = [index_html.index(instance.canonical_concepts[rep].title) for rep in expected_order]
    assert title_positions == sorted(title_positions)

    b_html = next(content for path, content in files if path.name == "b.html").decode("utf-8")
    assert "Previous: Concept A" in b_html
    assert "Next: Raw HTML payload" in b_html


def test_site_static_emits_hashed_stylesheet_when_not_inline():
    root = EXAMPLES_ROOT
    config = UniverseConfig.load(root / "universe.yaml")
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(root)

    files, assets = render_site(
        instance,
        TEMPLATE_DIR,
        mathjax=False,
        assets_inline=False,
        assets_minify=True,
    )

    file_map = {str(path): content for path, content in files}
    css_assets = [name for name in file_map if name.startswith("assets/style-") and name.endswith(".css")]
    assert css_assets
    css_name = css_assets[0]
    assert assets[0]["path"] == css_name
    assert assets[0]["hash"]
    assert assets[0]["minified"] is True
    assert assets[0]["inline"] is False
    css_body = file_map[css_name].decode("utf-8")
    assert "\n" not in css_body

    search_assets = [name for name in file_map if name.startswith("search-index-") and name.endswith(".json")]
    assert search_assets
    search_name = search_assets[0]
    assert any(asset.get("path") == search_name and asset.get("kind") == "search-index" for asset in assets)
    search_data = json.loads(file_map[search_name].decode("utf-8"))
    assert any(entry["const"] == "a" for entry in search_data)
    assert all("status" in entry for entry in search_data)
    assert all("publish_to" in entry for entry in search_data)

    sitemap_entry = next((asset for asset in assets if asset.get("kind") == "sitemap"), None)
    assert sitemap_entry is not None
    assert sitemap_entry["path"] == "sitemap.xml"
    sitemap_body = file_map["sitemap.xml"].decode("utf-8")
    assert "<urlset" in sitemap_body

    index_html = file_map["index.html"].decode("utf-8")
    assert css_name in index_html
    assert "concept-search" in index_html
    assert "search-status" in index_html
    assert "search-status-filter" in index_html
    assert "search-target-filter" in index_html
    assert search_name in index_html or "data-index" in index_html

    tag_entry = next((name for name in file_map if name.startswith("tags/")), None)
    assert tag_entry is not None
    tag_html = file_map[tag_entry].decode("utf-8")
    assert "../" in tag_html and css_name in tag_html


def test_site_static_lang_from_config():
    root = EXAMPLES_ROOT
    config = UniverseConfig.load(root / "universe.yaml")
    config.data.setdefault("html", {})["lang"] = "es"
    evaluator = Evaluator(
        config,
        EvaluationOptions(
            mode="permissive",
            sanitize_html=True,
            html_lang=config.data.get("html", {}).get("lang", "en"),
        ),
    )
    instance = evaluator.evaluate(root)

    files, _ = render_site(instance, TEMPLATE_DIR, mathjax=False)
    index_html = next(content for path, content in files if path.name == "index.html").decode("utf-8").lower()
    assert "<html lang=\"es\"" in index_html or "<html lang='es'" in index_html
