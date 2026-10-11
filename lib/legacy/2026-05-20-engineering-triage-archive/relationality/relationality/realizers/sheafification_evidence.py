from __future__ import annotations

from typing import Dict, List, Tuple

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    sheafification_evidence realizer.

    Inputs
    ------
    presheaf_site:
        Site carrier (kind ``presheaf_site``).
    presheaf:
        Presheaf carrier (kind ``presheaf``).

    Semantics
    ---------
    Realizes the SheafCondition act for a finite presheaf by:

    - re-checking presheaf functoriality against the site:
      identities act as identity maps on sections and composition
      satisfies ``res_{g∘f} = res_f ∘ res_g``; and
    - constructing, for each cover {U_i -> U}, the families of local
      sections obtained by restricting global sections s ∈ F(U) along
      the cover arrows, and checking that the induced map
      F(U) → Π_i F(U_i) is injective (uniqueness of gluings).

    In this concrete representation:
    - For an arrow ``f`` with restriction data
      ``restrictions[f] = {"from": V, "to": U, "map": F(V)->F(U)}``,
      we interpret ``f: U -> V`` and ``map`` as the restriction
      ``res_f : F(V) -> F(U)`` (contravariant in the site).
    - For each cover ``{f_i : U_i -> U}`` we consider all global
      sections s ∈ F(U) and record the induced family
      (res_{f_i}(s))_i as a matching family; uniqueness is enforced by
      requiring that distinct global sections never produce the same
      family.

    The evidence node records:
    - matching_families: a mapping cover_id → list of families
      (each family stores the arrows, local sections, and glued
      global section),
    - glued_sections: a canonical glued section label per cover
      (one distinguished global section for that cover), and
    - uniqueness_witnesses: a small summary of which laws were
      checked.

    Status is 'pass' iff all presheaf functoriality and gluing
    checks succeed; otherwise it is 'fail' and counterexample
    records the first failing law with details.
    """
    site = inputs.get("presheaf_site")
    presheaf = inputs.get("presheaf")
    if site is None or presheaf is None:
        raise KeyError("sheafification_evidence requires 'presheaf_site' and 'presheaf' inputs")
    if site.get("kind") != "presheaf_site":
        raise LawValidationError("sheafification_evidence presheaf_site input must have kind 'presheaf_site'")
    if presheaf.get("kind") != "presheaf":
        raise LawValidationError("sheafification_evidence presheaf input must have kind 'presheaf'")

    site_id = site.get("id")
    presheaf_site_id = presheaf.get("site_id")
    if isinstance(site_id, str) and isinstance(presheaf_site_id, str) and site_id != presheaf_site_id:
        raise LawValidationError("sheafification_evidence requires presheaf.site_id to match presheaf_site.id")

    objects: List[str] = list(presheaf.get("objects") or [])
    arrows: List[str] = list(presheaf.get("arrows") or [])
    sections: Dict[str, List[str]] = {obj: list(secs) for obj, secs in (presheaf.get("sections") or {}).items()}
    restrictions: Dict[str, dict] = dict(presheaf.get("restrictions") or {})

    def record_counterexample(law: str, details: Dict[str, object]) -> None:
        nonlocal counterexample
        if counterexample is None:
            ce = {"law": law}
            ce.update(details)
            counterexample = ce

    functor_ok = True
    sheaf_ok = True
    counterexample: Dict[str, object] | None = None

    # 1. Identity laws: for each object U, there is an identity arrow
    # id_U whose restriction acts as the identity on sections at U.
    identity = site.get("identity") or {}
    for obj in objects:
        id_arrow = identity.get(obj)
        if id_arrow is None:
            functor_ok = False
            record_counterexample(
                "presheaf_identity_missing",
                {"object": obj},
            )
            continue
        if id_arrow not in arrows:
            functor_ok = False
            record_counterexample(
                "presheaf_identity_not_in_arrows",
                {"object": obj, "id_arrow": id_arrow},
            )
            continue
        restr = restrictions.get(id_arrow)
        if restr is None:
            functor_ok = False
            record_counterexample(
                "presheaf_identity_missing_restriction",
                {"object": obj, "id_arrow": id_arrow},
            )
            continue
        src = restr.get("from")
        tgt = restr.get("to")
        if src != obj or tgt != obj:
            functor_ok = False
            record_counterexample(
                "presheaf_identity_wrong_domain_codom",
                {"object": obj, "id_arrow": id_arrow, "from": src, "to": tgt},
            )
            continue
        sec_obj = sections.get(obj, [])
        mapping = restr.get("map") or {}
        for s in sec_obj:
            image = mapping.get(s)
            if image != s:
                functor_ok = False
                record_counterexample(
                    "presheaf_identity_not_identity",
                    {"object": obj, "id_arrow": id_arrow, "section": s, "image": image},
                )
                break

    # 2. Composition laws: for each composable pair g ∘ f specified
    # in the site, restrictions must satisfy res_{g∘f} = res_f ∘ res_g.
    composition = site.get("composition") or {}
    for key, h in composition.items():
        parts = key.split("|")
        if len(parts) != 2:
            functor_ok = False
            record_counterexample(
                "presheaf_composition_key_malformed",
                {"key": key},
            )
            continue
        g, f = parts
        if f not in arrows or g not in arrows or h not in arrows:
            functor_ok = False
            record_counterexample(
                "presheaf_composition_arrow_missing",
                {"g": g, "f": f, "h": h},
            )
            continue
        restr_f = restrictions.get(f)
        restr_g = restrictions.get(g)
        restr_h = restrictions.get(h)
        if restr_f is None or restr_g is None or restr_h is None:
            functor_ok = False
            record_counterexample(
                "presheaf_composition_missing_restriction",
                {"g": g, "f": f, "h": h},
            )
            continue

        src_h = restr_h.get("from")
        src_g = restr_g.get("from")
        tgt_g = restr_g.get("to")
        src_f = restr_f.get("from")
        tgt_f = restr_f.get("to")
        tgt_h = restr_h.get("to")

        if not (src_h == src_g and tgt_h == tgt_f and tgt_g == src_f):
            functor_ok = False
            record_counterexample(
                "presheaf_composition_domains_incompatible",
                {
                    "g_from": src_g,
                    "g_to": tgt_g,
                    "f_from": src_f,
                    "f_to": tgt_f,
                    "h_from": src_h,
                    "h_to": tgt_h,
                },
            )
            continue

        src_obj = src_h
        sec_src = sections.get(src_obj, [])
        map_f = restr_f.get("map") or {}
        map_g = restr_g.get("map") or {}
        map_h = restr_h.get("map") or {}
        for s in sec_src:
            if s not in map_g or s not in map_h:
                functor_ok = False
                record_counterexample(
                    "presheaf_composition_missing_map_entry",
                    {"g": g, "f": f, "h": h, "section": s},
                )
                break
            mid = map_g[s]
            if mid not in map_f:
                functor_ok = False
                record_counterexample(
                    "presheaf_composition_missing_mid_image",
                    {"g": g, "f": f, "h": h, "section": s, "mid": mid},
                )
                break
            composed = map_f[mid]
            direct = map_h[s]
            if composed != direct:
                functor_ok = False
                record_counterexample(
                    "presheaf_composition_mismatch",
                    {
                        "g": g,
                        "f": f,
                        "h": h,
                        "section": s,
                        "res_g": mid,
                        "res_f_res_g": composed,
                        "res_h": direct,
                    },
                )
                break

    presheaf_covers = presheaf.get("covers") or []
    matching_families: Dict[str, List[dict]] = {}
    glued_sections: Dict[str, str] = {}

    for idx, cover in enumerate(presheaf_covers):
        obj = cover.get("object")
        cover_arrows: List[str] = sorted(cover.get("arrows") or [])
        key = f"cover_{idx}"

        family_to_global: Dict[Tuple[str, ...], str] = {}
        families_for_cover: List[dict] = []

        globals_at_obj = sections.get(obj, [])

        for s in globals_at_obj:
            local_assignments: Dict[str, str] = {}
            local_tuple: List[str] = []
            ok_for_s = True
            for arr in cover_arrows:
                restr = restrictions.get(arr)
                if restr is None:
                    sheaf_ok = False
                    record_counterexample(
                        "sheaf_cover_missing_restriction",
                        {"object": obj, "arrow": arr},
                    )
                    ok_for_s = False
                    break
                src = restr.get("from")
                if src != obj:
                    sheaf_ok = False
                    record_counterexample(
                        "sheaf_cover_restriction_wrong_source",
                        {"object": obj, "arrow": arr, "from": src},
                    )
                    ok_for_s = False
                    break
                map_arr = restr.get("map") or {}
                if s not in map_arr:
                    sheaf_ok = False
                    record_counterexample(
                        "sheaf_cover_missing_map_entry",
                        {"object": obj, "arrow": arr, "section": s},
                    )
                    ok_for_s = False
                    break
                local_sec = map_arr[s]
                local_assignments[arr] = local_sec
                local_tuple.append(local_sec)

            if not ok_for_s:
                continue

            family_key = tuple(local_tuple)
            existing = family_to_global.get(family_key)
            if existing is not None and existing != s:
                sheaf_ok = False
                record_counterexample(
                    "sheaf_gluing_not_unique",
                    {
                        "object": obj,
                        "family": list(family_key),
                        "existing_global": existing,
                        "new_global": s,
                    },
                )
            else:
                family_to_global[family_key] = s

            families_for_cover.append(
                {
                    "object": obj,
                    "arrows": list(cover_arrows),
                    "sections": local_assignments,
                    "glued_section": s,
                }
            )

        matching_families[key] = families_for_cover

        if globals_at_obj:
            chosen = sorted(globals_at_obj)[0]
            glued_sections[key] = chosen

    evidence = {
        "kind": "sheafification_evidence",
        "presheaf_id": presheaf["id"],
        "matching_families": matching_families,
        "glued_sections": glued_sections,
        "uniqueness_witnesses": {
            "functoriality_ok": functor_ok,
            "sheaf_gluing_ok": sheaf_ok,
        },
        "status": "pass" if functor_ok and sheaf_ok else "fail",
        "act_ref": "SheafificationEvidence",
    }
    if evidence["status"] == "fail" and counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "sheafification_evidence",
        "src": presheaf["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"sheafification_evidence": evidence["id"]},
    )
