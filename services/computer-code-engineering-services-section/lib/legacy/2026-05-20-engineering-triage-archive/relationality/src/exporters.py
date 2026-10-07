from __future__ import annotations

"""
Exporters for the semiotic universe.

This module renders the evaluated `Universe` into:
- static HTML pages (site, concept docs, tag docs),
- a JSON concept API,
- RDF graphs, and
- an OpenAPI description.

It also contains the inline HTML templates used by the site generator.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from jinja2 import Environment, DictLoader, select_autoescape
from markdown_it import MarkdownIt

try:  # Optional RDF support
    from rdflib import Graph, Literal, Namespace, RDF, XSD
except Exception:  # pragma: no cover - graceful degradation when rdflib is missing
    Graph = Literal = Namespace = RDF = XSD = None  # type: ignore[assignment]

from .linting import build_atom_docs
from .model import Concept, FeatureSet, Universe
from .semantics import evaluation_components, evaluation_label
from .markdown_universe import WIKILINK_RE, slugify

MARKDOWN = MarkdownIt()


# ----------------------------
# Templates
# ----------------------------

THEMES: Dict[str, Dict[str, str]] = {
    "default": {
        "color_bg": "#f7f5f1",
        "color_bg_elevated": "#f0ede7",
        "color_ink": "#2e261a",
        "color_ink_muted": "#726655",
        "color_border_subtle": "#d0c7b8",
        "color_accent": "#6b7fd7",
        "color_accent_soft": "#dfe3f5",
        "link_color": "#4155b5",
        "link_hover_color": "#22348f",
        "link_visited_color": "#5b3f7a",
        "link_visited_hover_color": "#3c2756",
    }
}

BASE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ title }}</title>
  <style>
    :root {
      --font-body: "Georgia", "Times New Roman", serif;
      --font-ui: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --font-mono: "SF Mono", ui-monospace, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --line-height-body: 1.6;
      --space-1: 0.25rem;
      --space-2: 0.5rem;
      --space-3: 0.75rem;
      --space-4: 1rem;
      --space-5: 1.5rem;
      --space-6: 2rem;
      --space-7: 3rem;
      --radius-1: 2px;
      --radius-2: 4px;
      --color-bg: {{ theme.color_bg }};
      --color-bg-elevated: {{ theme.color_bg_elevated }};
      --color-ink: {{ theme.color_ink }};
      --color-ink-muted: {{ theme.color_ink_muted }};
      --color-border-subtle: {{ theme.color_border_subtle }};
      --color-accent: {{ theme.color_accent }};
      --color-accent-soft: {{ theme.color_accent_soft }};
      --link-color: {{ theme.link_color }};
      --link-hover-color: {{ theme.link_hover_color }};
      --link-visited-color: {{ theme.link_visited_color }};
      --link-visited-hover-color: {{ theme.link_visited_hover_color }};
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: var(--space-5) var(--space-3) var(--space-6);
      background: radial-gradient(circle at top left, #faf7f0 0, var(--color-bg) 38%, #f2efe8 100%);
      color: var(--color-ink);
      font-family: var(--font-body);
      font-size: 16px;
      line-height: var(--line-height-body);
      -webkit-font-smoothing: antialiased;
    }

    header.site-header {
      max-width: 72rem;
      margin: 0 auto var(--space-5);
      padding: 0 var(--space-1) var(--space-2);
      display: flex;
      justify-content: space-between;
      gap: var(--space-4);
      align-items: baseline;
      border-bottom: 1px solid var(--color-border-subtle);
    }

    .site-title {
      margin: 0;
      font-family: var(--font-ui);
      font-size: 1.05rem;
      font-weight: 500;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }

    .site-nav {
      display: flex;
      gap: var(--space-3);
      align-items: baseline;
      font-family: var(--font-ui);
      font-size: 0.8rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }

    .site-nav a {
      color: var(--color-ink-muted);
      text-decoration: none;
      border-bottom: none;
      padding-bottom: 0.1rem;
    }

    .site-nav a:hover,
    .site-nav a:focus {
      color: var(--link-hover-color);
      border-bottom: 1px solid var(--link-hover-color);
    }

    .page-main {
      max-width: 72rem;
      margin: 0 auto;
      padding: 0 var(--space-1);
    }

    a,
    .link {
      text-decoration: none;
      color: var(--link-color);
      border-bottom: 0.08em dotted rgba(65, 85, 181, 0.5);
      text-decoration-thickness: 0;
      text-underline-offset: 0.15em;
      transition: color 120ms ease-out, border-color 120ms ease-out;
    }

    a:hover,
    a:focus {
      color: var(--link-hover-color);
      border-bottom-style: solid;
      border-bottom-color: var(--link-hover-color);
      outline: none;
    }

    a:visited { color: var(--link-visited-color); }
    a:visited:hover,
    a:visited:focus {
      color: var(--link-visited-hover-color);
      border-bottom-color: var(--link-visited-hover-color);
    }

    h1, h2, h3, h4 {
      font-family: var(--font-ui);
      font-weight: 500;
      letter-spacing: 0.03em;
      text-rendering: optimizeLegibility;
    }

    h1 {
      font-size: 1.7rem;
      margin: 0 0 var(--space-3);
    }

    h2 {
      font-size: 1.35rem;
      margin: 0 0 var(--space-2);
    }

    h3 {
      font-size: 1rem;
      margin: 0 0 var(--space-2);
    }

    p { margin: 0 0 var(--space-3); }

    ul, ol {
      margin: 0 0 var(--space-3) 1.25rem;
      padding: 0;
    }

    code, pre {
      font-family: var(--font-mono);
      font-size: 0.9em;
    }

    .meta {
      font-family: var(--font-ui);
      font-size: 0.78rem;
      letter-spacing: 0.11em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
    }

    .meta-row {
      display: flex;
      justify-content: space-between;
      gap: var(--space-3);
      margin: 0 0 var(--space-2);
    }

    .meta-label {
      font-family: var(--font-ui);
      font-size: 0.72rem;
      letter-spacing: 0.11em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
      white-space: nowrap;
    }

    .meta-value {
      font-family: var(--font-body);
      font-size: 0.9rem;
      letter-spacing: 0;
      text-transform: none;
      color: var(--color-ink);
      text-align: right;
      flex: 1;
    }

    .meta-block { margin-top: var(--space-4); }

    /* Concept page layout */
    .concept-page { margin-bottom: var(--space-7); }

    .concept-header {
      margin-bottom: var(--space-4);
      border-bottom: 1px solid rgba(0, 0, 0, 0.06);
      padding-bottom: var(--space-3);
    }

    .concept-status-pill {
      display: inline-flex;
      align-items: center;
      padding: 0.1rem 0.6rem;
      margin: 0 0 var(--space-2);
      border-radius: 999px;
      border: 1px solid rgba(0, 0, 0, 0.15);
      font-family: var(--font-ui);
      font-size: 0.7rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      background: rgba(240, 225, 205, 0.6);
      color: var(--color-ink-muted);
    }

    .concept-status-pill--sketch {
      border-color: rgba(191, 110, 0, 0.7);
      background: rgba(191, 110, 0, 0.12);
      color: #6a3500;
    }

    .concept-status-pill--draft {
      border-color: rgba(191, 110, 0, 0.6);
      background: rgba(191, 110, 0, 0.06);
      color: #6a3500;
    }

    .concept-status-pill--stable,
    .concept-status-pill--public {
      border-color: rgba(40, 94, 54, 0.7);
      background: rgba(40, 94, 54, 0.08);
      color: #234b34;
    }

    .concept-status-pill--deprecated {
      border-color: rgba(90, 80, 70, 0.6);
      background: rgba(90, 80, 70, 0.06);
      color: #4a4036;
    }

    .concept-title {
      font-size: 1.6rem;
      margin: 0;
    }

    .concept-evaluation { margin-top: var(--space-2); }

    .evaluation-meter {
      position: relative;
      height: 0.18rem;
      max-width: 12rem;
      border-radius: 999px;
      background: linear-gradient(
        to right,
        var(--color-accent) 0,
        var(--color-accent) 55%,
        rgba(107, 127, 215, 0.2) 55%,
        rgba(107, 127, 215, 0.08) 100%
      );
      background-color: #d2d7e3;
      overflow: hidden;
    }

    .evaluation-label {
      margin-top: var(--space-2);
    }

    .concept-layout {
      display: grid;
      grid-template-columns: minmax(14rem, 18rem) minmax(0, 1fr);
      column-gap: var(--space-6);
      align-items: flex-start;
    }

    .concept-meta {
      padding-left: var(--space-3);
      border-left: 1px solid var(--color-border-subtle);
    }

    .concept-body { max-width: 70ch; }

    .body-html > *:first-child { margin-top: 0; }

    /* Tags / chips */
    .chip-list {
      list-style: none;
      margin: var(--space-2) 0 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
    }

    .chip {
      border-radius: var(--radius-2);
      border: 1px solid rgba(0, 0, 0, 0.15);
      background: var(--color-bg-elevated);
      padding: 0.15rem 0.55rem;
      font-family: var(--font-ui);
      font-size: 0.75rem;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
      white-space: nowrap;
    }

    .chip a {
      color: inherit;
      border-bottom: none;
    }

    .chip a:hover,
    .chip a:focus {
      color: var(--link-hover-color);
      border-bottom: none;
    }

    /* Related concepts */
    .related {
      margin-top: var(--space-6);
      padding-top: var(--space-4);
      border-top: 1px solid var(--color-border-subtle);
    }

    .related-heading {
      font-size: 0.95rem;
      margin: 0 0 var(--space-3);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--color-ink-muted);
    }

    .related-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .related-item {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: var(--space-3);
      margin-bottom: var(--space-2);
    }

    .related-link { flex: 1; }

    .related-score {
      font-size: 0.75rem;
      color: var(--color-ink-muted);
    }

    /* Index layout */
    .index-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
      gap: var(--space-4);
      margin: var(--space-2) 0 var(--space-6);
    }

    .index-card {
      background: var(--color-bg-elevated);
      border: 1px solid var(--color-border-subtle);
      border-radius: var(--radius-1);
      padding: var(--space-4);
    }

    .index-card-title {
      font-size: 0.95rem;
      margin: 0 0 var(--space-3);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--color-ink-muted);
    }

    .index-metrics {
      margin: 0;
      padding: 0;
    }

    .index-metric {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: var(--space-3);
      font-size: 0.9rem;
      margin-bottom: var(--space-1);
    }

    .index-metric dt {
      font-family: var(--font-ui);
      font-size: 0.75rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
    }

    .index-metric dd {
      margin: 0;
      font-family: var(--font-body);
      color: var(--color-ink);
    }

    .index-section {
      margin-bottom: var(--space-6);
    }

    .index-section-title {
      font-size: 1rem;
      margin: 0 0 var(--space-3);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--color-ink-muted);
    }

    .index-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .index-list-item {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: var(--space-3);
      padding: var(--space-1) 0;
      border-bottom: 1px solid rgba(212, 208, 197, 0.4);
    }

    .index-list-item:last-child { border-bottom: none; }

    .index-concept-link,
    .index-tag-name {
      flex: 1;
    }

    .index-list-meta {
      font-family: var(--font-ui);
      font-size: 0.78rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
      white-space: nowrap;
    }

    .index-top-concepts {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--space-2);
    }

    .index-top-concepts li {
      padding: 0.15rem 0.55rem;
      border-radius: var(--radius-2);
      border: 1px solid var(--color-border-subtle);
      background: #f1f0ea;
      font-family: var(--font-ui);
      font-size: 0.78rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--color-ink-muted);
    }

    @media (max-width: 900px) {
      body {
        padding: var(--space-4) var(--space-2) var(--space-5);
      }

      header.site-header,
      .page-main {
        padding: 0;
      }

      header.site-header {
        flex-direction: column;
        align-items: flex-start;
        gap: var(--space-2);
      }

      .concept-layout {
        grid-template-columns: minmax(0, 1fr);
      }

      .concept-meta {
        margin-bottom: var(--space-4);
        border-left: none;
        padding-left: 0;
      }

      .index-grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }

    ::selection {
      background-color: rgba(65, 85, 181, 0.18);
      color: var(--color-ink);
    }
  </style>
</head>
<body>
  <header class="site-header">
    <h1 class="site-title">{{ site_title }}</h1>
    <nav class="site-nav">
      <a href="{{ base_href }}/index.html">Universe</a>
      <a href="{{ base_href }}/docs/index.html">Docs</a>
      <a href="{{ base_href }}/tags/index.html">Tags</a>
    </nav>
  </header>
  <main class="page-main">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
"""

