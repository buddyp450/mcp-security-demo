from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ServerResponse:
    tool_call: str
    manifest: Dict[str, Any]
    payload: Dict[str, Any]
    latency_ms: float
    syscalls: List[Dict[str, Any]] = field(default_factory=list)
    network_events: List[Dict[str, Any]] = field(default_factory=list)
    covert_fields: Dict[str, Any] = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


class ServerBase:
    name: str
    version: str

    async def run(self, tool_call: str) -> ServerResponse:  # pragma: no cover - abstract
        raise NotImplementedError

    def manifest(self) -> Dict[str, Any]:
        raise NotImplementedError
