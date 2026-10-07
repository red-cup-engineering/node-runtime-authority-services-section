from __future__ import annotations

from typing import Dict, List, Mapping

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LatticeOps, LawValidationError
import relationality.validation as _v


_REQUIRED_LAWS: List[str] = [
    "order",
    "meet_join",
    "implication",
    "negation",
    "bounds",
]


def _build_lattice(carrier: Mapping[str, object]) -> LatticeOps:
    """
    Extract a LatticeOps view from a lattice-bearing carrier.

    This mirrors the construction in validate_lattice but does not itself
    enforce any laws; individual law checks are applied separately.
    """
    try:
        if "elements" in carrier:
            elements_source = carrier["elements"]  # type: ignore[index]
        elif "states" in carrier:
            elements_source = carrier["states"]  # type: ignore[index]
        else:  # pragma: no cover - defensive
            raise LawValidationError("carrier must provide 'elements' or 'states' for lattice elements")
        elements = set(elements_source)
        order = carrier["order"]  # type: ignore[index]
        meet_table = carrier["meet_table"]  # type: ignore[index]
        join_table = carrier["join_table"]  # type: ignore[index]
        imply_table = carrier["imply_table"]  # type: ignore[index]
        negate_map = carrier["negate_map"]  # type: ignore[index]
        bottom = carrier["bottom"]  # type: ignore[index]
        top = carrier["top"]  # type: ignore[index]
    except KeyError as exc:  # pragma: no cover - defensive path
        raise LawValidationError(f"carrier missing lattice field {exc!r}") from exc
    return LatticeOps(
        elements=elements,
        order=order,
        meet_table=meet_table,
        join_table=join_table,
        imply_table=imply_table,
        negate_map=negate_map,
        bottom=bottom,
        top=top,
    )


def _check_bounds(lat: LatticeOps) -> None:
    if lat.bottom not in lat.elements or lat.top not in lat.elements:
        raise LawValidationError("bottom/top must be elements")


def _check_order(lat: LatticeOps) -> None:
    _v._validate_order(lat.elements, lat.order, lat.bottom, lat.top)


def _check_meet_join(lat: LatticeOps) -> None:
    _v._require_total_binary(lat.meet_table, lat.elements, "meet")
    _v._require_total_binary(lat.join_table, lat.elements, "join")
    _v._check_commutative(lat.meet_table, "meet")
    _v._check_commutative(lat.join_table, "join")
    _v._check_associative(lat.meet, lat.elements, "meet")
    _v._check_associative(lat.join, lat.elements, "join")
    _v._check_absorption(lat)
    _v._check_distributive(lat)


def _check_implication_and_negation(lat: LatticeOps) -> Dict[str, LawValidationError | None]:
    """
    Run the implication/negation laws, attributing failures to the
    appropriate law bucket based on the diagnostic message.
    """
    errors: Dict[str, LawValidationError | None] = {"implication": None, "negation": None}
    try:
        _v._check_implication(lat)
    except Exception as exc:  # pragma: no cover - defensive widening
        msg = str(exc)
        if "implication adjunction fails" in msg:
            errors["implication"] = exc  # type: ignore[assignment]
        elif "negation" in msg:
            errors["negation"] = exc  # type: ignore[assignment]
        else:
            errors["implication"] = exc  # type: ignore[assignment]
    return errors


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    judgment_laws_check realizer.

    Inputs
    ------
    carrier:
        Any lattice-bearing carrier (profile_topos, phase_space,
        fixed_invariants, etc.) providing elements, order, meet/join,
        implication, negation, bottom, and top.

    Semantics
    ---------
    Evaluate every finite judgment lattice law on the carrier:
    - bounds (bottom/top elements),
    - order axioms,
    - meet/join laws (including distributivity),
    - implication adjunction,
    - negation = x⇒⊥ and disjointness,
    and emit a judgment_laws_evidence node summarizing per-law status plus
    the first counterexample for any failing law.
    """
    carrier = inputs.get("carrier")
    if carrier is None:
        raise KeyError("judgment_laws_check requires 'carrier' input")
    required_keys = {
        "order",
        "meet_table",
        "join_table",
        "imply_table",
        "negate_map",
        "bottom",
        "top",
    }
    missing = sorted(required_keys - set(carrier.keys()))
    if missing:
        raise LawValidationError(
            f"judgment_laws_check carrier missing lattice keys: {missing}"
        )
    if "elements" not in carrier and "states" not in carrier:
        raise LawValidationError(
            "judgment_laws_check carrier must provide 'elements' or 'states'"
        )

    lat = _build_lattice(carrier)

    law_checks: List[Dict[str, object]] = []

    # Bounds.
    try:
        _check_bounds(lat)
        law_checks.append({"law": "bounds", "status": "pass"})
    except Exception as exc:  # pragma: no cover - defensive widening
        law_checks.append(
            {"law": "bounds", "status": "fail", "counterexample": {"reason": str(exc)}}
        )

    # Order axioms.
    try:
        _check_order(lat)
        law_checks.append({"law": "order", "status": "pass"})
    except Exception as exc:  # pragma: no cover - defensive widening
        law_checks.append(
            {"law": "order", "status": "fail", "counterexample": {"reason": str(exc)}}
        )

    # Meet/join + distributivity.
    try:
        _check_meet_join(lat)
        law_checks.append({"law": "meet_join", "status": "pass"})
    except Exception as exc:  # pragma: no cover - defensive widening
        law_checks.append(
            {
                "law": "meet_join",
                "status": "fail",
                "counterexample": {"reason": str(exc)},
            }
        )

    # Implication adjunction and negation laws.
    imp_neg_errors = _check_implication_and_negation(lat)
    for law in ("implication", "negation"):
        err = imp_neg_errors[law]
        if err is None:
            law_checks.append({"law": law, "status": "pass"})
        else:
            law_checks.append(
                {"law": law, "status": "fail", "counterexample": {"reason": str(err)}}
            )

    # Preserve deterministic law ordering.
    law_checks.sort(key=lambda entry: _REQUIRED_LAWS.index(entry["law"]))  # type: ignore[index]

    any_fail = any(entry["status"] == "fail" for entry in law_checks)  # type: ignore[index]
    status = "fail" if any_fail else "pass"

    evidence: Dict[str, object] = {
        "kind": "judgment_laws_evidence",
        "carrier_id": carrier["id"],
        "law_checks": law_checks,
        "status": status,
        "act_ref": "JudgmentLawsCheck",
    }
    ensure_id_coherence(evidence)

    edge = {
        "operator": "judgment_laws_check",
        "src": carrier["id"],
        "tgt": evidence["id"],
    }

    return RealizerOutput(
        nodes=[evidence],
        edges=[edge],
        bindings={"judgment_laws_evidence": evidence["id"]},
    )