CONCEPT_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<article class="concept-page{% if concept.status %} concept-page--status-{{ concept.status|slugify }}{% endif %}{% if is_draft %} concept-page--draft{% endif %}">
  <header class="concept-header">
    {% if concept.status %}
    <p class="concept-status-pill concept-status-pill--{{ concept.status|slugify }}">
      {{ concept.status|capitalize }}
    </p>
    {% endif %}
    <h2 class="concept-title">{{ concept.title }}</h2>
    <div class="concept-evaluation">
      <div class="evaluation-meter" aria-hidden="true"></div>
      <div class="evaluation-label meta">
        Semantic connectivity: {{ evaluation_label }}
      </div>
    </div>
  </header>
  <section class="concept-layout">
    <aside class="concept-meta" aria-label="Concept metadata">
      {% if concept.status %}
      <p class="meta-row">
        <span class="meta-label">Status</span>
        <span class="meta-value">{{ concept.status }}</span>
      </p>
      {% endif %}
      {% if concept.type %}
      <p class="meta-row">
        <span class="meta-label">Type</span>
        <span class="meta-value">{{ concept.type }}</span>
      </p>
      {% endif %}
      {% if concept.created %}
      <p class="meta-row">
        <span class="meta-label">Created</span>
        <span class="meta-value">{{ concept.created }}</span>
      </p>
      {% endif %}
      {% if concept.updated %}
      <p class="meta-row">
        <span class="meta-label">Updated</span>
        <span class="meta-value">{{ concept.updated }}</span>
      </p>
      {% endif %}
      {% if concept.aliases %}
      <p class="meta-row">
        <span class="meta-label">Aliases</span>
        <span class="meta-value">{{ concept.aliases|join(", ") }}</span>
      </p>
      {% endif %}
      {% if concept.tags %}
      <div class="meta-block">
        <div class="meta-label">Tags</div>
        <ul class="chip-list">
          {% for t in concept.tags %}
          <li class="chip">
            <a href="{{ base_href }}/tags/{{ t|slugify }}.html">{{ t }}</a>
          </li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    </aside>
    <div class="concept-body">
      <div class="body-html">
        {{ body_html | safe }}
      </div>
      {% if related %}
      <section class="related">
        <h3 class="related-heading">Related concepts</h3>
        <ol class="related-list">
          {% for rel in related %}
          <li class="related-item">
            <a href="{{ base_href }}/docs/{{ rel.id }}.html" class="related-link">{{ rel.title }}</a>
            <span class="related-score meta">score {{ "%.2f"|format(rel.score) }}</span>
          </li>
          {% endfor %}
        </ol>
      </section>
      {% endif %}
      <section class="math-details">
        <h3 class="index-section-title">Math details</h3>
        <p class="meta">
          Evaluation score is computed as:
          <code>score = #tags + 0.5·#links + 0.3·#facts + 0.1·#temporal_years</code>
        </p>
        <dl class="index-metrics">
          <div class="index-metric">
            <dt>Tags</dt>
            <dd>{{ evaluation.tags }}</dd>
          </div>
          <div class="index-metric">
            <dt>Links</dt>
            <dd>{{ evaluation.links }}</dd>
          </div>
          <div class="index-metric">
            <dt>Facts</dt>
            <dd>{{ evaluation.facts }}</dd>
          </div>
          <div class="index-metric">
            <dt>Temporal years</dt>
            <dd>{{ evaluation.temporal_years }}</dd>
          </div>
          <div class="index-metric">
            <dt>Score</dt>
            <dd>{{ "%.2f"|format(evaluation.score) }}</dd>
          </div>
        </dl>
        <p class="meta">
          Full data:
          <a href="{{ base_href }}/api/concepts/{{ concept.id }}.json">JSON</a>.
        </p>
      </section>
    </div>
  </section>
