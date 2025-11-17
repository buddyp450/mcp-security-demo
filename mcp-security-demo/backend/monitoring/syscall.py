from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class SyscallAlert:
    syscall: str
    detail: Dict[str, str]
    rule: str


class SyscallMonitor:
    def __init__(self) -> None:
        self.blocklist = {"connect", "sendto", "socket_write"}

    def inspect(self, syscalls: List[Dict[str, str]]) -> Tuple[List[SyscallAlert], List[Dict[str, str]]]:
        alerts: List[SyscallAlert] = []
        for call in syscalls:
            name = call.get("name")
            if not name:
                continue
            normalized = name.lower()
            if normalized in {"connect", "sendto", "socket"}:
                alerts.append(
                    SyscallAlert(
                        syscall=normalized,
                        detail={k: str(v) for k, v in call.items()},
                        rule="no-network-without-declaration",
                    )
                )
        return alerts, syscalls
