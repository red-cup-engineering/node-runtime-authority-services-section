from __future__ import annotations

from typing import Dict, List, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError, validate_object


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    presheaf realizer.

    Inputs
    ------
    presheaf_site:
        Site carrier (kind ``presheaf_site``) describing contexts, arrows,
        identities, and composition.
    presheaf:
        Presheaf carrier (kind ``presheaf``) providing sections and
        restriction maps over the same site.

    Semantics
    ---------
    Realizes the Presheaf act by checking that the supplied carrier is a
    functor ``C^{op} -> Sets`` over the context site:

    - The presheaf is defined on exactly the site's objects/arrows.
    - Identity arrows act as identities on sections.
    - Composition satisfies ``res_{g∘f} = res_f ∘ res_g`` for every
      composable pair recorded in the site's composition table.

    When all laws hold, the realizer:
    - populates ``commutation_checks`` on the presheaf with booleans
      summarizing the functor laws; and
    - emits a canonicalized presheaf node.

    Any law violation is a hard error: the realizer raises
    LawValidationError and emits no nodes or edges.
    """
    site = inputs.get("presheaf_site")
    presheaf = inputs.get("presheaf")
    if site is None or presheaf is None:
        raise KeyError("presheaf realizer requires 'presheaf_site' and 'presheaf' inputs")
    if site.get("kind") != "presheaf_site":
        raise LawValidationError("presheaf realizer presheaf_site input must have kind 'presheaf_site'")
    if presheaf.get("kind") != "presheaf":
        raise LawValidationError("presheaf realizer presheaf input must have kind 'presheaf'")

    site_id = site.get("id")
    if not isinstance(site_id, str):
        raise LawValidationError("presheaf_site.id must be a string")
    if presheaf.get("site_id") != site_id:
        raise LawValidationError("presheaf.site_id must match presheaf_site.id")

    site_objects: List[str] = list(site.get("objects") or [])
    site_arrows: List[str] = list(site.get("arrows") or [])
    pf_objects: List[str] = list(presheaf.get("objects") or [])
    pf_arrows: List[str] = list(presheaf.get("arrows") or [])

    if set(site_objects) != set(pf_objects):
        raise LawValidationError("presheaf.objects must match presheaf_site.objects exactly")
    if set(site_arrows) != set(pf_arrows):
        raise LawValidationError("presheaf.arrows must match presheaf_site.arrows exactly")

    sections: Dict[str, List[str]] = {obj: list(secs) for obj, secs in (presheaf.get("sections") or {}).items()}
    restrictions: Dict[str, dict] = dict(presheaf.get("restrictions") or {})

    # Helper to check identity and composition laws and to populate the
    # commutation_checks summary.
    identity_ok = True
    composition_ok = True

    # Identity law: for each object U, the identity arrow id_U acts as
    # the identity on sections at U.
    identity_map: Mapping[str, str] = site.get("identity") or {}
    for obj in site_objects:
        id_arrow = identity_map.get(obj)
        if id_arrow is None:
            raise LawValidationError(f"presheaf_site.identity missing for object {obj!r}")
        if id_arrow not in pf_arrows:
            raise LawValidationError(
                f"presheaf identity arrow {id_arrow!r} for object {obj!r} not listed in presheaf.arrows"
            )
        restr = restrictions.get(id_arrow)
        if restr is None:
            raise LawValidationError(
                f"presheaf.restrictions missing entry for identity arrow {id_arrow!r} on object {obj!r}"
            )
        src = restr.get("from")
        tgt = restr.get("to")
        if src != obj or tgt != obj:
            identity_ok = False
            break
        sec_obj = sections.get(obj, [])
        mapping = restr.get("map") or {}
        for s in sec_obj:
            if mapping.get(s) != s:
                identity_ok = False
                break
        if not identity_ok:
            break

    if not identity_ok:
        raise LawValidationError("presheaf identity law failed: some identity arrow does not act as identity on sections")

    # Composition law: for each composable pair g ∘ f in the site's
    # composition table, restriction maps satisfy res_{g∘f} = res_f ∘ res_g.
    composition = site.get("composition") or {}
    for key, h in composition.items():
        parts = key.split("|")
        if len(parts) != 2:
            raise LawValidationError("presheaf_site.composition keys must encode pairs as 'g|f'")
        g, f = parts
        if f not in pf_arrows or g not in pf_arrows or h not in pf_arrows:
            raise LawValidationError(
                f"presheaf composition references unknown arrows g={g!r}, f={f!r}, h={h!r}"
            )
        restr_f = restrictions.get(f)
        restr_g = restrictions.get(g)
        restr_h = restrictions.get(h)
        if restr_f is None or restr_g is None or restr_h is None:
            raise LawValidationError(
                f"presheaf.restrictions missing entries for composition triple g={g!r}, f={f!r}, h={h!r}"
            )

        src_h = restr_h.get("from")
        src_g = restr_g.get("from")
        tgt_g = restr_g.get("to")
        src_f = restr_f.get("from")
        tgt_f = restr_f.get("to")
        tgt_h = restr_h.get("to")

        # We expect arrows f: U -> V, g: V -> W, h: U -> W, represented
        # by restriction maps F(W) -> F(V) -> F(U).
        if not (src_h == src_g and tgt_h == tgt_f and tgt_g == src_f):
            composition_ok = False
            break

        src_obj = src_h
        sec_src = sections.get(src_obj, [])
        map_f = restr_f.get("map") or {}
        map_g = restr_g.get("map") or {}
        map_h = restr_h.get("map") or {}
        for s in sec_src:
            if s not in map_g or s not in map_h:
                composition_ok = False
                break
            mid = map_g[s]
            if mid not in map_f:
                composition_ok = False
                break
            composed = map_f[mid]
            direct = map_h[s]
            if composed != direct:
                composition_ok = False
                break
        if not composition_ok:
            break

    if not composition_ok:
        raise LawValidationError(
            "presheaf composition law failed: some composition triple violates res_{g∘f} = res_f ∘ res_g"
        )

    # All functor laws hold; construct a canonical presheaf payload with a
    # commutation_checks summary.
    payload = dict(presheaf)
    payload["commutation_checks"] = {
        "identity": True,
        "composition": True,
    }
    ensure_id_coherence(payload)
    validate_object(payload)

    edge = {
        "operator": "presheaf",
        "src": site_id,
        "tgt": payload["id"],
    }

    return RealizerOutput(
        nodes=[payload],
        edges=[edge],
        bindings={"presheaf": payload["id"]},
    )