</article>
{% endblock %}
"""

INDEX_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-grid">
  <article class="index-card">
    <h2 class="index-card-title">Universe</h2>
    <dl class="index-metrics">
      <div class="index-metric">
        <dt>Concepts</dt>
        <dd>{{ summary.concepts }}</dd>
      </div>
      <div class="index-metric">
        <dt>Atoms</dt>
        <dd>{{ summary.atoms }}</dd>
      </div>
      <div class="index-metric">
        <dt>Facts</dt>
        <dd>{{ summary.facts }}</dd>
      </div>
      <div class="index-metric">
        <dt>Temporal markers</dt>
        <dd>{{ summary.temporal }}</dd>
      </div>
    </dl>
  </article>
</section>
<section class="index-section">
  <h2 class="index-section-title">Concepts</h2>
  <ul class="index-list index-concepts">
    {% for concept in concepts %}
    <li class="index-list-item">
      <a href="{{ base_href }}/docs/{{ concept.id }}.html" class="index-concept-link">{{ concept.title }}</a>
      <span class="index-list-meta">score {{ "%.2f"|format(concept.evaluation_score) }}</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% if tag_index %}
<section class="index-section">
  <h2 class="index-section-title">Tags</h2>
  <ul class="index-list index-tags">
    {% for tag in tag_index %}
    <li class="index-list-item">
      <a href="{{ base_href }}/tags/{{ tag.slug }}.html" class="index-tag-name">{{ tag.name }}</a>
      <span class="index-list-meta">{{ tag.count }} concepts</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endif %}
{% endblock %}
"""

