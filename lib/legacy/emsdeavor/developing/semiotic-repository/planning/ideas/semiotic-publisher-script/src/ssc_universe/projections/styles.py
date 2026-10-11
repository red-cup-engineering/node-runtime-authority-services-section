"""Shared style snippets for projections.

These mirror the base template styling so manual fallbacks remain
accessible and legible when Jinja2 is unavailable.
"""

import re
from hashlib import sha256
from pathlib import Path


def base_stylesheet(minify: bool = False) -> str:
    """Return the shared stylesheet for projections.

    The content mirrors the base template so Jinja and manual fallbacks stay
    visually aligned. Optional minification performs a conservative whitespace
    squeeze suitable for cache-friendly assets without altering semantics.
    """

    css = _BASE_STYLE_RAW.strip()
    return _minify_css(css) if minify else css


def stylesheet_asset(minify: bool = False) -> tuple[Path, bytes, str]:
    """Return a hashed stylesheet asset tuple (path, bytes, hash)."""

    css = base_stylesheet(minify=minify)
    digest = sha256(css.encode()).hexdigest()
    path = Path(f"assets/style-{digest[:12]}.css")
    return path, css.encode(), digest


def _minify_css(css: str) -> str:
    """Lightweight CSS minifier preserving semantics."""

    compact = re.sub(r"\s+", " ", css)
    compact = re.sub(r"\s*([{}:;,])\s*", r"\1", compact)
    return compact.strip()


