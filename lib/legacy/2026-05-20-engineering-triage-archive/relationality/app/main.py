from __future__ import annotations

import os
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional, Set
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Query, Body, Depends, APIRouter
from fastapi.responses import PlainTextResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.mcp_server import mcp
from app.auth.routes import auth_router
from app.auth.middleware import AuthMiddleware
from app.policy.middleware import PolicyMiddleware
from app.policy.engine import get_policy_engine
from app.policy.defaults import load_default_policies
from app.measurement.fabric import MeasurementFabric, MeasurementFabricState
from app.schemas.measurement import ObservableSchema, ChannelConfig, MeasurementEvent
from app.rewriter.act_bindings import ACT_BINDINGS
from app.rewriter.handlers import HandlerRegistry


ROOT = Path(__file__).resolve().parents[1]
CONTENT_ROOT = ROOT / "docs" / "math" / "content"
CLIENT_DIST = ROOT / "client" / "dist"


def _compute_known_acts() -> Set[str]:
    """Derive the set of known acts from bindings and handlers."""
    registry = HandlerRegistry.get_instance()
    handled = set(registry.list_handled_acts())
    bound = set(ACT_BINDINGS.keys())
    return handled | bound


KNOWN_ACTS: Set[str] = _compute_known_acts()


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.storage.database import init_db
    from app.auth.database import get_auth_pool
    await init_db()
    await get_auth_pool()
    policy_engine = get_policy_engine()
    load_default_policies(policy_engine)
    app.state.measurement_fabric = MeasurementFabric(MeasurementFabricState())
    yield


app = FastAPI(
    title="Relational Knowledge Service",
    description="API for the universal relational computer. Exposes acts, theorems, specifications, recognitions, runbooks, and execution capabilities.",
    lifespan=lifespan,
)

session_secret = os.environ.get("SESSION_SECRET")
if not session_secret:
    import secrets
    session_secret = secrets.token_urlsafe(32)

app.add_middleware(SessionMiddleware, secret_key=session_secret)
app.add_middleware(AuthMiddleware)
app.add_middleware(PolicyMiddleware)

app.include_router(auth_router)

app.mount("/mcp", mcp.sse_app())

api_router = APIRouter(prefix="/api")


async def get_db():
    from app.storage.database import get_db as _get_db
    return _get_db()


def get_measurement_fabric(app: FastAPI) -> MeasurementFabric:
    fabric = getattr(app.state, "measurement_fabric", None)
    if fabric is None:
        fabric = MeasurementFabric(MeasurementFabricState())
        app.state.measurement_fabric = fabric
    return fabric


@api_router.get("/")
def api_root() -> dict[str, Any]:
    """API information and available endpoints."""
    return {
        "name": "Relational Knowledge Service",
        "description": "Universal relational computer API with MCP support",
        "endpoints": {
            "docs": "/docs - Interactive API documentation",
            "runbooks": "/api/runbooks - Runbook management",
            "runbooks_execute": "/api/runbooks/{id}/execute - Execute a runbook",
            "snapshots": "/api/snapshots - Snapshot management",
            "audit": "/api/audit - Audit log queries",
            "mcp": "/mcp/sse - MCP Server-Sent Events endpoint for AI clients"
        },
        "stats": {
            "total_acts": len(KNOWN_ACTS),
        }
    }


@api_router.get("/acts")
def list_acts() -> list[str]:
    """Return all act slugs for form dropdowns."""
    return sorted(KNOWN_ACTS)


@api_router.get("/acts/handlers")
def list_handled_acts() -> dict[str, Any]:
    """Return acts with registered handlers."""
    from app.rewriter.handlers import HandlerRegistry
    
    registry = HandlerRegistry.get_instance()
    handled = registry.list_handled_acts()
    
    return {
        "handled_acts": handled,
        "total_handled": len(handled),
        "total_acts": len(KNOWN_ACTS),
        "coverage_percent": round(len(handled) / len(KNOWN_ACTS) * 100, 2) if KNOWN_ACTS else 0,
    }


