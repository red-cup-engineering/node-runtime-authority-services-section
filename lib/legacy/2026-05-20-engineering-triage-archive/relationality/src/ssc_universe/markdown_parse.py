from __future__ import annotations

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
    ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({"p", "h1", "h2", "h3", "h4", "h5", "h6", "span"})
else:
    ALLOWED_TAGS = {"p", "h1", "h2", "h3", "h4", "h5", "h6", "span", "a"}
ALLOWED_ATTRIBUTES = {"a": ["href", "title", "name"], "span": ["class"], "p": ["class"]}


class MarkdownRenderer:
    def __init__(self, sanitize: bool = True):
        self.md = MarkdownIt("commonmark") if MarkdownIt else None
        self.sanitize = sanitize

    def render(self, text: str) -> str:
        if self.md:
            html = self.md.render(text)
        else:
            # minimal fallback: wrap paragraphs
            html = "\n".join(f"<p>{line}</p>" for line in text.strip().split("\n\n"))
        if self.sanitize:
            html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        return html
