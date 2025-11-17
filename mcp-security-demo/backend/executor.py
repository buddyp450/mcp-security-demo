from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable, List, Sequence

from .catalog import build_client
from .clients.base import TestContext
from .models import EventLevel, EventRecord, TestResult
from .registry import RegistryProtocol
from .servers.base import ServerBase
from .servers.variants import build_server

EventDispatcher = Callable[[EventRecord], Awaitable[None]]


@dataclass
class TestInvocation:
    client_id: str
    server_variant_id: str
    stage_id: str | None = None
    scenario_id: str | None = None
    scenario_label: str | None = None

    @property
    def test_case_id(self) -> str:
        if self.scenario_id:
            return self.scenario_id
        return f"{self.client_id}__{self.server_variant_id}"


DEFAULT_INVOCATIONS: Sequence[TestInvocation] = [
    TestInvocation(client_id="client_v1", server_variant_id="covert-slice"),
    TestInvocation(client_id="client_v2", server_variant_id="version-shift"),
    TestInvocation(client_id="client_v25", server_variant_id="covert-slice"),
    TestInvocation(client_id="client_v25", server_variant_id="version-shift"),
    TestInvocation(client_id="client_v3", server_variant_id="prompt-chainer"),
    TestInvocation(client_id="client_v4", server_variant_id="side-effect-cascade"),
]


def _build_matrix(invocations: Sequence[TestInvocation], registry: RegistryProtocol):
    matrix = []
    for invocation in invocations:
        client = build_client(invocation.client_id, registry)
        server = build_server(invocation.server_variant_id)
        matrix.append((invocation.test_case_id, client, server, invocation))
    return matrix


async def _execute_matrix(
    session_id: str,
    matrix: Sequence[tuple[str, object, ServerBase, TestInvocation]],
    emit_event: EventDispatcher,
    record_results: Callable[[List[TestResult]], None],
) -> List[TestResult]:
    async def run_case(test_case: str, client, server: ServerBase, invocation: TestInvocation) -> TestResult:
        context = TestContext(
            session_id=session_id,
            test_case=test_case,
            emit_event=emit_event,
            stage_id=invocation.stage_id,
            scenario_id=invocation.scenario_id,
            server_variant_id=invocation.server_variant_id,
        )
        await emit_event(
            EventRecord(
                session_id=session_id,
                test_case=test_case,
                stage_id=invocation.stage_id,
                scenario_id=invocation.scenario_id,
                server_variant_id=invocation.server_variant_id,
                timestamp=datetime.utcnow(),
                level=EventLevel.INFO,
                phase="case_start",
                message=f"Starting {test_case}",
                metadata={
                    "client": client.name,
                    "server": f"{server.name}:{server.version}",
                    "server_variant": invocation.server_variant_id,
                    "scenario_label": invocation.scenario_label,
                },
            )
        )
        result = await client.run(server, context)
        await emit_event(
            EventRecord(
                session_id=session_id,
                test_case=test_case,
                stage_id=invocation.stage_id,
                scenario_id=invocation.scenario_id,
                server_variant_id=invocation.server_variant_id,
                timestamp=datetime.utcnow(),
                level=EventLevel.INFO,
                phase="case_end",
                message=f"Completed {test_case}",
                metadata={"outcome": result.outcome},
            )
        )
        return result

    results = await asyncio.gather(*(run_case(*row) for row in matrix))
    record_results(list(results))
    return list(results)


async def run_all_tests(
    session_id: str,
    emit_event: EventDispatcher,
    registry: RegistryProtocol,
    record_results: Callable[[List[TestResult]], None],
) -> List[TestResult]:
    matrix = _build_matrix(DEFAULT_INVOCATIONS, registry)
    return await _execute_matrix(session_id, matrix, emit_event, record_results)


async def run_invocations(
    session_id: str,
    invocations: Sequence[TestInvocation],
    emit_event: EventDispatcher,
    registry: RegistryProtocol,
    record_results: Callable[[List[TestResult]], None],
) -> List[TestResult]:
    if not invocations:
        raise ValueError("At least one invocation must be provided")
    matrix = _build_matrix(invocations, registry)
    return await _execute_matrix(session_id, matrix, emit_event, record_results)