CONCEPT_INDEX_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-section">
  <h2 class="index-section-title">Concepts</h2>
  <ul class="index-list index-concepts">
    {% for concept in concepts %}
    <li class="index-list-item">
      <a href="{{ base_href }}/docs/{{ concept.id }}.html" class="index-concept-link">{{ concept.title }}</a>
      <span class="index-list-meta">score {{ "%.2f"|format(concept.evaluation_score) }}</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
"""

TAG_LIST_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-section">
  <h2 class="index-section-title">Tags</h2>
  <ul class="index-list index-tags">
    {% for tag in tags %}
    <li class="index-list-item">
      <a href="{{ base_href }}/tags/{{ tag.slug }}.html" class="index-tag-name">{{ tag.name }}</a>
      <span class="index-list-meta">{{ tag.count }} concepts</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
"""

TAG_DETAIL_TEMPLATE = """{% extends "base.html" %}
{% block content %}
<section class="index-section">
  <h2 class="index-section-title">{{ tag.name }}</h2>
  {% if tag.doc %}
  <article class="concept-page">
    <header class="concept-header">
      <h3 class="concept-title">{{ tag.doc.title }}</h3>
    </header>
    <div class="concept-body">
      <div class="body-html">
        {{ doc_body_html | safe }}
      </div>
    </div>
  </article>
  {% endif %}
  <p class="meta">
    {{ tag.count }} concept{% if tag.count != 1 %}s{% endif %}
    · connectivity {{ "%.2f"|format(tag.avg_score) }}
  </p>
  <ul class="index-list index-concepts">
    {% for concept in tag.concepts %}
    <li class="index-list-item">
      <a href="{{ base_href }}/docs/{{ concept.id }}.html" class="index-concept-link">{{ concept.title }}</a>
      <span class="index-list-meta">score {{ "%.2f"|format(concept.evaluation_score) }}</span>
    </li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
"""


