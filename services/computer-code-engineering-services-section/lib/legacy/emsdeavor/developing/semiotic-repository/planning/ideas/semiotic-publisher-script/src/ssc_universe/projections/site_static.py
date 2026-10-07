from __future__ import annotations

import hashlib
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple

try:  # pragma: no cover - prefer jinja2
    from jinja2 import Environment, FileSystemLoader, select_autoescape
except Exception:  # pragma: no cover
    Environment = None

from ..markdown_parse import MarkdownRenderer
from ..sscu_model import UniverseInstance
from .ordering import canonical_order
from .styles import FALLBACK_STYLE, base_stylesheet
from ..annterm import FAIL_BOTTOM


def _env(template_dir: Path, sanitize: bool, mathjax: bool, html_lang: str):
    if Environment is None:
        return None
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.globals["mathjax"] = mathjax
    env.globals["sanitize"] = sanitize
    env.globals["html_lang"] = html_lang
    return env


def render_site(
    instance: UniverseInstance,
    template_dir: Path,
    mathjax: bool,
    relroot: str = "",
    build_info: Dict | None = None,
    delta: Dict | None = None,
    assets_inline: bool = True,
    assets_minify: bool = False,
    manifest_path: str = "manifest.json",
    include: List[str] | None = None,
) -> Tuple[List[Tuple[Path, bytes]], List[Dict]]:
    sanitize = getattr(instance, "sanitize_html", True)
    html_lang = getattr(instance, "html_lang", "en")
    build = {
        "projection": "site:static",
        "mode": build_info.get("mode") if build_info else None,
        "cache_status": build_info.get("cache_status") if build_info else None,
        "config_hash": instance.config_hash,
        "repo_fingerprint": instance.repo_fingerprint,
        "sanitize_html": sanitize,
        "html_lang": html_lang,
        "assets_inline": assets_inline,
        "assets_minify": assets_minify,
        "mathjax": mathjax,
        "manifest_href": None,
        "sitemap_href": None,
    }
    build["sitemap_href"] = _rel_manifest("sitemap.xml", Path("index.html"))
    env = _env(template_dir, sanitize, mathjax, html_lang)
    markdown = MarkdownRenderer(sanitize=sanitize)
    files: List[Tuple[Path, bytes]] = []
    css_text = base_stylesheet(minify=assets_minify)
    css_bytes = css_text.encode()
    css_hash = hashlib.sha256(css_bytes).hexdigest()
    css_asset: Path | None = None
    assets: List[Dict] = [
        {
            "path": None,
            "hash": css_hash,
            "inline": assets_inline,
            "bytes": len(css_bytes),
            "minified": assets_minify,
            "kind": "stylesheet",
        }
    ]
    if not assets_inline:
        css_asset = Path(f"assets/style-{css_hash[:12]}.css")
        files.append((css_asset, css_bytes))
        assets[0]["path"] = css_asset.as_posix()

    rendered_concepts = []
    tag_map: Dict[str, List[dict]] = {}
    equivalence_classes = []
    search_index: List[Dict] = []
    sitemap_urls: List[str] = [f"{relroot}index.html"]

    include_set = set(include) if include else None
    ordered_concepts = canonical_order(instance)
    if include_set is not None:
        ordered_concepts = [entry for entry in ordered_concepts if entry["rep"] in include_set]
    order_index = {entry["rep"]: idx for idx, entry in enumerate(ordered_concepts)}

    filtered_unresolved = [
        (src, target)
        for src, target in instance.unresolved
        if (include_set is None or instance.representative(src) in include_set)
    ]
    unresolved_map: Dict[str, List[str]] = {}
    for src, target in filtered_unresolved:
        rep = instance.representative(src)
        unresolved_map.setdefault(rep, []).append(target)

    ann_delta = delta.get("ann_changes", {}) if delta else {}
    ref_delta = delta.get("reference_changes", {}) if delta else {}
    unresolved_added_map: Dict[str, List[str]] = {}
    unresolved_removed_map: Dict[str, List[str]] = {}
    if delta:
        for src, target in delta.get("unresolved", {}).get("added", []):
            unresolved_added_map.setdefault(src, []).append(target)
        for src, target in delta.get("unresolved", {}).get("removed", []):
            unresolved_removed_map.setdefault(src, []).append(target)

    failure_fragments_count = len(instance.failures)
    if include_set is not None:
        failure_fragments_count = sum(
            1 for rep, frag in instance.fragments.items() if rep in include_set and frag.is_failure
        )
    diagnostics = {
        "unresolved_count": len(filtered_unresolved),
        "failures_count": failure_fragments_count,
        "unresolved_by_source": [],
        "failure_fragments": [],
        "failures": sorted(map(repr, instance.failures)),
    }
    reference_graph_entries = []

    for idx, entry in enumerate(ordered_concepts):
        rep = entry["rep"]
        concept = entry["concept"]
        aliases = entry["aliases"]
        prev_entry = ordered_concepts[idx - 1] if idx > 0 else None
        next_entry = ordered_concepts[idx + 1] if idx + 1 < len(ordered_concepts) else None
        prev_link = None
        next_link = None
        if prev_entry:
            prev_link = {"anchor": prev_entry["rep"], "title": prev_entry["concept"].title}
        if next_entry:
            next_link = {"anchor": next_entry["rep"], "title": next_entry["concept"].title}
        anchor = rep
        sitemap_urls.append(f"{relroot}{anchor}.html")
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
        unresolved = unresolved_map.get(rep, [])
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
        reference_graph_entries.append(
            {
                "anchor": anchor,
                "title": concept.title,
                "const": concept.const,
                "resolved": resolved_refs,
                "backlinks": backlinks,
            }
        )
        concept_delta = None
        if delta:
            ann_status = ann_delta.get(rep)
            ref_status = ref_delta.get(rep)
            unresolved_add = sorted(unresolved_added_map.get(rep, []))
            unresolved_remove = sorted(unresolved_removed_map.get(rep, []))
            if ann_status or ref_status or unresolved_add or unresolved_remove:
                concept_delta = {
                    "ann_status": ann_status,
                    "ref_status": ref_status,
                    "unresolved_added": unresolved_add,
                    "unresolved_removed": unresolved_remove,
                    "baseline_present": delta.get("baseline_present", False),
                }

        style_href, style_inline = _style_for(css_asset, css_text, Path(f"{anchor}.html"))
        if env:
            page_tpl = env.get_template("page.html")
            html = page_tpl.render(
                title=concept.title,
                concept=concept,
                body=body_html,
                fragment=fragment,
                sem=sem,
                ann_terms=ann_terms,
                generators=generator_steps,
                fragment_elements=fragment_elements,
                anchor=anchor,
                backlinks=backlinks,
                unresolved=unresolved,
                resolved_refs=resolved_refs,
                concept_delta=concept_delta,
                relroot=relroot,
                prev_link=prev_link,
                next_link=next_link,
                style_href=style_href,
                style_inline=style_inline,
                html_lang=html_lang,
                build_info=build,
                manifest_href=_rel_manifest(manifest_path, Path(f"{anchor}.html")),
            )
        else:
            html = _manual_page(
                concept,
                body_html,
                fragment,
                sem,
                ann_terms,
                generator_steps,
                fragment_elements,
                anchor,
                backlinks,
                resolved_refs,
                unresolved,
                concept_delta,
                relroot,
                prev_link,
                next_link,
                _style_tag(style_href, style_inline),
                html_lang,
                build,
                _rel_manifest(manifest_path, Path(f"{anchor}.html")),
            )
        files.append((Path(f"{anchor}.html"), html.encode()))
        rendered_concepts.append(
            {
                "anchor": anchor,
                "title": concept.title,
                "const": concept.const,
                "aliases": aliases,
                "ann_terms": ann_terms,
                "generator_count": len(generator_steps),
                "fragment_size": len(fragment.elements),
                "is_failure": fragment.is_failure,
            }
        )
        equivalence_classes.append(
            {
                "anchor": anchor,
                "title": concept.title,
                "const": concept.const,
                "aliases": aliases,
            }
        )
        search_index.append(
            {
                "anchor": anchor,
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
                "resolved": resolved_refs,
                "backlinks": backlinks,
                "unresolved": unresolved,
                "summary": " ".join(concept.body.split())[:280],
            }
        )
        for tag in concept.tags:
            tag_map.setdefault(tag, []).append(
                {
                    "anchor": anchor,
                    "title": concept.title,
                    "ann_terms": ann_terms,
                    "generator_count": len(generator_steps),
                    "fragment_size": len(fragment.elements),
                    "is_failure": fragment.is_failure,
                }
            )

        if unresolved:
            diagnostics["unresolved_by_source"].append(
                {
                    "anchor": anchor,
                    "title": concept.title,
                    "const": concept.const,
                    "targets": sorted(unresolved),
                }
            )
        if fragment.is_failure:
            diagnostics["failure_fragments"].append(
                {"anchor": anchor, "title": concept.title, "const": concept.const}
            )

    linked_delta = None
    if delta:
        linked_delta = {
            "baseline_present": delta.get("baseline_present", False),
            "failures": delta.get("failures", {}),
            "unresolved": delta.get("unresolved", {}),
            "ann_changes": [],
            "reference_changes": [],
        }

        for const, status in sorted(delta.get("ann_changes", {}).items()):
            concept = instance.canonical_concepts.get(const)
            linked_delta["ann_changes"].append(
                {
                    "const": const,
                    "status": status,
                    "anchor": const if concept else None,
                    "title": concept.title if concept else const,
                }
            )
        for const, status in sorted(delta.get("reference_changes", {}).items()):
            concept = instance.canonical_concepts.get(const)
            linked_delta["reference_changes"].append(
                {
                    "const": const,
                    "status": status,
                    "anchor": const if concept else None,
                    "title": concept.title if concept else const,
                }
            )

    search_bytes = json.dumps(search_index, indent=2).encode()
    search_hash = hashlib.sha256(search_bytes).hexdigest()
    search_path = Path(f"search-index-{search_hash[:12]}.json")
    assets.append(
        {
            "path": search_path.as_posix(),
            "hash": search_hash,
            "inline": False,
            "bytes": len(search_bytes),
            "minified": False,
            "kind": "search-index",
        }
    )
    sitemap_urls.append(f"{relroot}{search_path.as_posix()}")

    build["sitemap_href"] = _rel_manifest("sitemap.xml", Path("index.html"))

    index_style_href, index_inline = _style_for(css_asset, css_text, Path("index.html"))
    if env:
        index_tpl = env.get_template("index.html")
        index_html = index_tpl.render(
            title="Index",
            concepts=rendered_concepts,
            diagnostics=diagnostics,
            delta=linked_delta,
            reference_graph=reference_graph_entries,
            equivalence_classes=equivalence_classes,
            relroot=relroot,
            build_info=build,
            style_href=index_style_href,
            style_inline=index_inline,
            html_lang=html_lang,
            manifest_href=_rel_manifest(manifest_path, Path("index.html")),
            search_href=search_path.as_posix(),
        )
    else:
        manifest_href = _rel_manifest(manifest_path, Path("index.html"))
        index_items = "".join(
            (
                f"<li><a href='{relroot}{c['anchor']}.html'>{c['title']}</a> ({c['const']})"
                + (f" <span class='provenance'>(aliases: {', '.join(c['aliases'])})</span>" if c["aliases"] else "")
                + ("<div class='concept-ann' aria-label='Ann_X(k) terms for {const}'>Ann_X(k): {terms}</div>".format(
                    const=c["const"], terms=", ".join(c.get("ann_terms", []))
                )
                if c.get("ann_terms")
                else "")
                + "<div class='concept-metrics' aria-label='Inferred structure for {const}'>".format(const=c["const"])
                + f"<span class='concept-chip'>T generators: {c['generator_count']}</span>"
                + f"<span class='concept-chip'>F elements: {c['fragment_size']}</span>"
                + ("<span class='concept-chip failure'>&#8869;_fail</span>" if c["is_failure"] else "")
                + "</div></li>"
            )
            for c in rendered_concepts
        )
        delta_block = ""
        if linked_delta:
            def _render_delta_entries(entries, section):
                rendered = []
                for entry in entries:
                    if entry.get("anchor"):
                        rendered.append(
                            f"<li><a href='{relroot}{entry['anchor']}.html#{section}-{entry['anchor']}' aria-label='Jump to {section} for {entry['title']} ({entry['const']})'>{entry['title']}</a>: {entry['status']}</li>"
                        )
                    else:
                        rendered.append(f"<li>{entry['const']}: {entry['status']}</li>")
                return "".join(rendered) or "<li>none</li>"

            ann = _render_delta_entries(linked_delta.get("ann_changes", []), "math-object")
            refc = _render_delta_entries(linked_delta.get("reference_changes", []), "backlinks")
            delta_block = (
                "<section class='panel' role='region' aria-labelledby='delta-summary'>"
                "<h2 id='delta-summary'>Delta summary</h2>"
                "<div class='status-grid'>"
                f"<div class='status-item'><span class='status-label'>Baseline present</span><span class='status-value'>{linked_delta.get('baseline_present', False)}</span></div>"
                f"<div class='status-item'><span class='status-label'>Failures added</span><span class='status-value'>{len(linked_delta.get('failures', {}).get('added', []))}</span></div>"
                f"<div class='status-item'><span class='status-label'>Failures removed</span><span class='status-value'>{len(linked_delta.get('failures', {}).get('removed', []))}</span></div>"
                f"<div class='status-item'><span class='status-label'>Unresolved added</span><span class='status-value'>{len(linked_delta.get('unresolved', {}).get('added', []))}</span></div>"
                f"<div class='status-item'><span class='status-label'>Unresolved removed</span><span class='status-value'>{len(linked_delta.get('unresolved', {}).get('removed', []))}</span></div>"
                "</div>"
                f"<div><h3>Annotation changes</h3><ul>{ann}</ul></div>"
                f"<div><h3>Reference changes</h3><ul>{refc}</ul></div>"
                "</section>"
            )
        diagnostics_block = ""
        if diagnostics:
            unresolved_items = "".join(
                "<li>"
                + (
                    f"<a href='{relroot}{entry['anchor']}.html#unresolved-{entry['anchor']}' aria-label='Jump to unresolved refere"
                    f"nces for {entry['title']} ({entry['const']})'>{entry['title']}</a>"
                )
                + "<ul>"
                + "".join(f"<li class='broken'>{t}</li>" for t in entry["targets"])
                + "</ul></li>"
                for entry in diagnostics.get("unresolved_by_source", [])
            ) or "<li>None</li>"
            failure_fragment_items = "".join(
                f"<li><a href='{relroot}{entry['anchor']}.html#math-object-{entry['anchor']}' aria-label='Jump to math object for {entry['title']} ({entry['const']})'>{entry['title']}</a></li>"
                for entry in diagnostics.get("failure_fragments", [])
            ) or "<li>None</li>"
            failure_values = "".join(f"<li><code>{f}</code></li>" for f in diagnostics.get("failures", [])) or "<li>None</li>"
            diagnostics_block = (
                "<section class='panel diagnostics' role='region' aria-labelledby='diagnostics-panel'>"
                "<h2 id='diagnostics-panel'>Diagnostics</h2>"
                "<div class='status-grid'>"
                f"<div class='status-item'><span class='status-label'>Unresolved</span><span class='status-value'>{diagnostics['unresolved_count']}</span></div>"
                f"<div class='status-item'><span class='status-label'>Failure fragments</span><span class='status-value'>{len(diagnostics['failure_fragments'])}</span></div>"
                f"<div class='status-item'><span class='status-label'>Failure values</span><span class='status-value'>{diagnostics['failures_count']}</span></div>"
                "</div>"
                "<h3 id='diagnostics-unresolved'>Unresolved references</h3>"
                f"<ul aria-labelledby='diagnostics-unresolved'>{unresolved_items}</ul>"
                "<h3 id='diagnostics-failure-fragments'>Failure fragments</h3>"
                f"<ul aria-labelledby='diagnostics-failure-fragments'>{failure_fragment_items}</ul>"
                "<h3 id='diagnostics-failure-values'>Failure values</h3>"
                f"<ul aria-labelledby='diagnostics-failure-values'>{failure_values}</ul>"
                "</section>"
            )
        build_block = (
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
            f"<div class='status-item'><span class='status-label'>Manifest</span><span class='status-value'><a href='{manifest_href}'>manifest.json</a></span></div>"
            f"<div class='status-item'><span class='status-label'>Sitemap</span><span class='status-value'><a href='{_rel_manifest('sitemap.xml', Path('index.html'))}'>sitemap.xml</a></span></div>"
            "</div>"
            "</section>"
        )
        search_block_template = """
            <section class='panel' role='region' aria-labelledby='concept-search'>
            <h2 id='concept-search'>Search</h2>
            <p class='provenance'>Search canonical concepts, tags, annotations, and equivalents.</p>
            <input type='search' id='search-box' aria-describedby='search-help' placeholder='Search concepts' data-index='__INDEX__'>
            <div class='search-controls' aria-label='Search filters'>
              <label for='search-status-filter'>Status
                <select id='search-status-filter'>
                  <option value=''>All statuses</option>
                </select>
              </label>
              <label for='search-target-filter'>Publish target
                <select id='search-target-filter'>
                  <option value=''>All targets</option>
                </select>
              </label>
            </div>
            <p id='search-help' class='provenance'>Results update as you type. Filtering is case-insensitive.</p>
            <p id='search-status' class='provenance' aria-live='polite'>Loading search index…</p>
            <div id='search-results' role='list' aria-label='Search results'></div>
            <script>
            const searchInput=document.getElementById('search-box');
            const results=document.getElementById('search-results');
            const status=document.getElementById('search-status');
            const statusFilter=document.getElementById('search-status-filter');
            const targetFilter=document.getElementById('search-target-filter');
            let searchData=[];
            function populateFilters(data){
              if(statusFilter){
                const statuses=Array.from(new Set(data.map(entry=>entry.status).filter(Boolean))).sort();
                statuses.forEach(val=>{const opt=document.createElement('option');opt.value=val;opt.textContent=val;statusFilter.appendChild(opt);});
              }
              if(targetFilter){
                const targets=new Set();
                data.forEach(entry=>{(entry.publish_to||[]).forEach(val=>targets.add(val));});
                Array.from(targets).sort().forEach(val=>{const opt=document.createElement('option');opt.value=val;opt.textContent=val;targetFilter.appendChild(opt);});
              }
            }
            function setStatus(count,total,query){if(!status)return;const parts=[];if(query){parts.push(`query "${query}"`);} if(statusFilter&&statusFilter.value){parts.push(`status ${statusFilter.value}`);} if(targetFilter&&targetFilter.value){parts.push(`target ${targetFilter.value}`);} const base=`${count} result${count===1?'':'s'} shown of ${total}`;status.textContent=parts.length?`${base} for ${parts.join(', ')}`:base;}
            function matches(entry,term){const statusVal=statusFilter?statusFilter.value:'';const targetVal=targetFilter?targetFilter.value:'';if(statusVal && (entry.status||'')!==statusVal){return false;}if(targetVal && !(entry.publish_to||[]).includes(targetVal)){return false;}if(!term){return true;}return entry.title.toLowerCase().includes(term)||entry.const.toLowerCase().includes(term)||entry.aliases.some(a=>a.toLowerCase().includes(term))||entry.tags.some(t=>t.toLowerCase().includes(term))||entry.ann_terms.some(a=>a.toLowerCase().includes(term));}
            function renderResults(query){const term=query.trim().toLowerCase();const filtered=(term||(statusFilter&&statusFilter.value)||(targetFilter&&targetFilter.value)?searchData.filter(function(entry){return matches(entry,term);}):searchData).slice(0,50);results.innerHTML=filtered.map(function(entry){return "<div role='listitem' class='search-hit'><a href='"+entry.anchor+".html#content-"+entry.anchor+"' aria-label='Jump to " + entry.title + "'>"+entry.title+"</a> <span class='provenance'>("+entry.const+")</span>"+(entry.aliases.length?" <span class='provenance'>aliases: "+entry.aliases.join(', ')+"</span>":"")+"<div class='concept-metrics'><span class='concept-chip'>T generators: "+entry.generator_count+"</span><span class='concept-chip'>F elements: "+entry.fragment_size+"</span>"+(entry.failure?"<span class='concept-chip failure'>&#8869;_fail</span>":"")+"</div></div>";}).join('')||"<p>No matches</p>";setStatus(filtered.length,searchData.length,term);}
            fetch(searchInput.dataset.index).then(r=>r.json()).then(data=>{searchData=data;populateFilters(searchData);renderResults(searchInput.value||'');}).catch(()=>{if(status){status.textContent='Search index unavailable';}});
            searchInput.addEventListener('input',e=>renderResults(e.target.value));
            if(statusFilter){statusFilter.addEventListener('change',()=>renderResults(searchInput.value||''));}
            if(targetFilter){targetFilter.addEventListener('change',()=>renderResults(searchInput.value||''));}
            </script>
            </section>
        """
        search_block = search_block_template.replace("__INDEX__", f"{relroot}{search_path.as_posix()}")
        toc_links = ["<li><a href='#concept-search'>Search</a></li>", "<li><a href='#concept-list'>Concepts</a></li>"]
        toc_links.insert(0, "<li><a href='#build-info'>Build metadata</a></li>")
        equivalence_block = ""
        if equivalence_classes:
            toc_links.append("<li><a href='#equivalence-classes'>Equivalence classes</a></li>")
            eq_items = "".join(
                (
                    f"<li><a href='{relroot}{entry['anchor']}.html#content-{entry['anchor']}' aria-label='Jump to {entry['title']} ({entry['const']})'>{entry['title']}</a>"
                    + f" <span class='provenance'>({entry['const']})</span>"
                    + (f"<ul aria-label='Aliases for {entry['const']}'>" + "".join(f"<li>{alias}</li>" for alias in entry["aliases"]) + "</ul>" if entry["aliases"] else "<p>No aliases</p>")
                    + "</li>"
                )
                for entry in equivalence_classes
            )
            equivalence_block = (
                "<section class='panel' role='region' aria-labelledby='equivalence-classes'>"
                "<h2 id='equivalence-classes'>Equivalence classes</h2>"
                "<p class='provenance'>Canonical constants and their declared equivalents.</p>"
                f"<ul>{eq_items}</ul>"
                "</section>"
            )
        if delta_block:
            toc_links.append("<li><a href='#delta-summary'>Delta summary</a></li>")
        if diagnostics_block:
            toc_links.append("<li><a href='#diagnostics-panel'>Diagnostics</a></li>")
        reference_block = ""
        if reference_graph_entries:
            toc_links.append("<li><a href='#reference-graph'>Reference graph</a></li>")
            ref_items = "".join(
                (
                    f"<li>"
                    f"<a href='{relroot}{entry['anchor']}.html#resolved-{entry['anchor']}' aria-label='Jump to resolved references for {entry['title']} ({entry['const']})'>{entry['title']}</a>"
                    + "<div class='concept-metrics' aria-label='Reference graph metrics for {const}'>".format(const=entry["const"])
                    + f"<span class='concept-chip'>Resolved: {len(entry['resolved'])}</span>"
                    + f"<span class='concept-chip'>Backlinks: {len(entry['backlinks'])}</span>"
                    + "</div>"
                    + ("<ul aria-label='Resolved references'>{}</ul>".format(
                        "".join(
                            f"<li><a href='{relroot}{ref}.html#content-{ref}' aria-label='Jump to {ref}'>{ref}</a></li>"
                            for ref in entry["resolved"]
                        )
                        or "<li>None</li>"
                    ))
                    + ("<ul aria-label='Backlinks'>{}</ul>".format(
                        "".join(
                            f"<li><a href='{relroot}{ref}.html#backlinks-{ref}' aria-label='Jump to backlinks for {ref}'>{ref}</a></li>"
                            for ref in entry["backlinks"]
                        )
                        or "<li>None</li>"
                    ))
                    + "</li>"
                )
                for entry in reference_graph_entries
            )
            reference_block = (
                "<section class='panel' role='region' aria-labelledby='reference-graph'>"
                "<h2 id='reference-graph'>Reference graph</h2>"
                "<p class='provenance'>Resolved and incoming references per canonical constant.</p>"
                f"<ul>{ref_items}</ul>"
                "</section>"
            )
        toc = "<nav class='toc' aria-label='Page sections'><h2>Page sections</h2><ul>" + "".join(toc_links) + "</ul></nav>"
        index_html = (
            f"<!DOCTYPE html><html lang='{html_lang}'>"
            "<head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<meta name='color-scheme' content='light dark'><title>Index</title>"
            f"{_style_tag(index_style_href, index_inline)}</head>"
            "<body id='top'>"
            "<a href='#content' class='skip-link'>Skip to main content</a>"
            f"<header role='banner'><nav aria-label='Primary'><a href='{relroot}index.html' aria-current='page'>Index</a></nav></header>"
            "<div class='page'><main id='content' role='main'>"
            "<h1>Index</h1>"
            + toc
            + build_block
            + search_block
            + "<section class='panel' role='region' aria-labelledby='concept-list'><h2 id='concept-list'>Concepts</h2>"
            f"<ul>{index_items}</ul></section>"
            + equivalence_block
            + reference_block
            + delta_block
            + diagnostics_block
            + "<p class='back-to-top'><a href='#top' aria-label='Back to the top of this page'>Back to top</a></p>"
            + "</main></div></body></html>"
        )
    files.append((Path("index.html"), index_html.encode()))
    files.append((search_path, search_bytes))

    for tag in sorted(tag_map.keys()):
        concepts = sorted(tag_map[tag], key=lambda c: order_index[c["anchor"]])
        tag_style_href, tag_style_inline = _style_for(css_asset, css_text, Path("tags") / f"{tag}.html")
        if env:
            tag_tpl = env.get_template("tag.html")
            tag_html = tag_tpl.render(
                title=f"Tag {tag}",
                tag=tag,
                concepts=concepts,
                relroot=relroot,
                style_href=tag_style_href,
                style_inline=tag_style_inline,
                html_lang=html_lang,
            )
        else:
            tag_items = "".join(
                (
                    f"<li><a href='{relroot}{c['anchor']}.html'>{c['title']}</a>"
                    + ("<div class='concept-ann' aria-label='Ann_X(k) terms for {anchor}'>Ann_X(k): {terms}</div>".format(
                        anchor=c["anchor"], terms=", ".join(c.get("ann_terms", []))
                    )
                    if c.get("ann_terms")
                    else "")
                    + "<div class='concept-metrics' aria-label='Inferred structure for {anchor}'>".format(anchor=c["anchor"])
                    + f"<span class='concept-chip'>T generators: {c['generator_count']}</span>"
                    + f"<span class='concept-chip'>F elements: {c['fragment_size']}</span>"
                    + ("<span class='concept-chip failure'>&#8869;_fail</span>" if c["is_failure"] else "")
                    + "</div></li>"
                )
                for c in concepts
            )
            tag_html = (
                f"<!DOCTYPE html><html lang='{html_lang}'>"
                "<head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
                "<meta name='color-scheme' content='light dark'><title>Tag</title>"
                f"{_style_tag(tag_style_href, tag_style_inline)}</head>"
                "<body id='top'>"
                "<a href='#content' class='skip-link'>Skip to main content</a>"
                f"<header role='banner'><nav aria-label='Primary'><a href='{relroot}index.html'>Index</a></nav></header>"
                "<div class='page'><main id='content' role='main'>"
                f"<h1>Tag: {tag}</h1>"
                "<section class='panel' role='region' aria-labelledby='tagged-concepts'>"
                "<h2 id='tagged-concepts'>Tagged concepts</h2>"
                f"<ul>{tag_items}</ul></section>"
                "<p class='back-to-top'><a href='#top' aria-label='Back to the top of this page'>Back to top</a></p>"
                "</main></div></body></html>"
            )
        files.append((Path(f"tags/{tag}.html"), tag_html.encode()))
        sitemap_urls.append(f"{relroot}tags/{tag}.html")

    sitemap_bytes = _sitemap_xml(sorted(set(sitemap_urls))).encode()
    sitemap_hash = hashlib.sha256(sitemap_bytes).hexdigest()
    sitemap_path = Path("sitemap.xml")
    files.append((sitemap_path, sitemap_bytes))
    assets.append(
        {
            "path": sitemap_path.as_posix(),
            "hash": sitemap_hash,
            "inline": False,
            "bytes": len(sitemap_bytes),
            "minified": False,
            "kind": "sitemap",
        }
    )

    return files, assets


