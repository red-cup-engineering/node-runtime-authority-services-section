"""
FastAPI surface exposing the single interaction endpoint described in the README.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from jsonschema import ValidationError

from .models import InteractionRequest, InteractionResponse
from .persistence import PERSISTENT_ROOT, load_schema, _build_validator
from .runtime import boot


def create_app(base_path: Path | None = None) -> FastAPI:
    graph, engine, systems = boot(base_path)
    base = base_path or PERSISTENT_ROOT
    req_validator = _build_validator(load_schema(base, "schemas/interaction-request.schema.json"))
    resp_validator = _build_validator(load_schema(base, "schemas/interaction-response.schema.json"))

    app = FastAPI(
        title="Relational Computer",
        description="Aperiodic Operator Graph runtime derived from the acts.",
    )

    @app.post("/system/{system_id}/interact", response_model=InteractionResponse)
    async def interact(system_id: str, payload: InteractionRequest) -> InteractionResponse:
        try:
            system = systems.get(system_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="System not found")
        try:
            req_validator.validate(payload.model_dump())
            result = system.interact(
                engine=engine,
                observation=payload.observation,
                intent=payload.intent,
                constraints=payload.constraints,
            )
            resp_validator.validate(result)
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid observation: {exc.message}")
        return InteractionResponse.model_validate(result)

    return app


app = create_app()