# ----------------------------
# HTML helpers
# ----------------------------

def render_markdown_to_html(text: str, base_href: str = "") -> str:
    """Render markdown to HTML using markdown-it, expanding [[wikilinks]]."""

    def _wikilink_repl(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        target_id = slugify(label)
        if base_href:
            href = f"{base_href}/docs/{target_id}.html"
        else:
            href = f"docs/{target_id}.html"
        return f"[{label}]({href})"

    expanded = WIKILINK_RE.sub(_wikilink_repl, text)
    return MARKDOWN.render(expanded)


def jaccard(a: FeatureSet, b: FeatureSet) -> float:
    """Compute Jaccard similarity for relatedness."""
    if not a and not b:
        return 0.0
    inter = len(set(a) & set(b))
    union = len(set(a) | set(b))
    return inter / union if union else 0.0


def related_concepts(universe: Universe, concept: Concept, limit: int = 5) -> List[Tuple[Concept, float]]:
    """Find related concepts via Jaccard on semantic features."""
    results: List[Tuple[Concept, float]] = []
    for other in universe.concepts.values():
        if other.id == concept.id:
            continue
        score = jaccard(concept.semantic, other.semantic)
        if score > 0:
            results.append((other, score))
    results.sort(key=lambda pair: pair[1], reverse=True)
    return results[:limit]


def build_tag_items(universe: Universe) -> List[Dict[str, Any]]:
    """Assemble per-tag concept lists with evaluation-aware ordering."""
    tag_index = universe.indices.get("tag", {})
    atom_docs = build_atom_docs(universe)
    tag_docs = atom_docs.get("tag", {})
    items: List[Dict[str, Any]] = []
    for tag, concept_ids in tag_index.items():
        concepts_for_tag: List[Concept] = []
        for cid in concept_ids:
            if cid in universe.concepts:
                concepts_for_tag.append(universe.concepts[cid])
        concepts_for_tag.sort(key=lambda c: (-c.evaluation_score, c.title.lower()))
        count = len(concepts_for_tag)
        if concepts_for_tag:
            scores = [c.evaluation_score for c in concepts_for_tag]
            max_score = max(scores)
            min_score = min(scores)
            avg_score = sum(scores) / float(count)
        else:
            max_score = 0.0
            min_score = 0.0
            avg_score = 0.0
        items.append(
            {
                "name": tag,
                "slug": slugify(tag),
                "concepts": concepts_for_tag,
                "count": count,
                "max_score": max_score,
                "min_score": min_score,
                "avg_score": avg_score,
                "doc": tag_docs.get(tag),
            }
        )
    items.sort(key=lambda item: item["name"].lower())
    return items


def overview_summary(universe: Universe) -> Dict[str, Any]:
    """Assemble simple overview stats for the homepage."""
    tag_index = universe.indices.get("tag", {})
    folder_index = universe.indices.get("folder", {})
    fact_count = sum(1 for a in universe.atoms.values() if a.kind == "fact")
    temporal_atoms = sum(1 for a in universe.atoms.values() if a.kind in {"created_year", "updated_year"})
    all_tag_items = build_tag_items(universe)
    top_tags = sorted(all_tag_items, key=lambda item: item["count"], reverse=True)[:8]
    top_concepts = sorted(universe.concepts.values(), key=lambda c: c.evaluation_score, reverse=True)[:6]
    return {
        "concepts": len(universe.concepts),
        "atoms": len(universe.atoms),
        "tags": len(tag_index),
        "folders": len(folder_index),
        "facts": fact_count,
        "temporal": temporal_atoms,
        "top_tags": top_tags,
        "top_concepts": top_concepts,
    }


def export_html(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
    draft_statuses: Optional[List[str]] = None,
) -> None:
    """Render HTML site (index + concept pages)."""
    site_dir = output_dir / "site"
    doc_dir = site_dir / "docs"
    tag_dir = site_dir / "tags"
    if not dry_run:
        doc_dir.mkdir(parents=True, exist_ok=True)
        tag_dir.mkdir(parents=True, exist_ok=True)
    env = Environment(
        loader=DictLoader(
            {
                "base.html": BASE_TEMPLATE,
                "concept.html": CONCEPT_TEMPLATE,
                "index.html": INDEX_TEMPLATE,
                "concept_index.html": CONCEPT_INDEX_TEMPLATE,
                "tag_list.html": TAG_LIST_TEMPLATE,
                "tag_detail.html": TAG_DETAIL_TEMPLATE,
            }
        ),
        autoescape=select_autoescape(["html"]),
    )
    env.filters["slugify"] = slugify

    base_href = "."
    index_template = env.get_template("index.html")
    concept_template = env.get_template("concept.html")
    concept_index_template = env.get_template("concept_index.html")
    tag_list_template = env.get_template("tag_list.html")
    tag_detail_template = env.get_template("tag_detail.html")

    # Resolve theme from universe config.
    theme_name = (universe.config.theme or "default").lower()
    theme = THEMES.get(theme_name, THEMES["default"])

    concepts = sorted(universe.concepts.values(), key=lambda c: c.title.lower())
    if publish_statuses:
        allowed = set(publish_statuses)
        concepts = [c for c in concepts if c.status in allowed]
    tag_items = build_tag_items(universe)
    summary = overview_summary(universe)

    index_html = index_template.render(
        title=universe.config.site_title,
        header=universe.config.site_title,
        site_title=universe.config.site_title,
        base_href=base_href,
        concepts=concepts,
        tag_index=tag_items,
        summary=summary,
        theme=theme,
    )
    if not dry_run:
        (site_dir / "index.html").write_text(index_html, encoding="utf-8")

    concepts_index_html = concept_index_template.render(
        title=f"{universe.config.site_title} — Docs",
        header=universe.config.site_title,
        site_title=universe.config.site_title,
        base_href="..",
        concepts=concepts,
        theme=theme,
    )
    if not dry_run:
        (doc_dir / "index.html").write_text(concepts_index_html, encoding="utf-8")

    tag_list_html = tag_list_template.render(
        title=f"{universe.config.site_title} — Tags",
        header=universe.config.site_title,
        site_title=universe.config.site_title,
        base_href="..",
        tags=tag_items,
        theme=theme,
    )
    if not dry_run:
        (tag_dir / "index.html").write_text(tag_list_html, encoding="utf-8")

    for tag in tag_items:
        doc_body_html = None
        if tag.get("doc"):
            doc_body_html = render_markdown_to_html(tag["doc"].body_markdown, base_href="..")
        tag_html = tag_detail_template.render(
            title=f"{tag['name']} — {universe.config.site_title}",
            header=universe.config.site_title,
            site_title=universe.config.site_title,
            base_href="..",
            tag=tag,
            doc_body_html=doc_body_html,
            theme=theme,
        )
        if not dry_run:
            (tag_dir / f"{tag['slug']}.html").write_text(tag_html, encoding="utf-8")

    draft_status_set = set(draft_statuses or [])
    for concept in concepts:
        body_html = render_markdown_to_html(concept.body_markdown, base_href="..")
        eval_components = evaluation_components(universe, concept)
        eval_label = evaluation_label(eval_components["score"])
        is_draft = concept.status in draft_status_set if draft_status_set else False
        related = [{"id": c.id, "title": c.title, "score": score} for c, score in related_concepts(universe, concept)]
        html = concept_template.render(
            title=concept.title,
            header=universe.config.site_title,
            site_title=universe.config.site_title,
            base_href="..",
            concept=concept,
            body_html=body_html,
            evaluation=eval_components,
            evaluation_label=eval_label,
            is_draft=is_draft,
            related=related,
            theme=theme,
        )
        if not dry_run:
            (doc_dir / f"{concept.id}.html").write_text(html, encoding="utf-8")


# ----------------------------
# JSON / RDF / OpenAPI
# ----------------------------

def atoms_as_list(universe: Universe, features: FeatureSet) -> List[Dict[str, Any]]:
    """Render feature set atoms for JSON export."""
    items: List[Dict[str, Any]] = []
    for aid in features:
        atom = universe.atoms[aid]
        items.append({"id": atom.id, "kind": atom.kind, "value": atom.value})
    return sorted(items, key=lambda x: (x["kind"], x["value"]))


def export_json_api(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
) -> None:
    """Emit static JSON API for concepts."""
    api_dir = output_dir / "api" / "concepts"
    if not dry_run:
        api_dir.mkdir(parents=True, exist_ok=True)
    index_payload: List[Dict[str, Any]] = []
    concepts = sorted(universe.concepts.values(), key=lambda c: c.id)
    if publish_statuses:
        allowed = set(publish_statuses)
        concepts = [c for c in concepts if c.status in allowed]
    for concept in concepts:
        payload = {
            "id": concept.id,
            "title": concept.title,
            "path": concept.path.as_posix(),
            "tags": concept.tags,
            "folders": concept.folders,
            "links": concept.links,
            "status": concept.status,
            "type": concept.type,
            "aliases": concept.aliases,
            "created": concept.created,
            "updated": concept.updated,
            "evaluation": concept.evaluation_score,
            "fragment_features": atoms_as_list(universe, concept.fragment),
            "semantic_features": atoms_as_list(universe, concept.semantic),
        }
        if not dry_run:
            (api_dir / f"{concept.id}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
        index_payload.append(
            {
                "id": concept.id,
                "title": concept.title,
                "tags": concept.tags,
                "folders": concept.folders,
                "status": concept.status,
                "type": concept.type,
                "evaluation": concept.evaluation_score,
            }
        )
    if not dry_run:
        index_path = api_dir / "index.json"
        index_path.write_text(json.dumps(index_payload, indent=2), encoding="utf-8")


def export_rdf(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
) -> None:
    """Serialize universe as RDF (Turtle + optional JSON-LD)."""
    if Graph is None or Namespace is None or RDF is None or XSD is None:
        print("[rdf] rdflib not available; skipping RDF export.")
        return
    rdf_dir = output_dir / "rdf"
    if not dry_run:
        rdf_dir.mkdir(parents=True, exist_ok=True)
    graph = Graph()
    sem = Namespace("https://example.org/sem#")
    base = Namespace(universe.config.base_url)
    graph.bind("sem", sem)
    graph.bind("base", base)

    for atom in universe.atoms.values():
        atom_uri = base[f"atom/{atom.kind}/{slugify(atom.value)}"]
        graph.add((atom_uri, RDF.type, sem.Atom))
        graph.add((atom_uri, sem.kind, Literal(atom.kind)))
        graph.add((atom_uri, sem.value, Literal(atom.value)))

    concepts = list(universe.concepts.values())
    if publish_statuses:
        allowed = set(publish_statuses)
        concepts = [c for c in concepts if c.status in allowed]
    for concept in concepts:
        subject = base[f"concept/{concept.id}"]
        graph.add((subject, RDF.type, sem.Concept))
        graph.add((subject, sem.title, Literal(concept.title)))
        graph.add((subject, sem.evaluation, Literal(concept.evaluation_score, datatype=XSD.float)))
        for aid in concept.semantic:
            atom = universe.atoms[aid]
            atom_uri = base[f"atom/{atom.kind}/{slugify(atom.value)}"]
            graph.add((subject, sem.semanticFeature, atom_uri))

    if not dry_run:
        (rdf_dir / "graph.ttl").write_text(graph.serialize(format="turtle"), encoding="utf-8")
        try:
            (rdf_dir / "graph.jsonld").write_text(graph.serialize(format="json-ld"), encoding="utf-8")
        except Exception:
            pass


def openapi_schema_example(universe: Universe) -> Dict[str, Any]:
    """Build minimal OpenAPI schema matching the JSON API."""
    api_title = f"{universe.config.site_title} JSON API"
    return {
        "openapi": "3.1.0",
        "info": {"title": api_title, "version": "0.1.0"},
        "servers": [{"url": "."}],
        "paths": {
            "/api/concepts": {
                "get": {
                    "summary": "List concepts",
                    "responses": {
                        "200": {
                            "description": "Concept index",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "array", "items": {"$ref": "#/components/schemas/ConceptSummary"}}
                                }
                            },
                        }
                    },
                }
            },
            "/api/concepts/{id}": {
                "get": {
                    "summary": "Get concept",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {
                        "200": {
                            "description": "Concept",
                            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Concept"}}},
                        }
                    },
                }
            },
        },
        "components": {
            "schemas": {
                "Atom": {
                    "type": "object",
                    "properties": {"id": {"type": "integer"}, "kind": {"type": "string"}, "value": {"type": "string"}},
                },
                "Concept": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "path": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "folders": {"type": "array", "items": {"type": "string"}},
                        "links": {"type": "array", "items": {"type": "string"}},
                        "status": {"type": ["string", "null"]},
                        "type": {"type": ["string", "null"]},
                        "aliases": {"type": "array", "items": {"type": "string"}},
                        "evaluation": {"type": "number"},
                        "fragment_features": {"type": "array", "items": {"$ref": "#/components/schemas/Atom"}},
                        "semantic_features": {"type": "array", "items": {"$ref": "#/components/schemas/Atom"}},
                    },
                },
                "ConceptSummary": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "folders": {"type": "array", "items": {"type": "string"}},
                        "status": {"type": ["string", "null"]},
                        "type": {"type": ["string", "null"]},
                        "evaluation": {"type": "number"},
                    },
                },
            }
        },
    }


