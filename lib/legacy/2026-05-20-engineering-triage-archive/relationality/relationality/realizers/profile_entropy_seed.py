from __future__ import annotations

from typing import Dict

from relationality.canonical import ensure_id_coherence
from relationality.realizer_output import RealizerOutput
from relationality.validation import LawValidationError


def realize(graph, inputs: Dict[str, dict], context: dict) -> RealizerOutput:
    """
    profile_entropy_seed realizer.

    Inputs
    ------
    profile_reach:
        ProfileReach carrier describing reachable recognitions under the
        profile flow.
    observation_kernel:
        ObservationKernel carrier acting on fixed invariants. For this profile
        seed, we treat it as providing the kernel dynamics that will be
        compared against reachability.

    Semantics
    ---------
    Acts: ProfileEntropySeed = (ProfileKernelStep ProfileReach).

    In this code model, ProfileEntropySeed is represented implicitly via the
    existing observation_kernel and profile_reach carriers. To keep the
    implementation faithful without introducing an extra ad-hoc carrier kind,
    this realizer:

    - verifies basic compatibility between profile_reach and observation_kernel
      (kernel defined on a basis whose IDs are fixed invariant elements, and
      profile_reach elements are a subset of those);
    - emits no new nodes, but returns bindings so that subsequent entropy
      measurement steps can treat this as a validated seed.

    This keeps all entropy magnitudes in the entropy_measurement/profile_entropy
    carriers, matching the README, while enforcing the ProfileEntropySeed
    domain law.
    """
    profile_reach = inputs.get("profile_reach")
    observation_kernel = inputs.get("observation_kernel")
    if profile_reach is None or observation_kernel is None:
        raise KeyError("profile_entropy_seed requires 'profile_reach' and 'observation_kernel' inputs")
    if profile_reach.get("kind") != "profile_reach":
        raise LawValidationError("profile_entropy_seed profile_reach input must have kind 'profile_reach'")
    if observation_kernel.get("kind") != "observation_kernel":
        raise LawValidationError("profile_entropy_seed observation_kernel input must have kind 'observation_kernel'")

    # Basic compatibility: profile_reach.reachable_elements must be contained
    # in the kernel's carrier basis (fixed_invariants elements).
    reachable = set(profile_reach.get("reachable_elements") or [])
    kernel_basis = set(observation_kernel.get("elements") or [])
    if not reachable:
        raise LawValidationError("profile_entropy_seed requires non-empty reachable_elements in profile_reach")
    if not reachable.issubset(kernel_basis):
        raise LawValidationError(
            "profile_entropy_seed requires profile_reach.reachable_elements to be a subset of observation_kernel.elements"
        )

    # No new carrier is materialized; the seed is the pair
    # (profile_reach, observation_kernel). We still record an inert edge so
    # that the AOG captures that the ProfileEntropySeed act has been checked.
    edge = {
        "operator": "profile_entropy_seed",
        "src": profile_reach["id"],
        "tgt": observation_kernel["id"],
    }

    return RealizerOutput(
        nodes=[],
        edges=[edge],
        bindings={
            "profile_reach": profile_reach["id"],
            "observation_kernel": observation_kernel["id"],
        },
    )

