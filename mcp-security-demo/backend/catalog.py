from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from .clients.base import ClientBase
from .clients.registry_guard import ClientRegistryGuard
from .clients.v1 import ClientV1
from .clients.v2 import ClientV2
from .clients.v3 import ClientV3
from .clients.v4 import ClientV4HostSentinel
from .registry import RegistryProtocol


@dataclass(frozen=True)
class ClientProfile:
    id: str
    label: str
    description: str
    source_path: str
    article_refs: List[str]
    builder: Callable[[RegistryProtocol], ClientBase]


CLIENT_CATALOG: Dict[str, ClientProfile] = {
    "client_v1": ClientProfile(
        id="client_v1",
        label="Client v1 — Naive",
        description="No registry, no validation. Useful baseline for breaches.",
        source_path="mcp-security-demo/backend/clients/v1.py",
        article_refs=["cyberark"],
        builder=lambda registry: ClientV1(),
    ),
    "client_v2": ClientProfile(
        id="client_v2",
        label="Client v2 — Manifest Aware",
        description="Reads manifests but cannot intervene (visibility theater).",
        source_path="mcp-security-demo/backend/clients/v2.py",
        article_refs=["factset", "cyberark"],
        builder=lambda registry: ClientV2(),
    ),
    "client_v25": ClientProfile(
        id="client_v25",
        label="Client v2.5 — Registry Guard",
        description="Forces registry approval and tracks manifest drift.",
        source_path="mcp-security-demo/backend/clients/registry_guard.py",
        article_refs=["factset"],
        builder=lambda registry: ClientRegistryGuard(registry),
    ),
    "client_v3": ClientProfile(
        id="client_v3",
        label="Client v3 — Runtime Defense",
        description="Registry + syscall/network/latency enforcement.",
        source_path="mcp-security-demo/backend/clients/v3.py",
        article_refs=["cyberark", "windows"],
        builder=lambda registry: ClientV3(registry),
    ),
    "client_v4": ClientProfile(
        id="client_v4",
        label="Client v4 — Host Sentinel",
        description="Platform-style sandbox with auto-remediation.",
        source_path="mcp-security-demo/backend/clients/v4.py",
        article_refs=["windows"],
        builder=lambda registry: ClientV4HostSentinel(registry),
    ),
}


def build_client(client_id: str, registry: RegistryProtocol) -> ClientBase:
    profile = CLIENT_CATALOG.get(client_id)
    if not profile:
        raise ValueError(f"Unknown client id: {client_id}")
    return profile.builder(registry)

