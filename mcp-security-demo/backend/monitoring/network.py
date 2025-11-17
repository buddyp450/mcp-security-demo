from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class NetworkAlert:
    event: Dict[str, str]
    rule: str


class NetworkInterceptor:
    def __init__(self, allowed_hosts: List[str] | None = None) -> None:
        self.allowed_hosts = allowed_hosts or ["factset.local", "analytics.internal"]

    def inspect(self, events: List[Dict[str, str]]) -> Tuple[List[NetworkAlert], List[Dict[str, str]]]:
        alerts: List[NetworkAlert] = []
        for event in events:
            host = str(event.get("host", ""))
            if host and host not in self.allowed_hosts:
                alerts.append(
                    NetworkAlert(
                        event={k: str(v) for k, v in event.items()},
                        rule="no-external-network",
                    )
                )
        return alerts, events