def export_openapi(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    publish_statuses: Optional[List[str]] = None,
) -> None:
    """Write OpenAPI JSON describing the static API."""
    api_dir = output_dir / "api"
    if not dry_run:
        api_dir.mkdir(parents=True, exist_ok=True)
    schema = openapi_schema_example(universe)
    if not dry_run:
        (api_dir / "openapi.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")


def concept_to_pandoc_markdown(universe: Universe, concept: Concept) -> str:
    """Render a concept to markdown with YAML frontmatter and semantic appendix for pandoc."""
    yaml_content = None
    try:
        import yaml  # type: ignore

        meta = {
            "title": concept.title,
            "id": concept.id,
            "tags": concept.tags,
            "type": concept.type,
            "status": concept.status,
            "aliases": concept.aliases,
            "folders": concept.folders,
            "links": concept.links,
        }
        yaml_content = yaml.safe_dump(meta, sort_keys=False).strip()
    except Exception:
        pass
    header = f"---\n{yaml_content}\n---\n\n" if yaml_content else ""
    semantic_lines = "\n".join(
        f"- {universe.atoms[aid].kind}: {universe.atoms[aid].value}"
        for aid in sorted(concept.semantic, key=lambda x: (universe.atoms[x].kind, universe.atoms[x].value))
    )
    appendix = f"\n\n## Semantic features\n{semantic_lines}\n" if semantic_lines else ""
    return f"{header}{concept.body_markdown}{appendix}"


