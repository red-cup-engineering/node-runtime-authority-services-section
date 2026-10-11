from __future__ import annotations

import json
from pathlib import Path
from typing import List, Tuple

try:  # pragma: no cover - prefer jinja2
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None

from ..markdown_parse import MarkdownRenderer
from ..sscu_model import UniverseInstance
from .styles import FALLBACK_STYLE, base_stylesheet
from ..annterm import FAIL_BOTTOM


def _format_value(val: object) -> str:
    if val == FAIL_BOTTOM:
        return "⊥_fail"
    if isinstance(val, tuple):
        return repr(tuple(val))
    return repr(val)


def render_single(
    instance: UniverseInstance,
    template_dir: Path,
    mathjax: bool,
    build_info: dict | None = None,
    delta: dict | None = None,
    assets_minify: bool = False,
    manifest_href: str | None = None,
    include: list[str] | None = None,
) -> Tuple[str, bytes]:
    env = None
    tpl = None
    html_lang = getattr(instance, "html_lang", "en")
    sanitize = getattr(instance, "sanitize_html", True)
    build = {
        "projection": "single:html",
        "mode": build_info.get("mode") if build_info else None,
        "cache_status": build_info.get("cache_status") if build_info else None,
        "config_hash": instance.config_hash,
        "repo_fingerprint": instance.repo_fingerprint,
        "sanitize_html": sanitize,
        "html_lang": html_lang,
        "assets_inline": True,
        "assets_minify": assets_minify,
        "mathjax": mathjax,
        "manifest_href": manifest_href,
    }
    if Environment:
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        env.globals["mathjax"] = mathjax
        env.globals["html_lang"] = html_lang
        tpl = env.get_template("single.html")
    markdown = MarkdownRenderer(sanitize=sanitize)

    rendered = []
    reference_graph_entries = []
    equivalence_classes = []
    search_index = []
    include_set = set(include) if include else None
    ordered_concepts = sorted(instance.canonical_concepts.items(), key=lambda kv: kv[0])
    if include_set is not None:
        ordered_concepts = [(rep, concept) for rep, concept in ordered_concepts if rep in include_set]
    ann_delta = delta.get("ann_changes", {}) if delta else {}
    ref_delta = delta.get("reference_changes", {}) if delta else {}
    unresolved_added_map: dict[str, list[str]] = {}
    unresolved_removed_map: dict[str, list[str]] = {}
    if delta:
        for src, target in delta.get("unresolved", {}).get("added", []):
            unresolved_added_map.setdefault(src, []).append(target)
        for src, target in delta.get("unresolved", {}).get("removed", []):
            unresolved_removed_map.setdefault(src, []).append(target)
    for idx, (rep, concept) in enumerate(ordered_concepts):
        prev_entry = ordered_concepts[idx - 1] if idx > 0 else None
        next_entry = ordered_concepts[idx + 1] if idx + 1 < len(ordered_concepts) else None
        fragment = instance.fragments[rep]
        sem = instance.sem[rep]
        body_html = markdown.render(concept.body)
        ann_terms = [repr(t.surface()) for t in concept.ann]
        generator_steps = []
        for term, (value, prov) in zip(concept.ann, fragment.generators):
            generator_steps.append(
                {
                    "surface": term.surface(),
                    "value": _format_value(value),
                    "is_failure": value == FAIL_BOTTOM or value == ("fail", "unparseable"),
                    "provenance": prov.steps,
                }
            )
        fragment_elements = [_format_value(val) for val in sorted(fragment.elements, key=lambda v: repr(v))]
        unresolved = [r for src, r in instance.unresolved if src == rep]
        backlinks = sorted(
            k
            for k, refs in instance.reference_graph.items()
            if rep in refs and k != rep and (include_set is None or k in include_set)
        )
        resolved_refs = sorted(
            ref
            for ref in instance.reference_graph.get(rep, set())
            if ref in instance.canonical_concepts and ref != rep and (include_set is None or ref in include_set)
        )
        concept_delta = None
        if delta:
            ann_status = ann_delta.get(rep)
            ref_status = ref_delta.get(rep)
            add_unresolved = sorted(unresolved_added_map.get(rep, []))
            remove_unresolved = sorted(unresolved_removed_map.get(rep, []))
            if ann_status or ref_status or add_unresolved or remove_unresolved:
                concept_delta = {
                    "ann_status": ann_status,
                    "ref_status": ref_status,
                    "unresolved_added": add_unresolved,
                    "unresolved_removed": remove_unresolved,
                    "baseline_present": delta.get("baseline_present", False),
                }
        aliases = [alias for alias in sorted(instance.equivalence_classes.get(rep, [])) if alias != rep]
        rendered.append(
            {
                "anchor": rep,
                "title": concept.title,
                "const": concept.const,
                "aliases": aliases,
                "same_as": concept.same_as,
                "tags": concept.tags,
                "body": body_html,
                "fragment": fragment,
                "sem": sem,
                "ann_terms": ann_terms,
                "generators": generator_steps,
                "generator_count": len(generator_steps),
                "fragment_size": len(fragment.elements),
                "is_failure": fragment.is_failure,
                "fragment_elements": fragment_elements,
                "backlinks": backlinks,
                "resolved_refs": resolved_refs,
                "unresolved": unresolved,
                "concept_delta": concept_delta,
                "prev_link": {"anchor": prev_entry[0], "title": prev_entry[1].title} if prev_entry else None,
                "next_link": {"anchor": next_entry[0], "title": next_entry[1].title} if next_entry else None,
            }
        )
        reference_graph_entries.append(
            {
                "anchor": rep,
                "title": concept.title,
                "const": concept.const,
                "resolved": resolved_refs,
                "backlinks": backlinks,
            }
        )
        equivalence_classes.append(
            {
                "anchor": rep,
                "title": concept.title,
                "const": concept.const,
                "aliases": aliases,
            }
        )
        search_index.append(
            {
                "anchor": rep,
                "title": concept.title,
                "const": concept.const,
                "aliases": aliases,
                "tags": concept.tags,
                "ann_terms": ann_terms,
                "status": concept.status,
                "publish_to": concept.publish_to or [],
                "generator_count": len(generator_steps),
                "fragment_size": len(fragment.elements),
                "failure": fragment.is_failure,
            }
        )

    manifest = {
        "constants": list(instance.concepts.keys()),
        "unresolved": instance.unresolved,
        "failures": list(instance.failures),
        "config_hash": instance.config_hash,
        "repo": {"fingerprint": instance.repo_fingerprint},
        "equivalence_classes": instance.equivalence_classes,
        "reference_graph": reference_graph_entries,
    }
    if delta is not None:
        manifest["delta"] = delta

    style_text = base_stylesheet(minify=assets_minify)

    if tpl:
        html = tpl.render(
            title="SSCU",
            concepts=rendered,
            manifest=manifest,
            delta=delta,
            relroot="",
            style_inline=style_text,
            html_lang=html_lang,
            reference_graph=reference_graph_entries,
            build_info=build,
            equivalence_classes=equivalence_classes,
            manifest_href=manifest_href,
            search_data=json.dumps(search_index),
        )
    else:
        fallback_style = style_text if assets_minify else FALLBACK_STYLE
        search_section = (
            "<section class='panel' role='region' aria-labelledby='concept-search'>"
            "<h2 id='concept-search'>Search</h2>"
            "<input type='search' id='search-box' aria-describedby='search-help' placeholder='Search concepts'>"
            "<div class='search-controls' aria-label='Search filters'>"
            "<label for='search-status-filter'>Status"
            "<select id='search-status-filter'><option value=''>All statuses</option></select>"
            "</label>"
            "<label for='search-target-filter'>Publish target"
            "<select id='search-target-filter'><option value=''>All targets</option></select>"
            "</label>"
            "</div>"
            "<p id='search-help' class='provenance'>Filter by title, const, aliases, tags, or Ann_X(k) entries.</p>"
            "<p id='search-status' class='provenance' aria-live='polite'>Showing all concepts.</p>"
            "<div id='search-results' role='list' aria-label='Search results'></div>"
            f"<script type='application/json' id='search-data'>{json.dumps(search_index)}</script>"
            "<script>const searchInput=document.getElementById('search-box');const results=document.getElementById('search-results');const status=document.getElementById('search-status');const statusFilter=document.getElementById('search-status-filter');const targetFilter=document.getElementById('search-target-filter');const searchData=JSON.parse(document.getElementById('search-data').textContent);function populateFilters(data){if(statusFilter){const statuses=Array.from(new Set(data.map(entry=>entry.status).filter(Boolean))).sort();statuses.forEach(val=>{const opt=document.createElement('option');opt.value=val;opt.textContent=val;statusFilter.appendChild(opt);});}if(targetFilter){const targets=new Set();data.forEach(entry=>{(entry.publish_to||[]).forEach(val=>targets.add(val));});Array.from(targets).sort().forEach(val=>{const opt=document.createElement('option');opt.value=val;opt.textContent=val;targetFilter.appendChild(opt);});}}function matches(entry,term){const statusVal=statusFilter?statusFilter.value:'';const targetVal=targetFilter?targetFilter.value:'';if(statusVal && (entry.status||'')!==statusVal){return false;}if(targetVal && !(entry.publish_to||[]).includes(targetVal)){return false;}if(!term){return true;}return entry.title.toLowerCase().includes(term)||entry.const.toLowerCase().includes(term)||entry.aliases.some(a=>a.toLowerCase().includes(term))||entry.tags.some(t=>t.toLowerCase().includes(term))||entry.ann_terms.some(a=>a.toLowerCase().includes(term));}function renderResults(q){const term=q.trim().toLowerCase();const filtered=(term||(statusFilter&&statusFilter.value)||(targetFilter&&targetFilter.value)?searchData.filter(function(entry){return matches(entry,term);}):searchData).slice(0,50);results.innerHTML=filtered.map(function(entry){return \"<div role='listitem' class='search-hit'><a href='#\"+entry.anchor+\"' aria-label='Jump to \" + entry.title + \"'>\"+entry.title+\"</a> <span class='provenance'>(\"+entry.const+\")</span>\"+(entry.aliases.length?\" <span class='provenance'>aliases: \"+entry.aliases.join(', ')+\"</span>\":\"\")+\"<div class='concept-metrics'><span class='concept-chip'>T generators: \"+entry.generator_count+\"</span><span class='concept-chip'>F elements: \"+entry.fragment_size+\"</span>\"+(entry.failure?\"<span class='concept-chip failure'>&#8869;_fail</span>\":\"\")+\"</div></div>\";}).join('')||\"<p>No matches</p>\";if(status){const parts=[];if(term){parts.push(`query \"${q.trim()}\"`);}if(statusFilter&&statusFilter.value){parts.push(`status ${statusFilter.value}`);}if(targetFilter&&targetFilter.value){parts.push(`target ${targetFilter.value}`);}const base=`${filtered.length} result${filtered.length===1?'':'s'} shown of ${searchData.length}`;status.textContent=parts.length?`${base} for ${parts.join(', ')}`:base;}}populateFilters(searchData);renderResults('');searchInput.addEventListener('input',e=>renderResults(e.target.value));if(statusFilter){statusFilter.addEventListener('change',()=>renderResults(searchInput.value||''));}if(targetFilter){targetFilter.addEventListener('change',()=>renderResults(searchInput.value||''));}</script>"
            "</section>"
        )
        delta_section = ""
        if delta:
            ann = "".join(f"<li>{c}: {s}</li>" for c, s in delta.get("ann_changes", {}).items()) or "<li>none</li>"
            refc = "".join(f"<li>{c}: {s}</li>" for c, s in delta.get("reference_changes", {}).items()) or "<li>none</li>"
            delta_section = (
                "<section class='panel' role='region' aria-labelledby='delta-summary'>"
                "<h2 id='delta-summary'>Delta summary</h2>"
                f"<div>Baseline present: {delta.get('baseline_present', False)}</div>"
                f"<div>Annotation changes:<ul>{ann}</ul></div>"
                f"<div>Reference changes:<ul>{refc}</ul></div>"
                "</section>"
            )
        outline_links = []
        outline_links.append("<li><a href='#concept-search'>Search</a></li>")
        outline_links.append("<li><a href='#build-info'>Build metadata</a></li>")
        outline_links.append("<li><a href='#reference-graph'>Reference graph</a></li>")
        outline_links.append("<li><a href='#equivalence-classes'>Equivalence classes</a></li>")
        if delta_section:
            outline_links.append("<li><a href='#delta-summary'>Delta summary</a></li>")
        outline_links.extend(
            "".join(
                [
                    f"<li><a href='#{c['anchor']}'>{c['title']}</a>",
                    (
                        "<span class='concept-ann' aria-label='Ann_X(k) terms for {const}'>Ann_X(k): {terms}</span>".format(
                            const=c["const"], terms=", ".join(c.get("ann_terms", []))
                        )
                        if c.get("ann_terms")
                        else ""
                    ),
                    f"<span class='concept-chip'>T generators: {c['generator_count']}</span>",
                    f"<span class='concept-chip'>F elements: {c['fragment_size']}</span>",
                    "<span class='concept-chip failure'>⊥_fail</span>" if c["is_failure"] else "",
                    "</li>",
                ]
            )
            for c in rendered
        )
        outline_links.insert(0, "<li><a href='#build-info'>Build metadata</a></li>")
        outline_nav = (
            "<nav class='toc' aria-label='Document outline'>"
            "<h2>Document outline</h2>"
            "<ul>" + "".join(outline_links) + "</ul>"
            "</nav>"
        )
        build_section = (
            "<section class='panel' role='region' aria-labelledby='build-info'>"
            "<h2 id='build-info'>Build metadata</h2>"
            "<div class='status-grid'>"
            f"<div class='status-item'><span class='status-label'>Projection</span><span class='status-value'>{build['projection']}</span></div>"
            f"<div class='status-item'><span class='status-label'>Mode</span><span class='status-value'>{build.get('mode')}</span></div>"
            f"<div class='status-item'><span class='status-label'>Cache</span><span class='status-value'>{build.get('cache_status')}</span></div>"
            f"<div class='status-item'><span class='status-label'>Config hash</span><span class='status-value'>{build['config_hash']}</span></div>"
            f"<div class='status-item'><span class='status-label'>Repo fingerprint</span><span class='status-value'>{build['repo_fingerprint']}</span></div>"
            f"<div class='status-item'><span class='status-label'>Sanitize HTML</span><span class='status-value'>{build['sanitize_html']}</span></div>"
            f"<div class='status-item'><span class='status-label'>Lang</span><span class='status-value'>{build['html_lang']}</span></div>"
            f"<div class='status-item'><span class='status-label'>Assets inline</span><span class='status-value'>{build['assets_inline']}</span></div>"
            f"<div class='status-item'><span class='status-label'>Assets minify</span><span class='status-value'>{build['assets_minify']}</span></div>"
            + (
                f"<div class='status-item'><span class='status-label'>Manifest</span><span class='status-value'><a href='{manifest_href}'>manifest.json</a></span></div>"
                if manifest_href
                else "<div class='status-item'><span class='status-label'>Manifest</span><span class='status-value'>inline</span></div>"
            )
            + "</div>"
            + "</section>"
        )
        equivalence_items = "".join(
            (
                f"<li><a href='#{entry['anchor']}' aria-label='Jump to {entry['title']}'>{entry['title']}</a>"
                + f" <span class='provenance'>({entry['const']})</span>"
                + (
                    "<ul aria-label='Aliases for {const}'>".format(const=entry["const"])
                    + "".join(f"<li>{alias}</li>" for alias in entry["aliases"])
                    + "</ul>"
                    if entry["aliases"]
                    else "<p>No aliases</p>"
                )
                + "</li>"
            )
            for entry in equivalence_classes
        )
        equivalence_section = (
            "<section class='panel' role='region' aria-labelledby='equivalence-classes'>"
            "<h2 id='equivalence-classes'>Equivalence classes</h2>"
            "<p class='provenance'>Canonical constants and their declared equivalents.</p>"
            f"<ul>{equivalence_items}</ul>"
            "</section>"
        )
        reference_section_items = []
        for entry in reference_graph_entries:
            resolved = "".join(
                f"<li><a href='#{ref}' aria-label='Resolved reference to {ref}'>{ref}</a></li>" for ref in entry["resolved"]
            )
            backlinks = "".join(
                f"<li><a href='#{ref}' aria-label='Backlink from {ref} to {entry['anchor']}'>{ref}</a></li>"
                for ref in entry["backlinks"]
            )
            reference_section_items.append(
                "<li>"
                f"<div class='reference-row'><a href='#{entry['anchor']}'>{entry['title']}</a>"
                f"<span class='concept-chip'>Resolved: {len(entry['resolved'])}</span>"
                f"<span class='concept-chip'>Backlinks: {len(entry['backlinks'])}</span>"
                "</div>"
                f"<div class='reference-lists'><div><h3>Resolved</h3><ul>{resolved or '<li>None</li>'}</ul></div>"
                f"<div><h3>Backlinks</h3><ul>{backlinks or '<li>None</li>'}</ul></div></div>"
                "</li>"
            )

        reference_section = (
            "<section class='panel' role='region' aria-labelledby='reference-graph'>"
            "<h2 id='reference-graph'>Reference graph</h2>"
            "<p>Resolved references and backlinks per canonical concept.</p>"
            "<ul class='reference-graph'>" + "".join(reference_section_items) + "</ul>"
            "</section>"
        )

        section_parts = [search_section, build_section, equivalence_section, reference_section]
        for c in rendered:
            status = (
                "<section class='status-banner' role='status' aria-live='polite'>"
                "<p class='sr-only'>Concept status summary</p>"
                "<div class='status-grid'>"
                f"<div class='status-item'><span class='status-label'>Fragment</span><span class='status-value'>{len(c['fragment'].elements)}"
                f" element{'s' if len(c['fragment'].elements) != 1 else ''}{' (failure fragment)' if c['fragment'].is_failure else ''}</span></div>"
                f"<div class='status-item'><span class='status-label'>Backlinks</span><span class='status-value'>{len(c['backlinks'])}</span></div>"
                f"<div class='status-item'><span class='status-label'>Resolved refs</span><span class='status-value'>{len(c['resolved_refs'])}</span></div>"
                f"<div class='status-item'><span class='status-label'>Unresolved</span><span class='status-value'>{len(c['unresolved'])}</span></div>"
                "</div></section>"
            )
            toc_links = [
                f"<li><a href='#build-info-{c['anchor']}'>Build metadata</a></li>",
                f"<li><a href='#content-{c['anchor']}'>Content</a></li>",
                f"<li><a href='#math-object-{c['anchor']}'>Math object</a></li>",
                f"<li><a href='#provenance-{c['anchor']}'>Provenance</a></li>",
            ]
            if c["concept_delta"]:
                toc_links.append(f"<li><a href='#delta-{c['anchor']}'>Delta</a></li>")
            if c["resolved_refs"]:
                toc_links.append(f"<li><a href='#resolved-{c['anchor']}'>Resolved references</a></li>")
            if c["backlinks"]:
                toc_links.append(f"<li><a href='#backlinks-{c['anchor']}'>Backlinks</a></li>")
            if c["unresolved"]:
                toc_links.append(f"<li><a href='#unresolved-{c['anchor']}'>Unresolved references</a></li>")
            toc = "<nav class='toc' aria-label='In-page navigation'><h2>In-page navigation</h2><ul>" + "".join(toc_links) + "</ul></nav>"
            pager = "<nav class='pager' aria-label='Adjacent concepts'>"
            if c["prev_link"]:
                pager += (
                    "<a class='pager-link' href='#{anchor}' aria-label='Previous concept {title}'>&larr; Previous: {title}</a>".format(
                        anchor=c["prev_link"]["anchor"], title=c["prev_link"]["title"]
                    )
                )
            else:
                pager += "<span class='pager-link disabled'>Start</span>"
            if c["next_link"]:
                pager += (
                    "<a class='pager-link' href='#{anchor}' aria-label='Next concept {title}'>Next: {title} &rarr;</a>".format(
                        anchor=c["next_link"]["anchor"], title=c["next_link"]["title"]
                    )
                )
            else:
                pager += "<span class='pager-link disabled'>End</span>"
            pager += "</nav>"
            backlinks = "".join(f"<li><a href='#{b}'>{b}</a></li>" for b in c["backlinks"])
            resolved = "".join(
                f"<li><a href='#{r}' aria-label='Resolved reference to {r}'>{r}</a></li>" for r in c["resolved_refs"]
            )
            unresolved = "".join(f"<li>{u}</li>" for u in c["unresolved"])
            equivalents = ", ".join(c["same_as"])
            generators = "".join(
                (
                    f"<li><code>{g['surface']}</code> → <span class='generator-value'>{g['value']}</span>"
                    + (" <span class='failure'>⊥_fail</span>" if g["is_failure"] else "")
                    + (
                        "<ul>" + "".join(f"<li>{step.kind}: {step.detail}</li>" for step in g["provenance"]) + "</ul>"
                        if g["provenance"]
                        else ""
                    )
                    + "</li>"
                )
                for g in c["generators"]
            )
            fragment_elements = "".join(
                f"<li><span class='generator-value'>{val}</span></li>" for val in c["fragment_elements"]
            )
            generator_prov = "".join(
                (
                    f"<li><code>{g['surface']}</code>"
                    + (
                        "<ul>" + "".join(f"<li>{step.kind}: {step.detail}</li>" for step in g.get("provenance", [])) + "</ul>"
                        if g.get("provenance")
                        else "<span class='provenance'>No provenance recorded.</span>"
                    )
                    + "</li>"
                )
                for g in c["generators"]
            )
            fragment_prov = "".join(
                (
                    f"<li>{element}<ul>"
                    + "".join(f"<li>{step.kind}: {step.detail}</li>" for step in prov.steps)
                    + "</ul></li>"
                )
                for element, prov in c["fragment"].provenance.items()
            ) or "<li><span class='provenance'>No fragment provenance recorded.</span></li>"
            section_parts.append(
                f"<article id='{c['anchor']}'>"
                f"<header><p class='provenance'>Canonical anchor: <span class='failure'>#{c['anchor']}</span></p>"
                f"<h1 id='concept-{c['anchor']}'>{c['title']}</h1>"
                f"<p><strong>Const:</strong> {c['const']}</p>"
                + (f"<p>Equivalent IDs: {equivalents}</p>" if equivalents else "")
                + ("<p class='tags' aria-label='Tags'>" + "".join(f"<span class='tag'>{t}</span>" for t in c["tags"]) + "</p>" if c["tags"] else "")
                + "</header>"
                + status
                + pager
                + toc
                + f"<section class='panel' role='region' aria-labelledby='build-info-{c['anchor']}'>"
                + f"<h2 id='build-info-{c['anchor']}'>Build metadata</h2>"
                + "<dl>"
                + f"<div><dt>Projection</dt><dd>{build.get('projection')}</dd></div>"
                + f"<div><dt>Mode</dt><dd>{build.get('mode')}</dd></div>"
                + f"<div><dt>Cache</dt><dd>{build.get('cache_status')}</dd></div>"
                + f"<div><dt>Config hash</dt><dd>{build.get('config_hash')}</dd></div>"
                + f"<div><dt>Repo fingerprint</dt><dd>{build.get('repo_fingerprint')}</dd></div>"
                + f"<div><dt>Sanitize HTML</dt><dd>{build.get('sanitize_html')}</dd></div>"
                + f"<div><dt>Lang</dt><dd>{build.get('html_lang')}</dd></div>"
                + f"<div><dt>Assets inline</dt><dd>{build.get('assets_inline')}</dd></div>"
                + f"<div><dt>Assets minify</dt><dd>{build.get('assets_minify')}</dd></div>"
                + (
                    f"<div><dt>Manifest</dt><dd><a href='{manifest_href}'>manifest.json</a></dd></div>"
                    if manifest_href
                    else "<div><dt>Manifest</dt><dd>inline</dd></div>"
                )
                + "</dl></section>"
                + f"<section class='panel' role='region' aria-labelledby='content-{c['anchor']}'><h2 id='content-{c['anchor']}'>Content</h2>"
                + f"<div class='body'>{c['body']}</div></section>"
                + f"<section class='panel' role='region' aria-labelledby='math-object-{c['anchor']}'>"
                + f"<h2 id='math-object-{c['anchor']}'>Math object</h2>"
                + f"<div>Ann_X(k): {c['ann_terms']}</div>"
                + "<div class='math-lists'>"
                + "<div><h3>T_{k,X} generators</h3><ul>" + generators + "</ul></div>"
                + "<div><h3>F_{k,X} fragment elements</h3><ul>" + fragment_elements + "</ul></div>"
                + "</div>"
                + f"<div>Fragment size: {len(c['fragment'].elements)}</div>"
                + f"<div>Failure fragment: {c['fragment'].is_failure}</div>"
                + f"<div>Closure trace: {'/'.join(c['sem'].closure_trace.steps)}</div>"
                + "</section>"
                + (
                    f"<section class='panel' role='region' aria-labelledby='provenance-{c['anchor']}'>"
                    f"<h2 id='provenance-{c['anchor']}'>Provenance</h2>"
                    "<div class='status-grid provenance-grid'>"
                    f"<div class='status-item'><span class='status-label'>Generators</span><span class='status-value'>{len(c['generators'])}</span></div>"
                    f"<div class='status-item'><span class='status-label'>Fragment elements</span><span class='status-value'>{len(c['fragment'].elements)}</span></div>"
                    "</div>"
                    "<div class='math-lists'>"
                    f"<div><h3>Generator provenance</h3><ul>{generator_prov}</ul></div>"
                    f"<div><h3>Fragment provenance</h3><ul>{fragment_prov}</ul></div>"
                    "</div>"
                    "</section>"
                )
                + (
                    f"<section class='panel' role='region' aria-labelledby='delta-{c['anchor']}'>"
                    f"<h2 id='delta-{c['anchor']}'>Delta</h2>"
                    "<div class='status-grid'>"
                    f"<div class='status-item'><span class='status-label'>Baseline present</span><span class='status-value'>{c['concept_delta'].get('baseline_present', False)}</span></div>"
                    f"<div class='status-item'><span class='status-label'>Ann_X(k)</span><span class='status-value'>{c['concept_delta'].get('ann_status') or 'unchanged'}</span></div>"
                    f"<div class='status-item'><span class='status-label'>References</span><span class='status-value'>{c['concept_delta'].get('ref_status') or 'unchanged'}</span></div>"
                    "</div>"
                    f"<div><h3>Unresolved added</h3><ul>{''.join(f'<li>{ref}</li>' for ref in c['concept_delta'].get('unresolved_added', [])) or '<li>None</li>'}</ul></div>"
                    f"<div><h3>Unresolved removed</h3><ul>{''.join(f'<li>{ref}</li>' for ref in c['concept_delta'].get('unresolved_removed', [])) or '<li>None</li>'}</ul></div>"
                    "</section>"
                    if c["concept_delta"]
                    else ""
                )
                + (
                    f"<section class='panel' role='region' aria-labelledby='resolved-{c['anchor']}'>"
                    f"<h2 id='resolved-{c['anchor']}'>Resolved references</h2>"
                    f"<ul aria-label='Resolved references declared by {c['anchor']}'>{resolved}</ul>"
                    f"</section>"
                    if resolved
                    else ""
                )
                + (f"<section class='panel' role='region' aria-labelledby='backlinks-{c['anchor']}'><h2 id='backlinks-{c['anchor']}'>Backlinks</h2><ul aria-label='Backlinks pointing to {c['anchor']}'>{backlinks}</ul></section>" if backlinks else "")
                + (
                    f"<section class='panel diagnostics' role='alert' aria-live='assertive' aria-labelledby='unresolved-{c['anchor']}'>"
                    f"<h2 id='unresolved-{c['anchor']}'>Unresolved references</h2>"
                    f"<ul aria-label='Unresolved references declared by {c['anchor']}'>{unresolved}</ul></section>"
                    if unresolved
                    else ""
                )
                + "<p class='back-to-top'><a href='#top' aria-label='Back to the top of this document'>Back to top</a></p>"
                + "</article>"
            )
        sections = "".join(section_parts)
        manifest_block = f"<script type='application/json' id='sscu-manifest'>{json.dumps(manifest)}</script>"
        html = (
            f"<!DOCTYPE html><html lang='{html_lang}'>"
            "<head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<meta name='color-scheme' content='light dark'><title>SSCU Concepts</title>"
            f"<style>{fallback_style}</style></head>"
            "<body id='top'>"
            "<a href='#content' class='skip-link'>Skip to main content</a>"
            "<header role='banner'><nav aria-label='Primary'><a href='#top'>Top</a></nav></header>"
            "<div class='page'><main id='content' role='main'>"
            f"{outline_nav}{delta_section}{sections}{manifest_block}"
            "</main></div></body></html>"
        )

    return "single.html", html.encode()