_BASE_STYLE_RAW = """
:root {
  --bg: #f7f8fb;
  --panel: #ffffff;
  --border: #d7d9df;
  --text: #1f2933;
  --muted: #4b5563;
  --accent: #2563eb;
  --danger: #b91c1c;
  --warning: #f97316;
  --success: #15803d;
}

* { box-sizing: border-box; }

body {
  font-family: "Inter", "Segoe UI", system-ui, -apple-system, sans-serif;
  margin: 0;
  padding: 0;
  background: var(--bg);
  color: var(--text);
  line-height: 1.6;
  color-scheme: light dark;
}

.page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

header {
  background: #0f172a;
  color: #e2e8f0;
  padding: 0.75rem 1.25rem;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.25);
}

nav {
  display: flex;
  align-items: center;
  gap: 1rem;
}

nav a {
  color: #e2e8f0;
  text-decoration: none;
  font-weight: 600;
  padding: 0.35rem 0.65rem;
  border-radius: 0.35rem;
}

nav a:focus-visible,
nav a:hover {
  background: rgba(226, 232, 240, 0.14);
  outline: 2px solid rgba(226, 232, 240, 0.6);
  outline-offset: 2px;
}

.skip-link {
  position: absolute;
  top: -40px;
  left: 0.75rem;
  background: #0f172a;
  color: #fff;
  padding: 0.5rem 0.75rem;
  border-radius: 0.35rem;
  z-index: 10;
}

.skip-link:focus {
  top: 0.75rem;
  outline: 3px solid var(--accent);
}

main {
  margin-top: 1.5rem;
}

h1, h2, h3, h4 {
  line-height: 1.3;
  color: #0f172a;
}

a {
  color: var(--accent);
  text-decoration-thickness: 2px;
  text-underline-offset: 3px;
}

a:focus-visible {
  outline: 3px solid var(--accent);
  outline-offset: 2px;
}

p { margin: 0.4rem 0 0.6rem; }

ul { padding-left: 1.25rem; }

.failure { color: var(--danger); font-weight: 700; }
.provenance { font-size: 0.95em; color: var(--muted); }

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  padding: 0.9rem 1rem;
  margin-top: 1rem;
  border-radius: 0.6rem;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.04);
}

.panel h2,
.panel h3 {
  margin-top: 0;
}

.search-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.5rem 0 0.75rem;
}

.search-controls label {
  display: flex;
  flex-direction: column;
  font-size: 0.95em;
  color: var(--muted);
  gap: 0.25rem;
}

.search-controls select {
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  background: var(--panel);
  color: var(--text);
}

.diagnostics {
  background: #fff1f2;
  border-color: #fecdd3;
}

.broken { color: var(--danger); font-weight: 600; }

.tags { display: inline-flex; flex-wrap: wrap; gap: 0.35rem; }
.tag {
  display: inline-flex;
  align-items: center;
  padding: 0.15rem 0.55rem;
  background: #e0f2fe;
  color: #0f172a;
  border-radius: 999px;
  font-size: 0.9em;
  border: 1px solid #bae6fd;
}

.concept-metrics {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.35rem 0 0.1rem;
}

.concept-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.55rem;
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  border-radius: 0.45rem;
  font-weight: 700;
  font-size: 0.9em;
  color: #111827;
}

.concept-chip.failure {
  background: #fef2f2;
  border-color: #fecdd3;
  color: #991b1b;
}

.status-banner {
  background: #ecfdf3;
  border: 1px solid #bbf7d0;
  color: #064e3b;
  border-radius: 0.6rem;
  padding: 0.75rem 1rem;
  margin: 1rem 0;
  box-shadow: 0 2px 8px rgba(6, 78, 59, 0.08);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.65rem;
  margin-top: 0.35rem;
}

.status-item {
  background: #ffffff;
  border: 1px solid #bbf7d0;
  border-radius: 0.5rem;
  padding: 0.6rem 0.8rem;
}

.provenance-grid .status-item {
  background: #fffbeb;
  border-color: #fcd34d;
}

.status-label { font-weight: 700; display: block; color: #065f46; }
.status-value { margin: 0.1rem 0 0; }

.toc {
  background: #eef2ff;
  border: 1px solid #c7d2fe;
  padding: 0.85rem 1rem;
  border-radius: 0.6rem;
  margin: 1rem 0 1.25rem;
}

.toc h2 { margin-top: 0; color: #111827; }

.toc ul { margin: 0; padding-left: 1rem; }

.toc a { font-weight: 600; }

.math-list,
.math-lists ul {
  margin: 0.35rem 0 0;
  padding-left: 1.1rem;
}

.math-lists {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
  margin: 0.5rem 0 1rem;
}

.generator-value {
  font-family: "IBM Plex Mono", "SFMono-Regular", Menlo, monospace;
  font-size: 0.92rem;
}

.pager {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  margin: 1rem 0;
  padding: 0.75rem 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.pager-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 700;
}

.pager-link.disabled {
  color: var(--muted);
  font-weight: 600;
}

.back-to-top {
  margin-top: 1rem;
  text-align: right;
}

.back-to-top a {
  font-weight: 700;
}

@media (max-width: 720px) {
  header {
    padding: 0.65rem 0.9rem;
  }

  nav {
    flex-wrap: wrap;
    gap: 0.6rem;
  }

  .page {
    padding: 1.1rem 0.85rem 2rem;
  }

  .status-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }

  .pager {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0b1220;
    --panel: #0f172a;
    --border: #1f2937;
    --text: #e5e7eb;
    --muted: #9ca3af;
    --accent: #60a5fa;
    --danger: #fca5a5;
    --warning: #fdba74;
    --success: #86efac;
  }

  header { background: #0b1220; color: #e5e7eb; box-shadow: 0 2px 6px rgba(15, 23, 42, 0.55); }
  nav a { color: #e5e7eb; }
  nav a:hover, nav a:focus-visible { outline-color: rgba(224, 231, 255, 0.6); }

  .panel { background: var(--panel); border-color: var(--border); box-shadow: 0 3px 14px rgba(0, 0, 0, 0.45); }
  .diagnostics { background: #2c0f16; border-color: #7f1d1d; }
  .tag { background: #1e3a8a; color: #e5e7eb; border-color: #3b82f6; }
  .status-banner { background: #052e16; border-color: #166534; color: #bbf7d0; box-shadow: 0 2px 12px rgba(0,0,0,0.45); }
  .status-item { background: #0b1324; border-color: #166534; }
  .concept-chip { background: #1f2937; border-color: #334155; color: #e5e7eb; }
  .concept-chip.failure { background: #2c0f16; border-color: #7f1d1d; color: #fecdd3; }
  .toc { background: #1f2937; border-color: #334155; }
  h1, h2, h3, h4 { color: #e5e7eb; }
  a { color: var(--accent); }
  .pager { border-color: var(--border); }
  .skip-link { background: #0b1220; }
}

@media print {
  body {
    background: #ffffff;
    color: #000000;
  }

  header,
  .pager,
  .status-banner,
  .skip-link,
  nav,
  .toc {
    display: none !important;
  }

  .page {
    max-width: none;
    padding: 0;
  }

  .panel {
    box-shadow: none;
    border-color: #000000;
  }

  a {
    color: #000000;
    text-decoration: underline;
  }

  a::after {
    content: " (" attr(href) ")";
    font-size: 0.85em;
    color: #333333;
  }
}
"""

FALLBACK_STYLE = base_stylesheet()
