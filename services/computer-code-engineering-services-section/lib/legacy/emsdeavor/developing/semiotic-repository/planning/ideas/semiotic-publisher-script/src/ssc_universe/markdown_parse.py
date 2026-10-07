from __future__ import annotations

import json
import re
from html import escape as html_escape

try:  # pragma: no cover - prefer real dependency
    from markdown_it import MarkdownIt
    from markdown_it.renderer import RendererHTML  # noqa: F401
except Exception:  # pragma: no cover
    MarkdownIt = None
try:  # pragma: no cover
    import bleach
except Exception:  # pragma: no cover
    class _Bleach:
        def clean(self, text, tags=None, attributes=None):
            # minimal fallback sanitizer: strip script tags
            import re

            return re.sub(r"<script.*?>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)

    bleach = _Bleach()


if hasattr(bleach, "sanitizer"):
    ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union(
        {"p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "pre"}
    )
else:
    ALLOWED_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "a", "pre"}
ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "name"],
    "span": ["class", "data-ann"],
    "p": ["class"],
    "pre": ["class", "data-ann"],
    "blockquote": ["class"],
    "code": ["class"],
}

_WIKILINK_RE = re.compile(r"(?<!!)\[\[([^\]]+)\]\]")
_TRANSCLUSION_RE = re.compile(r"!\[\[([^\]]+)\]\]")
_CALLOUT_TYPE_RE = re.compile(r"^\[!([A-Za-z0-9_-]+)\](?:\s+(.*))?$")
_CODEANN_LINE_RE = re.compile(r"^\s*(\[|\()\s*([^\[\(\]\)]+?)\s*::\s*(.*?)\s*(\]|\))\s*$")


class MarkdownRenderer:
    def __init__(self, sanitize: bool = True):
        self.md = MarkdownIt("commonmark") if MarkdownIt else None
        self.sanitize = sanitize

    def render(self, text: str) -> str:
        text, codeann_markers = _extract_code_block_annotations(text)
        text = _rewrite_wikilinks(text)
        if self.md:
            html = self.md.render(text)
        else:
            # minimal fallback: wrap paragraphs
            html = "\n".join(f"<p>{line}</p>" for line in text.strip().split("\n\n"))
        html = _apply_code_block_annotations(html, codeann_markers)
        html = _rewrite_callouts(html)
        if self.sanitize:
            html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        return html


def _rewrite_wikilinks(text: str) -> str:
    from .ingest import slugify

    def normalize_target(raw: str) -> tuple[str, str | None]:
        inner = raw.strip()
        if "|" in inner:
            target, label = inner.split("|", 1)
            return target.strip(), label.strip() or None
        return inner, None

    def target_href(target: str) -> str:
        target = target.strip()
        if target.startswith("#"):
            return f"#{slugify(target[1:])}"
        base = target
        frag = ""
        for sep in ("#", "^"):
            if sep in base:
                base, rest = base.split(sep, 1)
                frag = f"#{rest}"
                break
        base_slug = slugify(base)
        return f"{base_slug}.html{frag}"

    def repl_transclusion(match: re.Match) -> str:
        target_raw = match.group(1)
        target, label = normalize_target(target_raw)
        href = target_href(target)
        visible = label or target.strip()
        # Use an HTML wrapper (allowed by sanitizer) so projections can style embeds,
        # while keeping a plain link semantics.
        return f'<span class="transclusion"><a href="{html_escape(href)}">{html_escape(visible)}</a></span>'

    def repl_wikilink(match: re.Match) -> str:
        target_raw = match.group(1)
        target, label = normalize_target(target_raw)
        href = target_href(target)
        visible = label or target.strip()
        return f'[{visible}]({href})'

    text = _TRANSCLUSION_RE.sub(repl_transclusion, text)
    return _WIKILINK_RE.sub(repl_wikilink, text)


def _rewrite_callouts(html: str) -> str:
    def repl(match: re.Match) -> str:
        inner = match.group("inner")
        parts = inner.split("\n", 2)
        if not parts:
            return match.group(0)
        first = parts[0]
        m = re.match(r"<p>(?P<text>.*?)</p>\\s*$", first)
        if not m:
            return match.group(0)
        title_text = re.sub(r"<.*?>", "", m.group("text"))
        callout_match = _CALLOUT_TYPE_RE.match(title_text.strip())
        if not callout_match:
            return match.group(0)
        callout_type = callout_match.group(1).lower()
        title = callout_match.group(2) or callout_type.capitalize()
        rest = "\n".join(parts[1:]) if len(parts) > 1 else ""
        title_html = f'<p class="callout-title">{html_escape(title)}</p>'
        return f'<blockquote class="callout callout-{html_escape(callout_type)}">{title_html}\n{rest}</blockquote>'

    return re.sub(r"<blockquote>\\s*(?P<inner>.*?)\\s*</blockquote>", repl, html, flags=re.DOTALL)


def _extract_code_block_annotations(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    out: list[str] = []
    markers: list[str] = []
    pending: dict[str, str] = {}

    def flush_pending() -> None:
        nonlocal pending
        if pending:
            payload = json.dumps(pending, ensure_ascii=False, separators=(",", ":"))
            markers.append(payload)
            out.append(f'<span class="codeann" data-ann="{html_escape(payload)}"></span>')
            pending = {}

    i = 0
    while i < len(lines):
        line = lines[i]
        fence_match = re.match(r"^```", line)
        if fence_match:
            flush_pending()
            out.append(line)
            i += 1
            continue
        ann_match = _CODEANN_LINE_RE.match(line)
        if ann_match:
            j = i
            collected: list[re.Match] = []
            while j < len(lines):
                m = _CODEANN_LINE_RE.match(lines[j])
                if not m:
                    break
                collected.append(m)
                j += 1
            next_non_ann = lines[j] if j < len(lines) else ""
            if collected and re.match(r"^```", next_non_ann):
                for m in collected:
                    key = m.group(2).strip()
                    value = m.group(3).strip()
                    if key:
                        pending[key] = value
                i = j
                continue
        out.append(line)
        i += 1
    flush_pending()
    return "\n".join(out) + ("\n" if text.endswith("\n") else ""), markers


def _apply_code_block_annotations(html: str, markers: list[str]) -> str:
    if not markers:
        return html

    def repl(match: re.Match) -> str:
        payload = match.group("payload")
        pre = match.group("pre")
        return f'<pre data-ann="{payload}">{pre}</pre>'

    # Replace marker+codeblock pairs, leaving plain code blocks unchanged.
    return re.sub(
        r'<span class="codeann" data-ann="(?P<payload>[^"]*)"></span>\\s*<pre>(?P<pre>\\s*<code.*?</code>\\s*)</pre>',
        repl,
        html,
        flags=re.DOTALL,
    )
