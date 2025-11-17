from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Set

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .catalog import CLIENT_CATALOG
from .codeintel import compute_code_diff
from .executor import run_all_tests, run_invocations, TestInvocation
from .models import (
    CodeDiffResponse,
    EventLevel,
    EventRecord,
    RemediationAction,
    RemediationRequest,
    RemediationResponse,
    ResetStateRequest,
    RunAllResponse,
    RunCaseRequest,
    TailSnapshot,
    TestResult,
)
from .registry import RegistryService
from .storage import Storage
from .servers.variants import SERVER_VARIANTS
from .tail_buffer import TailBufferService

app = FastAPI(title="MCP Security Demo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

storage = Storage()
registry = RegistryService()
tail_buffer = TailBufferService()
subscribers: Dict[str, Set[WebSocket]] = {}
subscribers_lock = asyncio.Lock()


async def emit_to_subscribers(event: EventRecord) -> None:
    async with subscribers_lock:
        session_peers = list(subscribers.get(event.session_id, set()))
    for ws in session_peers:
        try:
            await ws.send_json(event.model_dump(mode="json"))
        except Exception:
            continue


def record_results_factory(session_id: str):
    def _record(results: list[TestResult]) -> None:
        storage.append_results(session_id, results)

    return _record


async def dispatch_event(event: EventRecord) -> None:
    storage.append_event(event)
    await tail_buffer.append(event)
    await emit_to_subscribers(event)


async def execute_session(session_id: str) -> None:
    session_registry = registry.spawn_session_registry()
    await run_all_tests(
        session_id=session_id,
        emit_event=dispatch_event,
        registry=session_registry,
        record_results=record_results_factory(session_id),
    )


async def execute_session_for_cases(session_id: str, invocations: list[TestInvocation]) -> None:
    session_registry = registry.spawn_session_registry()
    await run_invocations(
        session_id=session_id,
        invocations=invocations,
        emit_event=dispatch_event,
        registry=session_registry,
        record_results=record_results_factory(session_id),
    )


@app.post("/api/run-all", response_model=RunAllResponse)
async def api_run_all() -> RunAllResponse:
    session_id = uuid.uuid4().hex
    asyncio.create_task(execute_session(session_id))
    ws_url = f"/ws/{session_id}"
    return RunAllResponse(session_id=session_id, ws_url=ws_url)


@app.post("/api/run-case", response_model=RunAllResponse)
async def api_run_case(request: RunCaseRequest) -> RunAllResponse:
    if request.client_id not in CLIENT_CATALOG:
        raise HTTPException(status_code=400, detail="Unknown client")
    if request.server_variant_id not in SERVER_VARIANTS:
        raise HTTPException(status_code=400, detail="Unknown server variant")
    session_id = uuid.uuid4().hex
    invocation = TestInvocation(
        client_id=request.client_id,
        server_variant_id=request.server_variant_id,
        stage_id=request.stage_id,
        scenario_id=request.scenario_id,
        scenario_label=request.scenario_label,
    )
    asyncio.create_task(execute_session_for_cases(session_id, [invocation]))
    await tail_buffer.register_session(
        session_id,
        stage_id=request.stage_id,
        scenario_id=request.scenario_id,
        client_id=request.client_id,
        server_variant_id=request.server_variant_id,
    )
    ws_url = f"/ws/{session_id}"
    return RunAllResponse(session_id=session_id, ws_url=ws_url)


@app.post("/api/reset-state")
async def api_reset_state(request: ResetStateRequest):
    registry.reset_to_defaults()
    metadata = {
        "stage_id": request.stage_id,
        "scenario_id": request.scenario_id,
        "client_id": request.client_id,
        "server_variant_id": request.server_variant_id,
        "reason": request.reason,
    }
    event = EventRecord(
        session_id="state-reset",
        test_case="state-reset",
        timestamp=datetime.utcnow(),
        level=EventLevel.INFO,
        phase="state_reset",
        message="Backend state reset to canonical defaults",
        metadata={k: v for k, v in metadata.items() if v},
    )
    await dispatch_event(event)
    return {"status": "reset"}


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    async with subscribers_lock:
        peers = subscribers.setdefault(session_id, set())
        peers.add(websocket)
    try:
        session_log = storage.get_session(session_id)
        if session_log:
            for event in session_log.events:
                await websocket.send_json(event.model_dump(mode="json"))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with subscribers_lock:
            subscribers.get(session_id, set()).discard(websocket)


@app.get("/api/logs/{session_id}")
async def api_logs(session_id: str):
    session = storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.model_dump(mode="json")


@app.post("/api/remediate", response_model=RemediationResponse)
async def api_remediate(request: RemediationRequest) -> RemediationResponse:
    server, version = request.server.split(":")
    if request.action == RemediationAction.BAN:
        registry.ban(server, version, request.reason)
    elif request.action == RemediationAction.QUARANTINE:
        registry.quarantine(server, version, request.reason)
    elif request.action == RemediationAction.ROLLBACK:
        registry.allow(server, "1.0.0", request.reason)
    else:
        registry.allow(server, version, request.reason)

    event = EventRecord(
        session_id="remediation",
        test_case="remediation",
        timestamp=datetime.utcnow(),
        level=EventLevel.INFO,
        phase="remediation",
        message=f"{request.action.value.upper()} {request.server}",
        metadata={"reason": request.reason},
    )
    await dispatch_event(event)
    return RemediationResponse(
        status="accepted",
        action=request.action,
        server=request.server,
        reason=request.reason,
        timestamp=event.timestamp,
    )


@app.get("/api/tail/{session_id}", response_model=TailSnapshot)
async def api_tail(session_id: str) -> TailSnapshot:
    snapshot = await tail_buffer.read(session_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="Tail not found")
    return snapshot


@app.get("/api/code-diff", response_model=CodeDiffResponse)
async def api_code_diff(file: str, baseline: str, variant: str) -> CodeDiffResponse:
    try:
        return compute_code_diff(file, baseline, variant)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