@api_router.get("/intake/schemas")
def list_intake_schemas() -> dict[str, Any]:
    """List all registered intake schemas."""
    from app.intake.registry import SchemaRegistry
    
    registry = SchemaRegistry.get_instance()
    schemas = registry.list_schemas()
    
    return {
        "schemas": schemas,
        "total": len(schemas),
    }


@api_router.post("/intake/validate")
async def validate_intake(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a recognition against the intake pipeline without persisting."""
    from app.intake.pipeline import IntakePipeline
    
    pipeline = IntakePipeline()
    
    result = await pipeline.process(data, KNOWN_ACTS)
    
    return {
        "success": result.success,
        "errors": result.errors,
        "warnings": result.warnings,
        "trace_id": result.trace_id,
        "validation": {
            "valid": result.validation_result.valid if result.validation_result else None,
            "schema_id": result.validation_result.schema_id if result.validation_result else None,
            "schema_version": result.validation_result.schema_version if result.validation_result else None,
            "errors": result.validation_result.errors if result.validation_result else [],
        } if result.validation_result else None,
        "policy": result.policy_result.to_dict() if result.policy_result else None,
        "normalization": {
            "transformations": result.normalization_result.transformations if result.normalization_result else [],
            "hash": result.normalization_result.hash if result.normalization_result else None,
        } if result.normalization_result else None,
    }


@api_router.post("/runbooks")
async def create_runbook(
    data: dict[str, Any] = Body(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Create a new runbook from YAML or JSON."""
    from app.schemas.runbook import validate_runbook
    from app.runbooks.parser import parse_runbook_yaml, RunbookParseError
    from app.runbooks.validator import RunbookValidator
    from app.storage.repositories import RunbookRepository
    
    if isinstance(data.get("yaml"), str):
        try:
            runbook_data = parse_runbook_yaml(data["yaml"])
        except RunbookParseError as e:
            raise HTTPException(status_code=400, detail=str(e))
    else:
        is_valid, errors = validate_runbook(data, KNOWN_ACTS)
        if not is_valid:
            raise HTTPException(status_code=400, detail={"errors": errors})
        from app.schemas.runbook import RunbookCreate
        runbook_data = RunbookCreate.model_validate(data)
    
    validator = RunbookValidator(GRAPH_PATH)
    result = validator.validate(runbook_data)
    
    if not result.is_valid:
        raise HTTPException(status_code=400, detail=result.to_dict())
    
    repo = RunbookRepository(db)
    runbook = await repo.create(runbook_data)
    
    response = runbook.model_dump(mode="json")
    response["validation"] = result.to_dict()
    
    return response


@api_router.get("/runbooks")
async def list_runbooks(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    """List runbooks with optional filters."""
    from app.schemas.runbook import RunbookStatus
    from app.storage.repositories import RunbookRepository
    
    repo = RunbookRepository(db)
    status_enum = RunbookStatus(status) if status else None
    runbooks = await repo.list(status=status_enum, limit=limit, offset=offset)
    
    return [r.model_dump(mode="json") for r in runbooks]


@api_router.get("/runbooks/{runbook_id}")
async def get_runbook(
    runbook_id: UUID,
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get a runbook by ID."""
    from app.storage.repositories import RunbookRepository
    
    repo = RunbookRepository(db)
    runbook = await repo.get(runbook_id)
    
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")
    
    return runbook.model_dump(mode="json")


@api_router.post("/runbooks/{runbook_id}/execute")
async def execute_runbook(
    runbook_id: UUID,
    inputs: dict[str, Any] = Body(default={}),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Execute a runbook."""
    from app.storage.repositories import RunbookRepository, RecognitionRepository, AuditRepository
    from app.rewriter.engine import RewriterEngine
    from app.schemas.runbook import RunbookStatus
    from app.schemas.policy import PolicyScope
    from app.policy.engine import get_policy_engine
    
    repo = RunbookRepository(db)
    recognition_repo = RecognitionRepository(db)
    runbook = await repo.get(runbook_id)
    
    if not runbook:
        raise HTTPException(status_code=404, detail="Runbook not found")

    # Enforce runbook-level policy requirements, if any.
    if runbook.policy_requirements:
        engine = get_policy_engine()
        target = {
            "runbook_id": str(runbook.id),
            "name": runbook.name,
            "tags": runbook.tags,
            "policy_requirements": runbook.policy_requirements,
        }
        decision = engine.evaluate(
            target=target,
            scope=PolicyScope.RUNBOOK,
            policy_ids=runbook.policy_requirements,
        )

        audit_repo = AuditRepository(db)
        try:
            await audit_repo.log(
                action="runbook_policy_check",
                entity_type="runbook",
                entity_id=str(runbook.id),
                actor=None,
                details={
                    "target": target,
                    "decision": decision.to_dict(),
                },
                trace_id=None,
                policy_decision=decision.effect.value,
            )
        except Exception:
            # Audit failures should not block policy enforcement.
            pass

        if not decision.allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Runbook execution denied by policy",
                    "decision": decision.to_dict(),
                },
            )

    from app.schemas.runbook import RunbookCreate
    runbook_create = RunbookCreate(
        name=runbook.name,
        description=runbook.description,
        version=runbook.version,
        steps=runbook.steps,
        tags=runbook.tags,
        policy_requirements=runbook.policy_requirements,
    )
    
    fabric = get_measurement_fabric(app=app)  # type: ignore[arg-type]
    engine = RewriterEngine(
        db=db,
        measurement_fabric=fabric,
        known_acts=KNOWN_ACTS,
        recognition_repo=recognition_repo,
        persist_recognitions=True,
    )
    result = await engine.execute(runbook_create, inputs)
    
    new_status = RunbookStatus.COMPLETED if result.is_success() else RunbookStatus.FAILED
    await repo.update_status(runbook_id, new_status, result.execution_id)
    
    return result.to_dict()


@api_router.post("/information/probe")
async def information_probe(
    params: dict[str, Any] = Body(default={}),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Probe the information state via a small tower + sheaf + Markov slice.

    This endpoint is part of the *information core*: it builds a minimal
    profile tower over a single fibre, embeds it into a sheaf section, applies
    a simple observation kernel and profile-kernel dynamics, and returns the
    resulting structures for inspection.
    """
    from app.rewriter.engine import RewriterEngine
    from app.storage.repositories import RecognitionRepository
    from app.schemas.runbook import RunbookCreate, RunbookStep, StepInput, StepOutput

    # Optional overrides for the probe; sensible defaults are provided.
    base_profile = params.get(
        "base_profile",
        {
            "id": "information-probe-base-profile",
            "description": "Base profile for information probe example",
        },
    )
    height = int(params.get("height", 3))

    # Define the probe runbook inline, mirroring runbooks/library/information-probe.yaml
    build_tower = RunbookStep(
        id="build_profile_tower",
        name="Build profile tower",
        description="Build a simple profile tower of height 3",
        acts=["build-profile-tower"],
        depends_on=[],
        inputs=[
            StepInput(
                name="base_profile",
                type="any",
                required=True,
                default=base_profile,
            ),
            StepInput(
                name="height",
                type="number",
                required=True,
                default=height,
            ),
        ],
        outputs=[
            StepOutput(name="tower", type="any"),
            StepOutput(name="tower_id", type="string"),
            StepOutput(name="sheaf_section", type="any"),
        ],
    )

    build_kernel = RunbookStep(
        id="build_kernel",
        name="Build observation kernel",
        description="Build a simple observation kernel over two states",
        acts=["observation-kernel"],
        depends_on=[],
        inputs=[
            StepInput(
                name="states",
                type="any",
                required=True,
                default=[{"id": "s0"}, {"id": "s1"}],
            ),
            StepInput(
                name="transition_law",
                type="any",
                required=True,
                default={
                    "s0": {"s0": 0.9, "s1": 0.1},
                    "s1": {"s0": 0.2, "s1": 0.8},
                },
            ),
        ],
        outputs=[
            StepOutput(name="kernel", type="any"),
            StepOutput(name="kernel_id", type="string"),
        ],
    )

    apply_step = RunbookStep(
        id="apply_profile_kernel_step",
        name="Apply profile kernel step",
        description="Attach the observation kernel to level 1 of the tower",
        acts=["profile-kernel-step"],
        depends_on=["build_profile_tower", "build_kernel"],
        inputs=[
            StepInput(
                name="tower",
                type="any",
                required=True,
                from_step="build_profile_tower.tower",
            ),
            StepInput(
                name="level",
                type="number",
                required=True,
                default=1,
            ),
            StepInput(
                name="kernel",
                type="any",
                required=True,
                from_step="build_kernel.kernel",
            ),
        ],
        outputs=[StepOutput(name="tower", type="any")],
    )

    build_chain = RunbookStep(
        id="build_profile_kernel_chain",
        name="Build profile kernel chain",
        description="Summarise kernel witnesses across tower levels",
        acts=["profile-kernel-chain"],
        depends_on=["apply_profile_kernel_step"],
        inputs=[
            StepInput(
                name="tower",
                type="any",
                required=True,
                from_step="apply_profile_kernel_step.tower",
            ),
            StepInput(
                name="kernel",
                type="any",
                required=True,
                from_step="build_kernel.kernel",
            ),
        ],
        outputs=[
            StepOutput(name="chain", type="any"),
            StepOutput(name="profile_kernel_chain", type="any"),
        ],
    )

    fixed_chain = RunbookStep(
        id="compute_fixed_chain",
        name="Compute fixed profile kernel chain",
        description="Mark the profile kernel chain as fixed/stationary",
        acts=["fixed-chain"],
        depends_on=["build_profile_kernel_chain"],
        inputs=[
            StepInput(
                name="chain",
                type="any",
                required=True,
                from_step="build_profile_kernel_chain.profile_kernel_chain",
            )
        ],
        outputs=[StepOutput(name="fixed_chain", type="any")],
    )

    probe_runbook = RunbookCreate(
        name="information-probe-inline",
        description="Information probe: tower + sheaf section + kernel dynamics",
        version="1.0.0",
        steps=[
            build_tower,
            build_kernel,
            apply_step,
            build_chain,
            fixed_chain,
        ],
        tags=["information-probe"],
        policy_requirements=[],
    )

    rec_repo = RecognitionRepository(db)
    fabric = get_measurement_fabric(app)  # type: ignore[arg-type]
    engine = RewriterEngine(
        db=db,
        measurement_fabric=fabric,
        known_acts=KNOWN_ACTS,
        recognition_repo=rec_repo,
        persist_recognitions=True,
    )

    result = await engine.execute(probe_runbook, inputs={}, trace_id=uuid4())

    # Summarise the core structures for callers; the full execution result is
    # also returned for inspection.
    tower_step = result.step_results.get("build_profile_tower")
    kernel_step = result.step_results.get("build_kernel")
    chain_step = result.step_results.get("build_profile_kernel_chain")
    fixed_step = result.step_results.get("compute_fixed_chain")

    tower = tower_step.outputs.get("tower") if tower_step else None
    sheaf_section = tower_step.outputs.get("sheaf_section") if tower_step else None
    kernel = kernel_step.outputs.get("kernel") if kernel_step else None
    chain = chain_step.outputs.get("profile_kernel_chain") if chain_step else None
    fixed_chain_out = fixed_step.outputs.get("fixed_chain") if fixed_step else None

    return {
        "tower": tower,
        "sheaf_section": sheaf_section,
        "kernel": kernel,
        "kernel_chain": chain,
        "fixed_chain": fixed_chain_out,
        "execution": result.to_dict(),
    }


@api_router.post("/runbooks/validate")
async def validate_runbook_endpoint(
    data: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    """Validate a runbook without saving it."""
    from app.runbooks.parser import parse_runbook_yaml, RunbookParseError
    from app.runbooks.validator import RunbookValidator
    from app.runbooks.resolver import resolve_dependencies
    
    if isinstance(data.get("yaml"), str):
        try:
            runbook_data = parse_runbook_yaml(data["yaml"])
        except RunbookParseError as e:
            return {"valid": False, "parse_error": str(e)}
    else:
        from app.schemas.runbook import RunbookCreate
        try:
            runbook_data = RunbookCreate.model_validate(data)
        except Exception as e:
            return {"valid": False, "parse_error": str(e)}
    
    validator = RunbookValidator(GRAPH_PATH)
    result = validator.validate(runbook_data)
    
    response = result.to_dict()
    
    if result.is_valid:
        try:
            plan = resolve_dependencies(runbook_data)
            response["execution_plan"] = plan.to_dict()
        except ValueError as e:
            response["is_valid"] = False
            response["errors"].append(str(e))
    
    return response


@api_router.delete("/runbooks/{runbook_id}")
async def delete_runbook(
    runbook_id: UUID,
    db=Depends(get_db),
) -> dict[str, str]:
    """Delete a runbook."""
    from app.storage.repositories import RunbookRepository
    
    repo = RunbookRepository(db)
    deleted = await repo.delete(runbook_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Runbook not found")
    
    return {"status": "deleted", "id": str(runbook_id)}


@api_router.post("/snapshots")
async def create_snapshot(
    data: dict[str, Any] = Body(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Create a new snapshot with baseline hash computation."""
    from app.snapshot.service import SnapshotService
    
    service = SnapshotService(db)
    
    result = await service.create_snapshot(
        name=data.get("name", f"Snapshot {datetime.now().isoformat()}"),
        description=data.get("description"),
        include_contexts=data.get("include_contexts", True),
        include_traces=data.get("include_traces", True),
        metadata=data.get("metadata"),
    )
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.error)
    
    return {
        "id": result.snapshot_id,
        "name": data.get("name", f"Snapshot {datetime.now().isoformat()}"),
        "baseline_hash": result.baseline_hash,
        "recognition_count": result.recognition_count,
        "context_count": result.context_count,
        "trace_count": result.trace_count,
        "created_at": result.created_at,
    }


@api_router.get("/snapshots")
async def list_snapshots(
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    """List snapshots."""
    from app.storage.repositories import SnapshotRepository
    
    repo = SnapshotRepository(db)
    snapshots = await repo.list(limit=limit, offset=offset)
    
    return snapshots


@api_router.get("/snapshots/{snapshot_id}")
async def get_snapshot(
    snapshot_id: UUID,
    db=Depends(get_db),
) -> dict[str, Any]:
    """Get a snapshot by ID."""
    from app.storage.repositories import SnapshotRepository
    
    repo = SnapshotRepository(db)
    snapshot = await repo.get(snapshot_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    return snapshot


@api_router.get("/snapshots/{snapshot_id}/tracepoints")
async def get_snapshot_tracepoints(
    snapshot_id: UUID,
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all TracePoints in a snapshot."""
    from app.storage.repositories import SnapshotRepository
    
    repo = SnapshotRepository(db)
    snapshot = await repo.get(snapshot_id)
    
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    
    recognitions = await repo.get_recognitions(snapshot_id)
    return [r.model_dump(mode="json") for r in recognitions]


@api_router.get("/snapshots/{snapshot_id}/verify")
async def verify_snapshot(
    snapshot_id: str,
    db=Depends(get_db),
) -> dict[str, Any]:
    """Verify the integrity of a snapshot by recomputing baseline hash."""
    from app.snapshot.service import SnapshotService
    
    service = SnapshotService(db)
    return await service.verify_snapshot(snapshot_id)


@api_router.get("/snapshots/{snapshot_id}/diff/{other_id}")
async def diff_snapshots(
    snapshot_id: str,
    other_id: str,
    db=Depends(get_db),
) -> dict[str, Any]:
    """Compare two snapshots and return differences."""
    from app.snapshot.service import SnapshotService
    
    service = SnapshotService(db)
    result = await service.diff_snapshots(snapshot_id, other_id)
    
    return {
        "added_count": result.added_count,
        "removed_count": result.removed_count,
        "modified_count": result.modified_count,
        "added_ids": result.added_ids,
        "removed_ids": result.removed_ids,
        "modified_ids": result.modified_ids,
        "diff_hash": result.diff_hash,
    }


@api_router.get("/audit")
async def query_audit_logs(
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db=Depends(get_db),
) -> list[dict[str, Any]]:
    """Query audit logs."""
    from app.storage.repositories import AuditRepository
    
    repo = AuditRepository(db)
    logs = await repo.query(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit,
        offset=offset,
    )
    
    return logs


@api_router.get("/policies")
async def list_policies() -> list[dict[str, Any]]:
    """List all registered policies."""
    engine = get_policy_engine()
    policies = engine.list_policies()
    return [p.model_dump(mode="json") for p in policies]


@api_router.get("/policies/{policy_id}")
async def get_policy(policy_id: str) -> dict[str, Any]:
    """Get a policy by ID."""
    engine = get_policy_engine()
    policy = engine.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy.model_dump(mode="json")


@api_router.post("/policies/check")
async def check_policy_endpoint(
    data: dict[str, Any] = Body(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    """Check a target against policies without enforcing."""
    from app.schemas.policy import PolicyScope
    from app.policy.middleware import check_policy
    from app.storage.repositories import AuditRepository
    
    target = data.get("target", {})
    scope_str = data.get("scope", "recognition")
    policy_ids = data.get("policy_ids")
    
    try:
        scope = PolicyScope(scope_str)
    except ValueError:
        scope = PolicyScope.RECOGNITION
    
    result = check_policy(target, policy_ids=policy_ids, scope=scope)

    # Record an audit log entry for this policy check so the policy
    # simulation and traceability specifications have a concrete
    # ledger of decisions.
    repo = AuditRepository(db)
    try:
        await repo.log(
            action="policy_check",
            entity_type="policy",
            entity_id=",".join(policy_ids) if policy_ids else None,
            actor=None,
            details={
                "target": target,
                "scope": scope.value,
                "policy_ids": policy_ids,
                "decision": result,
            },
            trace_id=target.get("trace_id") if isinstance(target, dict) else None,
            policy_decision=result.get("effect") if isinstance(result, dict) else None,
        )
    except Exception:
        # Audit failures should not break policy checks; they can be
        # surfaced via separate monitoring.
        pass

    return result


@api_router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


app.include_router(api_router)

SERVER_PATHS = {"/api", "/auth", "/docs", "/openapi.json", "/redoc", "/mcp"}

if CLIENT_DIST.exists():
    app.mount("/assets", StaticFiles(directory=CLIENT_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA for client-side routes only."""
        path = f"/{full_path}"
        for server_path in SERVER_PATHS:
            if path.startswith(server_path):
                raise HTTPException(status_code=404, detail="Not found")
        
        static_file = CLIENT_DIST / full_path
        if static_file.exists() and static_file.is_file():
            return FileResponse(static_file)
        
        index_path = CLIENT_DIST / "index.html"
        if index_path.exists():
            return FileResponse(index_path, media_type="text/html")
        return HTMLResponse("<h1>Frontend not built</h1><p>Run: cd client && npm run build</p>", status_code=500)