def _style_for(css_asset: Path | None, css_text: str, target: Path) -> Tuple[str | None, str | None]:
    if css_asset:
        href = Path(os.path.relpath(css_asset, start=target.parent)).as_posix()
        return href, None
    return None, css_text


def _style_tag(style_href: str | None, style_inline: str | None) -> str:
    if style_href:
        return f"<link rel='stylesheet' href='{style_href}'>"
    return f"<style>{style_inline}</style>"


def _rel_manifest(manifest: str, target: Path) -> str:
    manifest_path = Path(manifest)
    try:
        return Path(os.path.relpath(manifest_path, start=target.parent)).as_posix()
    except Exception:
        return manifest_path.as_posix()


def _sitemap_xml(urls: List[str]) -> str:
    entries = "".join(f"  <url><loc>{url}</loc></url>" for url in urls)
    return "\n".join(
        [
            "<?xml version='1.0' encoding='UTF-8'?>",
            "<urlset xmlns='http://www.sitemaps.org/schemas/sitemap/0.9'>",
            entries,
            "</urlset>",
        ]
    )


def _format_value(val: object) -> str:
    if val == FAIL_BOTTOM:
        return "&#8869;_fail"
    if isinstance(val, tuple):
        return repr(tuple(val))
    return repr(val)


def _manual_page(
    concept,
    body_html,
    fragment,
    sem,
    ann_terms,
    generators,
    fragment_elements,
    anchor,
    backlinks,
    resolved_refs,
    unresolved,
    concept_delta,
    relroot,
    prev_link,
    next_link,
    style_tag,
    html_lang,
    build_info,
    manifest_href,
):
    prov_list = "".join(
        f"<li>{element}: "
        + "".join(f"<div>{step.kind}: {step.detail}</div>" for step in prov.steps)
        + "</li>"
        for element, prov in fragment.provenance.items()
    )
    backlinks_html = "".join(f"<li><a href='{relroot}{b}.html'>{b}</a></li>" for b in backlinks)
    resolved_html = "".join(
        f"<li><a href='{relroot}{r}.html' aria-label='Resolved reference to {r}'>{r}</a></li>" for r in resolved_refs
    )
    unresolved_html = "".join(f"<li>{u}</li>" for u in unresolved)
    equivalents = ", ".join(eq for eq in concept.same_as)
    status = (
        "<section class='status-banner' role='status' aria-live='polite'>"
        "<p class='sr-only'>Concept status summary</p>"
        "<div class='status-grid'>"
        f"<div class='status-item'><span class='status-label'>Fragment</span><span class='status-value'>{len(fragment.elements)}"
        f" element{'s' if len(fragment.elements) != 1 else ''}{' (failure fragment)' if fragment.is_failure else ''}</span></div>"
        f"<div class='status-item'><span class='status-label'>Backlinks</span><span class='status-value'>{len(backlinks)}</span></div>"
        f"<div class='status-item'><span class='status-label'>Resolved refs</span><span class='status-value'>{len(resolved_refs)}</span></div>"
        f"<div class='status-item'><span class='status-label'>Unresolved</span><span class='status-value'>{len(unresolved)}</span></div>"
        "</div></section>"
    )
    toc_links = [f"<li><a href='#content-{anchor}'>Content</a></li>", f"<li><a href='#math-object-{anchor}'>Math object</a></li>"]
    toc_links.insert(0, f"<li><a href='#build-info-{anchor}'>Build metadata</a></li>")
    toc_links.append(f"<li><a href='#provenance-{anchor}'>Provenance</a></li>")
    if concept_delta:
        toc_links.insert(1, f"<li><a href='#delta-{anchor}'>Delta</a></li>")
    if backlinks:
        toc_links.append(f"<li><a href='#backlinks-{anchor}'>Backlinks</a></li>")
    if resolved_refs:
        toc_links.append(f"<li><a href='#resolved-{anchor}'>Resolved references</a></li>")
    if unresolved:
        toc_links.append(f"<li><a href='#unresolved-{anchor}'>Unresolved references</a></li>")
    toc = "<nav class='toc' aria-label='In-page navigation'><h2>In-page navigation</h2><ul>" + "".join(toc_links) + "</ul></nav>"
    pager = "<nav class='pager' aria-label='Adjacent concepts'>"
    if prev_link:
        pager += (
            "<a class='pager-link' href='{href}' aria-label='Previous concept {title}'>".format(
                href=f"{relroot}{prev_link['anchor']}.html", title=prev_link["title"]
            )
            + f"← Previous: {prev_link['title']}</a>"
        )
    else:
        pager += "<span class='pager-link disabled'>Start</span>"
    if next_link:
        pager += (
            "<a class='pager-link' href='{href}' aria-label='Next concept {title}'>".format(
                href=f"{relroot}{next_link['anchor']}.html", title=next_link["title"]
            )
            + f"Next: {next_link['title']} →</a>"
        )
    else:
        pager += "<span class='pager-link disabled'>End</span>"
    pager += "</nav>"
    backlinks_section = (
        f"<section class='panel' role='region' aria-labelledby='backlinks-{anchor}'><h2 id='backlinks-{anchor}'>Backlinks</h2><ul aria-label='Backlinks pointing to {anchor}'>{backlinks_html}</ul></section>"
        if backlinks
        else ""
    )
    resolved_section = (
        f"<section class='panel' role='region' aria-labelledby='resolved-{anchor}'>"
        f"<h2 id='resolved-{anchor}'>Resolved references</h2>"
        f"<ul aria-label='Resolved references declared by {anchor}'>{resolved_html}</ul>"
        f"</section>"
        if resolved_refs
        else ""
    )
    unresolved_section = (
        f"<section class='panel diagnostics' role='alert' aria-live='assertive' aria-labelledby='unresolved-{anchor}'>"
        f"<h2 id='unresolved-{anchor}'>Unresolved references</h2><ul aria-label='Unresolved references declared by {anchor}'>{unresolved_html}</ul></section>"
        if unresolved
        else ""
    )
    delta_section = ""
    if concept_delta:
        added = "".join(f"<li>{t}</li>" for t in concept_delta.get("unresolved_added", [])) or "<li>None</li>"
        removed = "".join(f"<li>{t}</li>" for t in concept_delta.get("unresolved_removed", [])) or "<li>None</li>"
        delta_section = (
            f"<section class='panel' role='region' aria-labelledby='delta-{anchor}'>"
            f"<h2 id='delta-{anchor}'>Delta</h2>"
            "<div class='status-grid'>"
            f"<div class='status-item'><span class='status-label'>Baseline present</span><span class='status-value'>{concept_delta.get('baseline_present', False)}</span></div>"
            f"<div class='status-item'><span class='status-label'>Ann_X(k)</span><span class='status-value'>{concept_delta.get('ann_status') or 'unchanged'}</span></div>"
            f"<div class='status-item'><span class='status-label'>References</span><span class='status-value'>{concept_delta.get('ref_status') or 'unchanged'}</span></div>"
            "</div>"
            f"<div><h3>Unresolved added</h3><ul>{added}</ul></div>"
            f"<div><h3>Unresolved removed</h3><ul>{removed}</ul></div>"
            "</section>"
        )
    tags = "".join(f"<span class='tag'>{tag}</span>" for tag in concept.tags)
    return (
        f"<!DOCTYPE html><html lang='{html_lang}'>"
        "<head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<meta name='color-scheme' content='light dark'><title>SSCU Concept</title>"
        f"{style_tag}</head>"
        "<body id='top'>"
        "<a href='#content' class='skip-link'>Skip to main content</a>"
        f"<header role='banner'><nav aria-label='Primary'><a href='{relroot}index.html'>Index</a></nav></header>"
        "<div class='page'><main id='content' role='main'>"
        f"<article id='{anchor}' aria-labelledby='concept-{anchor}'>"
        f"<header><p class='provenance'>Canonical anchor: <span class='failure'>#{anchor}</span></p>"
        f"<h1 id='concept-{anchor}'>{concept.title}</h1>"
        f"<p><strong>Const:</strong> {concept.const}</p>"
        + (f"<p>Equivalent IDs: {equivalents}</p>" if equivalents else "")
        + (f"<p class='tags' aria-label='Tags'>{tags}</p>" if tags else "")
        + "</header>"
        + status
        + pager
        + toc
        + f"<section class='panel' role='region' aria-labelledby='build-info-{anchor}'><h2 id='build-info-{anchor}'>Build metadata</h2>"
        + "<dl>"
        + f"<div><dt>Projection</dt><dd>{build_info.get('projection')}</dd></div>"
        + f"<div><dt>Mode</dt><dd>{build_info.get('mode')}</dd></div>"
        + f"<div><dt>Cache</dt><dd>{build_info.get('cache_status')}</dd></div>"
        + f"<div><dt>Config hash</dt><dd>{build_info.get('config_hash')}</dd></div>"
        + f"<div><dt>Repo fingerprint</dt><dd>{build_info.get('repo_fingerprint')}</dd></div>"
        + f"<div><dt>Sanitize HTML</dt><dd>{build_info.get('sanitize_html')}</dd></div>"
        + f"<div><dt>Lang</dt><dd>{build_info.get('html_lang')}</dd></div>"
        + f"<div><dt>Assets inline</dt><dd>{build_info.get('assets_inline')}</dd></div>"
        + f"<div><dt>Assets minify</dt><dd>{build_info.get('assets_minify')}</dd></div>"
        + f"<div><dt>Manifest</dt><dd><a href='{manifest_href}'>manifest.json</a></dd></div>"
        + f"<div><dt>Sitemap</dt><dd><a href='{build_info.get('sitemap_href')}'>sitemap.xml</a></dd></div>"
        + "</dl></section>"
        + f"<section class='panel' role='region' aria-labelledby='content-{anchor}'><h2 id='content-{anchor}'>Content</h2>"
        + f"<div class='body'>{body_html}</div></section>"
        + f"<section class='panel' role='region' aria-labelledby='math-object-{anchor}'>"
        + f"<h2 id='math-object-{anchor}'>Math object</h2>"
        + f"<div>Ann_X(k): {ann_terms}</div>"
        + "<div class='math-lists'>"
        + "<div><h3>T_{k,X} generators</h3><ul>"
        + "".join(
            (
                f"<li><code>{g['surface']}</code> → <span class='generator-value'>{g['value']}</span>"
                + (" <span class='failure'>&#8869;_fail</span>" if g["is_failure"] else "")
                + ("<ul>" + "".join(f"<li>{step.kind}: {step.detail}</li>" for step in g["provenance"]) + "</ul>" if g["provenance"] else "")
                + "</li>"
            )
            for g in generators
        )
        + "</ul></div>"
        + "<div><h3>F_{k,X} fragment elements</h3><ul>"
        + "".join(f"<li><span class='generator-value'>{val}</span></li>" for val in fragment_elements)
        + "</ul></div></div>"
        + f"<div>Fragment size: {len(fragment.elements)}</div>"
        + f"<div>Failure fragment: {fragment.is_failure}</div>"
        + f"<div>Closure trace: {'/'.join(sem.closure_trace.steps)}</div>"
        + "</section>"
        + (
            f"<section class='panel' role='region' aria-labelledby='provenance-{anchor}'>"
            f"<h2 id='provenance-{anchor}'>Provenance</h2>"
            "<div class='status-grid provenance-grid'>"
            f"<div class='status-item'><span class='status-label'>Generators</span><span class='status-value'>{len(generators)}</span></div>"
            f"<div class='status-item'><span class='status-label'>Fragment elements</span><span class='status-value'>{len(fragment.elements)}</span></div>"
            "</div>"
            "<div class='math-lists'>"
            "<div><h3>Generator provenance</h3><ul>"
            + "".join(
                f"<li><code>{g['surface']}</code>"
                + (
                    "<ul>"
                    + "".join(f"<li>{step.kind}: {step.detail}</li>" for step in g.get("provenance", []))
                    + "</ul>"
                    if g.get("provenance")
                    else "<span class='provenance'>No provenance recorded.</span>"
                )
                + "</li>"
                for g in generators
            )
            + "</ul></div>"
            + "<div><h3>Fragment provenance</h3><ul>"
            + (
                prov_list
                if prov_list
                else "<li><span class='provenance'>No fragment provenance recorded.</span></li>"
            )
            + "</ul></div>"
            + "</div>"
            + "</section>"
        )
        + delta_section
        + resolved_section
        + backlinks_section
        + unresolved_section
        + "<p class='back-to-top'><a href='#top' aria-label='Back to the top of this page'>Back to top</a></p>"
        + "</article>"
        "</main></div></body></html>"
    )
