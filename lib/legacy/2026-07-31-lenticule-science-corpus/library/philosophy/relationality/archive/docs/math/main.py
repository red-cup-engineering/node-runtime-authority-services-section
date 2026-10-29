from __future__ import annotations

from pathlib import Path

import yaml


DOCS_DIR = Path(__file__).parent / "content"


def load_acts():
    acts_dir = DOCS_DIR / "acts"
    acts = []
    for path in sorted(acts_dir.glob("*.md")):
        if path.name == "index.md":
            continue
        text = path.read_text()
        try:
            front = text.split("---", 2)[1]
        except IndexError:
            continue
        meta = yaml.safe_load(front)
        meta["__file"] = path
        acts.append(meta)
    return acts


ACTS = load_acts()
ACTS.sort(key=lambda item: item["slug"])
ACT_BY_ACT = {act["act"]: act for act in ACTS}
ACT_BY_SLUG = {act["slug"]: act for act in ACTS}


def find_act(meta: dict) -> dict | None:
    slug = meta.get("slug")
    act_name = meta.get("act")
    if slug:
        return ACT_BY_SLUG.get(slug)
    if act_name:
        return ACT_BY_ACT.get(act_name)
    return None


def format_act_link(act_name: str | None) -> str:
    if not act_name:
        return "`∅`"
    target = ACT_BY_ACT.get(act_name)
    if not target:
        return f"`{act_name}`"
    rel = target["__file"].name
    return f"[{act_name}]({rel})"


def format_title_link(act: dict) -> str:
    rel = Path(act["__file"].name)
    return f"[{act['title']}]({rel})"


def define_env(env):
    @env.macro
    def act_info(meta):
        top = format_act_link(meta.get("top"))
        bottom = format_act_link(meta.get("bottom"))
        strata = ", ".join(meta.get("strata") or []) or "unclassified"
        phase = meta.get("phase", "free")
        tags = ", ".join(meta.get("tags") or []) or "none"
        witnesses = [meta.get("top"), meta.get("bottom")]
        witnesses = [w for w in witnesses if w]
        definition = "(" + " ".join(witnesses) + ")" if witnesses else "()"
        lines = [
            '!!! info "Witness data"',
            f"    - Definition: `{meta['act']} = {definition}`",
        ]
        symbol = meta.get("symbol")
        if symbol:
            lines.append(f"    - Symbol: `{symbol}`")
        lines.extend(
            [
                f"    - Top: {top}",
                f"    - Bottom: {bottom}",
                f"    - Strata: {strata}",
                f"    - Phase: {phase}",
                f"    - Tags: {tags}",
            ]
        )
        return "\n".join(lines)

    @env.macro
    def act_nav(meta):
        current = find_act(meta)
        if not current:
            return ""
        sections = []

        def role_links(role: str) -> str:
            targets = meta.get(role)
            if not targets:
                return f"{role.title()}: `∅`"
            if isinstance(targets, str):
                targets = [targets]
            links = [format_act_link(name) for name in targets]
            return f"{role.title()}: {', '.join(links)}"

        sections.append(role_links("top"))
        sections.append(role_links("bottom"))
        nav_line = " | ".join(sections)
        return f"---\n\n{nav_line}"

    env.variables["acts"] = ACTS
