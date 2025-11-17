from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from ..models import EventLevel, EventRecord, TestOutcome, TestResult
from ..servers.base import ServerBase, ServerResponse


@dataclass
class TestContext:
    session_id: str
    test_case: str
    emit_event: Callable[[EventRecord], Awaitable[None]]
    stage_id: str | None = None
    scenario_id: str | None = None
    server_variant_id: str | None = None


class ClientBase:
    name: str
    version: str
    description: str

    async def run(self, server: ServerBase, context: TestContext) -> TestResult:  # pragma: no cover - abstract
        raise NotImplementedError

    async def _log(
        self,
        context: TestContext,
        level: EventLevel,
        phase: str,
        message: str,
        metadata: dict | None = None,
    ) -> None:
        await context.emit_event(
            EventRecord(
                session_id=context.session_id,
                test_case=context.test_case,
                stage_id=context.stage_id,
                scenario_id=context.scenario_id,
                server_variant_id=context.server_variant_id,
                timestamp=contextual_now(),
                level=level,
                phase=phase,
                message=message,
                metadata=metadata or {},
            )
        )


def extract_breach_indicators(response: ServerResponse) -> Dict[str, Any]:
    indicators: Dict[str, Any] = {}
    covert_data = response.payload.get("covert_data")
    if covert_data:
        preview = str(covert_data)
        indicators["covert_data_preview"] = preview if len(preview) <= 160 else f"{preview[:160]}…"
    server_notes = response.payload.get("server_notes")
    if server_notes:
        indicators["server_notes"] = server_notes
    if response.covert_fields:
        indicators["covert_fields"] = response.covert_fields
    suspicious_syscalls = [
        call for call in response.syscalls if call.get("name", "").lower() in {"open", "write", "connect", "sendto", "socket"}
    ]
    if suspicious_syscalls:
        indicators["syscalls"] = suspicious_syscalls
    if response.network_events:
        indicators["network_events"] = response.network_events
    if response.notes:
        indicators["variant_notes"] = response.notes
    return indicators


def summarize_indicators(indicators: Dict[str, Any]) -> str:
    tokens: list[str] = []
    if "covert_data_preview" in indicators:
        tokens.append("payload exfiltration")
    if "server_notes" in indicators:
        tokens.append("prompt chaining")
    if "covert_fields" in indicators:
        tokens.append("covert channel markers")
    if "network_events" in indicators:
        tokens.append("unauthorized egress")
    if "syscalls" in indicators:
        tokens.append("filesystem/network syscalls")
    return ", ".join(tokens) if tokens else "no indicators"


def contextual_now():
    from datetime import datetime

    return datetime.utcnow()
