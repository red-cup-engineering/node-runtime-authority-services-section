from pathlib import Path

from ssc_universe.cli import build_manifest
from ssc_universe.config import UniverseConfig
from ssc_universe.eval_core import EvaluationOptions, Evaluator
from ssc_universe.projections.filtering import published_representatives
from ssc_universe.projections.site_static import render_site

from support import TEMPLATE_DIR


def test_publish_filters_limit_static_site(tmp_path):
    cfg_path = tmp_path / "emsenn-net.universe.yaml"
    cfg_path.write_text(
        """
sources: "*.md"
publish:
  filters:
    publish_to: [emsenn-net]
    status: [public]
html:
  lang: en
  assets:
    inline: true
    minify: false
cache:
  enabled: false
"""
    )

    (tmp_path / "public.md").write_text(
        """---
id: public-const
title: Public Concept
status: public
publish_to: [emsenn-net]
ann: []
---
Body
"""
    )
    (tmp_path / "private.md").write_text(
        """---
id: private-const
title: Private Concept
status: draft
publish_to: [other-site]
ann: []
---
Body
"""
    )

    config = UniverseConfig.load(cfg_path)
    evaluator = Evaluator(
        config,
        EvaluationOptions(mode="permissive", sanitize_html=True, html_lang=config.data.get("html", {}).get("lang", "en")),
    )
    instance = evaluator.evaluate(tmp_path)
    include = published_representatives(
        instance,
        publish_to=config.publish_filters().get("publish_to"),
        statuses=config.publish_filters().get("status"),
    )
    assert include == {"public-const"}

    files, assets = render_site(
        instance,
        TEMPLATE_DIR,
        mathjax=False,
        include=sorted(include),
    )
    names = {str(path) for path, _ in files}
    assert "public-const.html" in names
    assert not any("private-const.html" in name for name in names)

    filtered_unresolved = [
        (src, target) for src, target in instance.unresolved if instance.representative(src) in include
    ]
    manifest = build_manifest(
        instance,
        artifacts=[str(p) for p, _ in files] + ["manifest.json"],
        projection="site:static",
        mode=config.mode(),
        cache_status="disabled",
        delta={},
        assets=assets,
        constants=sorted(include),
        filters=config.publish_filters(),
        unresolved=filtered_unresolved,
    )
    assert manifest["constants"] == ["public-const"]
    assert manifest["unresolved"] == []


def test_publish_filters_allow_drafts_for_channel(tmp_path):
    cfg_path = tmp_path / "emsenn-net-drafts.universe.yaml"
    cfg_path.write_text(
        """
sources: "*.md"
publish:
  filters:
    publish_to: [emsenn-net]
    status: [public, draft]
html:
  lang: en
  assets:
    inline: true
    minify: false
cache:
  enabled: false
"""
    )

    (tmp_path / "public.md").write_text(
        """---
id: public-const
title: Public Concept
status: public
publish_to: [emsenn-net]
ann: []
---
Body
"""
    )
    (tmp_path / "draft.md").write_text(
        """---
id: draft-const
title: Draft Concept
status: draft
publish_to: [emsenn-net]
ann: []
---
Body
"""
    )
    (tmp_path / "other.md").write_text(
        """---
id: other-const
title: Other Concept
status: private
publish_to: [other-site]
ann: []
---
Body
"""
    )

    config = UniverseConfig.load(cfg_path)
    evaluator = Evaluator(
        config,
        EvaluationOptions(mode="permissive", sanitize_html=True, html_lang=config.data.get("html", {}).get("lang", "en")),
    )
    instance = evaluator.evaluate(tmp_path)
    include = published_representatives(
        instance,
        publish_to=config.publish_filters().get("publish_to"),
        statuses=config.publish_filters().get("status"),
    )
    assert include == {"public-const", "draft-const"}

    filtered_unresolved = [
        (src, target) for src, target in instance.unresolved if instance.representative(src) in include
    ]
    manifest = build_manifest(
        instance,
        artifacts=["draft-const.html", "public-const.html", "manifest.json"],
        projection="site:static",
        mode=config.mode(),
        cache_status="disabled",
        delta={},
        assets={},
        constants=sorted(include),
        filters=config.publish_filters(),
        unresolved=filtered_unresolved,
    )
    assert manifest["constants"] == ["draft-const", "public-const"]
    assert manifest["filters"] == {"publish_to": ["emsenn-net"], "status": ["public", "draft"]}