def export_pandoc(
    universe: Universe,
    output_dir: Path,
    dry_run: bool = False,
    allow_pandoc: bool = False,
    concept_id: Optional[str] = None,
) -> None:
    """Use pandoc to publish either a single concept or a combined document."""
    if not allow_pandoc or not universe.config.pandoc_enabled:
        print("[pandoc] Skipping (not enabled).")
        return
    formats = universe.config.pandoc_formats or ["pdf"]
    concepts: List[Concept]
    if concept_id:
        if concept_id not in universe.concepts:
            print(f"[pandoc] Concept {concept_id} not found; skipping.")
            return
        concepts = [universe.concepts[concept_id]]
    else:
        concepts = sorted(universe.concepts.values(), key=lambda c: c.title.lower())
    combined_md = "\n\n".join(concept_to_pandoc_markdown(universe, c) for c in concepts)
    pub_dir = output_dir / "pub"
    if not dry_run:
        pub_dir.mkdir(parents=True, exist_ok=True)
    for fmt in formats:
        output_name = (
            universe.config.pandoc_output_single
            if universe.config.pandoc_output_single
            else (concepts[0].id if concept_id else "book")
        )
        out_path = pub_dir / f"{output_name}.{fmt}"
        cmd = ["pandoc", "-f", "markdown", "-t", fmt]
        if universe.config.pandoc_template:
            cmd.extend(["--template", universe.config.pandoc_template])
        if universe.config.pandoc_filters:
            for flt in universe.config.pandoc_filters:
                cmd.extend(["--filter", flt])
        cmd.extend(["-o", str(out_path)])
        if dry_run:
            print(f"[pandoc] (dry-run) {' '.join(cmd)}")
            continue
        try:
            subprocess.run(cmd, input=combined_md.encode("utf-8"), check=True)
            print(f"[pandoc] wrote {out_path}")
        except FileNotFoundError:
            print("[pandoc] pandoc not installed or not in PATH; skipping.")
            return
        except subprocess.CalledProcessError as exc:
            print(f"[pandoc] pandoc failed: {exc}")


