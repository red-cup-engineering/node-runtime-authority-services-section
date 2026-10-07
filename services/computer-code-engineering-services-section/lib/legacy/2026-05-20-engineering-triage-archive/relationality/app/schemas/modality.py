"""Modality-related schemas.

These datatypes implement the state described in the modal logic and
modality tower specifications: predicates over states and modal
evaluations (box/diamond) across a state graph.
"""

from __future__ import annotations

from typing import Dict, List

from pydantic import BaseModel, Field


class StateGraph(BaseModel):
    """Finite or symbolic state graph G = (V, E)."""

    nodes: List[str] = Field(
        default_factory=list,
        description="State identifiers (stabilized recognitions)",
    )
    edges: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Adjacency lists: node -> list of successors",
    )


class PredicateVector(BaseModel):
    """Boolean predicate assignment over a state graph."""

    values: Dict[str, bool] = Field(
        default_factory=dict,
        description="Predicate value per state id",
    )


class ModalEvaluation(BaseModel):
    """Evaluation of box/diamond modalities over a predicate."""

    graph: StateGraph
    base: PredicateVector
    box: PredicateVector = Field(
        default_factory=PredicateVector,
        description="□P for each state",
    )
    diamond: PredicateVector = Field(
        default_factory=PredicateVector,
        description="◇P for each state",
    )

