import json
from pathlib import Path
from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from app.rewriter.act_bindings import ACT_BINDINGS
from app.rewriter.handlers import HandlerRegistry

ROOT = Path(__file__).resolve().parents[1]


def _compute_known_acts() -> set[str]:
    """Derive known acts from bindings and handlers for MCP tools."""
    registry = HandlerRegistry.get_instance()
    handled = set(registry.list_handled_acts())
    bound = set(ACT_BINDINGS.keys())
    return handled | bound


KNOWN_ACTS = _compute_known_acts()

mcp = FastMCP(
    "Relational Knowledge Service",
    instructions="""You are connected to a universal relational computer.

RUNBOOKS (executable workflows):
- Use 'list_runbooks' to see available runbooks
- Use 'validate_runbook' to check if a runbook is valid before saving
- Use 'execute_runbook' to run a runbook and see results

Each recognition and runbook step traces back to earned mathematical acts."""
)


@mcp.tool()
def list_acts() -> list[str]:
    """List all available act slugs.
    
    Returns:
        Sorted list of act slugs that can be used in runbooks
    """
    return sorted(KNOWN_ACTS)


def _run_async(coro):
    """Run an async coroutine from sync context safely."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()
    except RuntimeError:
        return asyncio.run(coro)


@mcp.tool()
def list_runbooks(
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """List runbooks from the datastore.
    
    Args:
        status: Optional filter by status (draft, validated, completed, etc.)
        limit: Maximum number of results
    
    Returns:
        List of runbooks with their metadata
    """
    try:
        from app.storage.database import init_db
        from app.storage.repositories import RunbookRepository
        from app.schemas.runbook import RunbookStatus
        
        async def _list():
            db = await init_db()
            repo = RunbookRepository(db)
            status_enum = RunbookStatus(status) if status else None
            runbooks = await repo.list(status=status_enum, limit=limit)
            return [r.model_dump(mode="json") for r in runbooks]
        
        return _run_async(_list())
    except Exception as e:
        return [{"error": str(e)}]


@mcp.tool()
def validate_runbook(yaml_content: str) -> dict[str, Any]:
    """Validate a runbook YAML without saving it.
    
    Args:
        yaml_content: The YAML string containing the runbook definition
    
    Returns:
        Validation result with errors, warnings, and execution plan
    """
    try:
        from app.runbooks.parser import parse_runbook_yaml, RunbookParseError
        from app.runbooks.validator import RunbookValidator
        from app.runbooks.resolver import resolve_dependencies
        
        try:
            runbook = parse_runbook_yaml(yaml_content)
        except RunbookParseError as e:
            return {"valid": False, "parse_error": str(e)}
        
        validator = RunbookValidator()
        result = validator.validate(runbook)
        
        response = result.to_dict()
        
        if result.is_valid:
            try:
                plan = resolve_dependencies(runbook)
                response["execution_plan"] = plan.to_dict()
            except ValueError as e:
                response["is_valid"] = False
                response["errors"].append(str(e))
        
        return response
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def execute_runbook(runbook_id: str, inputs: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Execute a stored runbook.
    
    Args:
        runbook_id: The UUID of the runbook to execute
        inputs: Optional input parameters for the runbook
    
    Returns:
        Execution result with step results and status
    """
    try:
        from uuid import UUID
        from app.storage.database import init_db
        from app.storage.repositories import RunbookRepository, RecognitionRepository
        from app.rewriter.engine import RewriterEngine
        from app.schemas.runbook import RunbookCreate, RunbookStatus
        
        async def _execute():
            db = await init_db()
            repo = RunbookRepository(db)
            recognition_repo = RecognitionRepository(db)
            
            runbook = await repo.get(UUID(runbook_id))
            if not runbook:
                return {"error": "Runbook not found"}
            
            runbook_create = RunbookCreate(
                name=runbook.name,
                description=runbook.description,
                version=runbook.version,
                steps=runbook.steps,
                tags=runbook.tags,
                policy_requirements=runbook.policy_requirements,
            )
            
            engine = RewriterEngine(
                db=db,
                known_acts=KNOWN_ACTS,
                recognition_repo=recognition_repo,
                persist_recognitions=True,
            )
            result = await engine.execute(runbook_create, inputs or {})
            
            new_status = RunbookStatus.COMPLETED if result.is_success() else RunbookStatus.FAILED
            await repo.update_status(UUID(runbook_id), new_status, result.execution_id)
            
            return result.to_dict()
        
        return _run_async(_execute())
    except Exception as e:
        return {"error": str(e)}


def get_graph_stats() -> dict[str, Any]:
    """Compute simple knowledge-graph statistics from the live datastore.

    This is intentionally lightweight: it treats TracePoints as nodes and
    `tracepoint_edges` as edges, in line with the internal knowledge-graph
    theorems and specifications.
    """
    try:
        from app.storage.database import init_db

        async def _stats() -> dict[str, Any]:
            db = await init_db()
            tp_row = await db.fetch_one(
                "SELECT COUNT(*) AS c FROM tracepoints", ()
            )
            edge_row = await db.fetch_one(
                "SELECT COUNT(*) AS c FROM tracepoint_edges", ()
            )

            def _count(row: Any) -> int:
                if not row:
                    return 0
                # aiosqlite.Row behaves like a mapping
                return int(row["c"])

            return {
                "tracepoints": _count(tp_row),
                "edges": _count(edge_row),
            }

        return _run_async(_stats())
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


@mcp.resource("graph://stats")
def graph_stats_resource() -> str:
    """Get knowledge graph statistics as a resource.

    The statistics are derived from the live SQLite datastore, not from any
    precomputed JSON graph.
    """
    stats = get_graph_stats()
    return json.dumps(stats, indent=2)


@mcp.resource("graph://nodes")
def nodes_list_resource() -> str:
    """Get a summary list of graph nodes as a resource.

    Nodes are TracePoints in the live datastore; for now we expose a
    limited view (id, type, title) suitable for navigation.
    """
    try:
        from app.storage.database import init_db
        from app.storage.repositories import RecognitionRepository

        async def _nodes() -> list[dict[str, Any]]:
            db = await init_db()
            repo = RecognitionRepository(db)
            recognitions = await repo.list(limit=500, offset=0)
            return [
                {
                    "id": str(r.id),
                    "type": r.type.value,
                    "title": r.title,
                }
                for r in recognitions
            ]

        nodes_summary = _run_async(_nodes())
        return json.dumps(nodes_summary, indent=2)
    except Exception as e:  # pragma: no cover - defensive
        return json.dumps([{"error": str(e)}], indent=2)


@mcp.resource("graph://acts")
def acts_list_resource() -> str:
    """Get list of all act slugs as a resource."""
    return json.dumps(sorted(KNOWN_ACTS), indent=2)