# ----------------------------
# Orchestration
# ----------------------------

def export_all(
    universe: Universe,
    output_dir: Path,
    targets: List[str],
    dry_run: bool = False,
    allow_pandoc: bool = False,
    concept_id: Optional[str] = None,
    publish_statuses: Optional[List[str]] = None,
    draft_statuses: Optional[List[str]] = None,
) -> None:
    """Run selected exporters."""
    if "html" in targets:
        export_html(
            universe,
            output_dir,
            dry_run=dry_run,
            publish_statuses=publish_statuses,
            draft_statuses=draft_statuses,
        )
    if "json" in targets:
        export_json_api(universe, output_dir, dry_run=dry_run, publish_statuses=publish_statuses)
    if "rdf" in targets:
        export_rdf(universe, output_dir, dry_run=dry_run, publish_statuses=publish_statuses)
    if "openapi" in targets:
        export_openapi(universe, output_dir, dry_run=dry_run, publish_statuses=publish_statuses)
    if "pandoc" in targets:
        export_pandoc(universe, output_dir, dry_run=dry_run, allow_pandoc=allow_pandoc, concept_id=concept_id)


def default_targets_for_mode(mode: str) -> List[str]:
    if mode == "doc":
        return ["pandoc"]
    return ["html", "json", "rdf", "openapi"]


def normalize_targets(targets: Any) -> List[str]:
    if isinstance(targets, str):
        return [t.strip() for t in targets.split(",") if t.strip()]
    if isinstance(targets, list):
        return [str(t) for t in targets]
    return []


__all__ = [
    "export_all",
    "export_html",
    "export_json_api",
    "export_rdf",
    "export_openapi",
    "export_pandoc",
    "default_targets_for_mode",
    "normalize_targets",
    "render_markdown_to_html",
]
