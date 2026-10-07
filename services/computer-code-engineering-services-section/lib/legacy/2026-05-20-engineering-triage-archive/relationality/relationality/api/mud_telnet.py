"""Telnet surface for the MUD-flavored profile/flow system.

This service keeps the runbook semantics unchanged while providing a
traditional telnet prompt. Each command is represented by an Observation
carrier; the profile lattice, flow map, and nucleus map are the same
carriers defined in ``data/objects`` for the MUD system. Session state is
kept as fresh nodes in the AOG (phase space + trace) so that multiple
clients can explore without mutating the persisted carriers.
"""

from __future__ import annotations

import asyncio
import os
from typing import Dict, Tuple

from relationality.canonical import ensure_id_coherence
from relationality.engine import execute_runbook
from relationality.graph import RelationalGraph
from relationality.runtime import get_computer
from relationality.validation import LawValidationError

MUD_SYSTEM_ID = "88921addf4b12295a748db37d9dce690be0be5abaa73325745bfcc410eb049ae"
RUNBOOK_NAME = "profile_observe"


def _build_graph() -> Tuple[RelationalGraph, Dict[str, dict]]:
    computer = get_computer(require_runtime_viability=True)
    objects = computer.objects
    graph = RelationalGraph()
    for payload in objects.by_id.values():
        graph.add_node(dict(payload))
    return graph, objects.by_id


def _select_runbook(runbook_name: str) -> dict:
    computer = get_computer(require_runtime_viability=True)
    runbooks = computer.runbooks
    candidates = runbooks.by_name.get(runbook_name)
    if not candidates:
        raise KeyError(f"runbook {runbook_name} not found")
    # Prefer the lowest ID to keep selection deterministic even if multiple
    # variants exist.
    return candidates[sorted(candidates)[0]]


def _command_catalog(objects: Dict[str, dict], measurement_frame_id: str) -> Dict[str, str]:
    frame = objects[measurement_frame_id]
    carrier_map = frame.get("kernel_params", {}).get("carrier_to_element", {})
    catalog: Dict[str, str] = {}
    for carrier_id, element in carrier_map.items():
        carrier = objects.get(carrier_id)
        if carrier is None:
            continue
        payload = carrier.get("payload_shape") or {}
        command = payload.get("command")
        if isinstance(command, str):
            catalog[command] = carrier_id
    return catalog


def _fresh_phase_space(template: dict, current_element: str) -> dict:
    phase = dict(template)
    phase["current_state"] = current_element
    phase.pop("id", None)
    ensure_id_coherence(phase)
    return phase


def _session_state(objects: Dict[str, dict], system: dict) -> Tuple[str, str]:
    """Return (phase_space_id, trace_id) for a new session."""
    trace_id = system["trace_id"]
    base_phase = objects[system["phase_space_id"]]
    phase = _fresh_phase_space(base_phase, base_phase["current_state"])
    return phase["id"], trace_id


def _render_help(commands: Dict[str, str]) -> str:
    available = "\n".join(f" - {cmd}" for cmd in sorted(commands))
    return (
        "Welcome to the relational MUD shell!\n"
        "Available commands (mapped to observation carriers):\n"
        f"{available}\n"
        "Type 'help' to see this list again or 'quit' to disconnect.\n"
    )


def _describe_state(graph: RelationalGraph, phase_space_id: str) -> str:
    phase = graph.nodes.get(phase_space_id)
    if not phase:
        return "(state unavailable)"
    return (
        f"current state: {phase.get('current_state')}\n"
        f"flow tags: {', '.join(phase.get('flow_tags', [])) or 'none'}\n"
    )


async def _run_command(
    command: str,
    carrier_id: str,
    session_trace_id: str,
    graph: RelationalGraph,
    objects: Dict[str, dict],
    runbook: dict,
    system: dict,
) -> Tuple[str, str, str]:
    """Execute one command cycle and return (message, phase_id, trace_id)."""

    measurement_frame_id = system["measurement_frame_id"]
    phase_template = objects[system["phase_space_id"]]
    phase_element = objects[measurement_frame_id]["kernel_params"]["carrier_to_element"][carrier_id]
    phase_node = _fresh_phase_space(phase_template, phase_element)
    graph.add_node(phase_node)

    bindings = {
        "observation": carrier_id,
        "profile_topos": system["profile_topos_id"],
        "measurement_frame": measurement_frame_id,
        "phase_space": phase_node["id"],
        "flow_map": system["flow_map_id"],
        "nucleus_map": system["nucleus_map_id"],
        "trace": session_trace_id,
        "commutation_evidence": system.get("commutation_evidence_id")
        or next(iter({k: v for k, v in objects.items() if v.get("kind") == "commutation_evidence"})),
    }

    execute_runbook(graph, runbook, bindings)

    new_phase_id = bindings.get("phase_space", phase_node["id"])
    new_trace_id = bindings.get("trace", session_trace_id)
    state_text = _describe_state(graph, new_phase_id)
    message = (
        f"Command '{command}' recognized.\n"
        f"Observation carrier: {carrier_id}\n"
        f"{state_text}"
    )
    return message, new_phase_id, new_trace_id


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    graph, objects = _build_graph()
    runbook = _select_runbook(RUNBOOK_NAME)
    system = objects[MUD_SYSTEM_ID]
    commands = _command_catalog(objects, system["measurement_frame_id"])
    phase_id, trace_id = _session_state(objects, system)
    writer.write(_render_help(commands).encode())
    await writer.drain()

    while True:
        writer.write(b"> ")
        await writer.drain()
        data = await reader.readline()
        if not data:
            break
        command = data.decode().strip().lower()
        if command in {"quit", "exit"}:
            writer.write(b"Goodbye!\n")
            await writer.drain()
            break
        if command in {"help", "?"}:
            writer.write(_render_help(commands).encode())
            await writer.drain()
            continue
        carrier_id = commands.get(command)
        if carrier_id is None:
            writer.write(f"Unknown command '{command}'. Type 'help' for options.\n".encode())
            await writer.drain()
            continue
        try:
            message, phase_id, trace_id = await _run_command(
                command,
                carrier_id,
                trace_id,
                graph,
                objects,
                runbook,
                system,
            )
        except LawValidationError as exc:
            writer.write(f"Command rejected by laws: {exc}\n".encode())
            await writer.drain()
            continue
        except Exception as exc:  # noqa: BLE001
            writer.write(f"Command failed: {exc}\n".encode())
            await writer.drain()
            continue
        writer.write(message.encode())
        await writer.drain()

    writer.close()
    await writer.wait_closed()


def main() -> None:
    port = int(os.environ.get("MUD_TELNET_PORT", "2323"))
    loop = asyncio.get_event_loop()
    server_coro = asyncio.start_server(handle_client, host="0.0.0.0", port=port)
    server = loop.run_until_complete(server_coro)
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"MUD telnet server listening on {addresses}")
    try:
        loop.run_forever()
    finally:
        server.close()
        loop.run_until_complete(server.wait_closed())
        loop.close()


if __name__ == "__main__":
    main()
