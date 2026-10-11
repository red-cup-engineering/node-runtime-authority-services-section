from __future__ import annotations

from typing import Dict, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def _compute_checks(profile_topos: Mapping[str, object]) -> tuple[Dict[str, bool], Dict[str, object] | None]:
    elements = set(profile_topos.get("elements", []))
    bottom = profile_topos.get("bottom")
    top = profile_topos.get("top")
    classifier = profile_topos.get("subobject_classifier") or {}
    truth = classifier.get("truth")
    falsehood = classifier.get("falsehood")
    finite_limits = profile_topos.get("finite_limits") or {}
    terminal = finite_limits.get("terminal")

    checks: Dict[str, bool] = {
        "classifier_truth_falsehood": bool(truth == top and falsehood == bottom),
        "classifier_elements": bool(truth in elements and falsehood in elements),
        "terminal_matches_top": bool(terminal == top and terminal in elements),
    }

    counterexample = None
    if not all(checks.values()):
        # Record the first failing check with enough detail to diagnose.
        if not checks["classifier_truth_falsehood"]:
            counterexample = {
                "check": "classifier_truth_falsehood",
                "truth": truth,
                "falsehood": falsehood,
                "expected_top": top,
                "expected_bottom": bottom,
            }
        elif not checks["classifier_elements"]:
            counterexample = {
                "check": "classifier_elements",
                "truth": truth,
                "falsehood": falsehood,
                "elements": sorted(elements),
            }
        elif not checks["terminal_matches_top"]:
            counterexample = {
                "check": "terminal_matches_top",
                "terminal": terminal,
                "top": top,
            }

    return checks, counterexample


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_semantics_check realizer.

    Input
    -----
    profile_topos:
        ProfileTopos carrier (kind ``profile_topos``) whose classifier and
        finite-limits structure are to be checked.

    Semantics
    ---------
    Diagnostic ProfileSemantics check:

    - classifier_truth_falsehood: subobject_classifier.truth/falsehood match
      top/bottom;
    - classifier_elements: classifier truth/falsehood are elements of the
      lattice;
    - terminal_matches_top: finite_limits.terminal equals the top element.

    Emits profile_semantics_evidence with per-check booleans and overall
    status, plus a counterexample on failure.
    """
    profile_topos = inputs.get("profile_topos")
    if profile_topos is None:
        raise KeyError("profile_semantics_check requires 'profile_topos' input")
    if profile_topos.get("kind") != "profile_topos":
        raise LawValidationError("profile_semantics_check input must have kind 'profile_topos'")

    checks, counterexample = _compute_checks(profile_topos)
    status = "pass" if all(checks.values()) else "fail"

    evidence = {
        "kind": "profile_semantics_evidence",
        "profile_topos_id": profile_topos["id"],
        "checks": checks,
        "status": status,
        "act_ref": "ProfileSemanticsCheck",
    }
    if counterexample is not None:
        evidence["counterexample"] = counterexample
    ensure_id_coherence(evidence)

    edge = {
        "operator": "profile_semantics_check",
        "src": profile_topos["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"profile_semantics_evidence": evidence["id"]},
    )

