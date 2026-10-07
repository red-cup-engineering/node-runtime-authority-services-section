"""
Loader for serialized AOG seeds into the in-memory graph.

Reads objects/runbooks/systems from data/ using relationality.files, and constructs
an AOG via relationality.graph. Realizers are bound dynamically elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

from relationality.files import load_objects, load_runbooks, load_systems, SerializedObject, SerializedRunbook
from relationality.graph import AOG, NodeData
from relationality.system import System, SystemRegistry
from jsonschema import Draft202012Validator


def build_graph_from_data(data_root: Path | None = None) -> Tuple[AOG, Dict[str, SerializedRunbook], Dict[str, Dict]]:
    graph = AOG()
    objects = load_objects(data_root)
    runbooks = load_runbooks(data_root)
    systems = load_systems(data_root)

    runbook_map: Dict[str, SerializedRunbook] = {rb.id: rb for rb in runbooks}

    for obj in objects:
        graph.add_node(
            NodeData(
                id=obj.id,
                kind=obj.kind,
                acts=obj.acts,
                payload=obj.payload,
                metadata={},
            ),
            status="loaded",
        )

    for rb in runbooks:
        for step in rb.steps:
            graph.record_operator_template(
                input_kind=step["input_kind"],
                output_kind=step["output_kind"],
                operator=step["operator"],
                runbook_id=rb.id,
                realizer_id=step["realizer"],
            )

    system_defs = {sys["id"]: sys for sys in systems}
    return graph, runbook_map, system_defs


def build_system_registry(graph: AOG, runbook_map: Dict[str, SerializedRunbook], system_defs: Dict[str, Dict]) -> SystemRegistry:
    # Observation validator
    import json
    from importlib import resources

    obs_schema = json.loads(resources.files("relationality.schemas").joinpath("observation-carrier.schema.json").read_text())
    observation_validator = Draft202012Validator(obs_schema)

    system_registry = SystemRegistry(graph, runbooks=runbook_map, observation_validator=observation_validator)
    if system_defs:
        for sys_def in system_defs.values():
            system_registry.build_from_definition(sys_def)
    else:
        system_registry.build_default(
            runbook_id="canonical-system-interaction",
            trace_runbook_id="system-trace",
            system_id="default",
        )
    return system_registry
