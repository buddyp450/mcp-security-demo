from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Tuple, Protocol

from .models import RegistryEntry, RegistrySnapshot


class RegistryProtocol(Protocol):
    def reset_to_defaults(self) -> None: ...

    def snapshot(self) -> RegistrySnapshot: ...

    def update_status(self, server: str, version: str, status: str, notes: str | None = None) -> RegistryEntry: ...

    def ban(self, server: str, version: str, reason: str) -> RegistryEntry: ...

    def quarantine(self, server: str, version: str, reason: str) -> RegistryEntry: ...

    def allow(self, server: str, version: str, notes: str | None = None) -> RegistryEntry: ...

    def is_allowed(self, server: str, version: str) -> bool: ...

    def describe(self) -> Dict[str, str]: ...


class RegistryService(RegistryProtocol):
    def __init__(self) -> None:
        self._defaults = [
            # RegistryEntry(server="subscriptor", version="1.0.0", status="allowed"),
            # RegistryEntry(server="subscriptor", version="2.0.0", status="allowed"),
            # RegistryEntry(server="subscriptor", version="2.0.1", status="quarantined"),
            # RegistryEntry(server="subscriptor", version="2.1.0", status="banned"),
            # RegistryEntry(server="subscriptor", version="2.2.0", status="quarantined"),
            
            # allowing all presently because I am not demo'ing the quarantine and banned behavior yet
            RegistryEntry(server="subscriptor", version="1.0.0", status="allowed"),
            RegistryEntry(server="subscriptor", version="2.0.0", status="allowed"),
            RegistryEntry(server="subscriptor", version="2.0.1", status="allowed"),
            RegistryEntry(server="subscriptor", version="2.1.0", status="allowed"),
            RegistryEntry(server="subscriptor", version="2.2.0", status="allowed"),
        ]
        self._entries: Dict[Tuple[str, str], RegistryEntry] = {}
        self.reset_to_defaults()

    def reset_to_defaults(self) -> None:
        self._entries = {
            (entry.server, entry.version): entry.model_copy(deep=True)
            for entry in self._defaults
        }

    def snapshot(self) -> RegistrySnapshot:
        return RegistrySnapshot(
            entries=list(self._entries.values()),
            updated_at=datetime.utcnow(),
        )

    def default_entries(self) -> List[RegistryEntry]:
        return [entry.model_copy(deep=True) for entry in self._defaults]

    def spawn_session_registry(self) -> "SessionRegistry":
        return SessionRegistry(self.default_entries())

    def update_status(self, server: str, version: str, status: str, notes: str | None = None) -> RegistryEntry:
        entry = RegistryEntry(server=server, version=version, status=status, notes=notes)
        self._entries[(server, version)] = entry
        return entry

    def ban(self, server: str, version: str, reason: str) -> RegistryEntry:
        return self.update_status(server, version, "banned", notes=reason)

    def quarantine(self, server: str, version: str, reason: str) -> RegistryEntry:
        return self.update_status(server, version, "quarantined", notes=reason)

    def allow(self, server: str, version: str, notes: str | None = None) -> RegistryEntry:
        return self.update_status(server, version, "allowed", notes=notes)

    def is_allowed(self, server: str, version: str) -> bool:
        snapshot = self.snapshot()
        for entry in snapshot.entries:
            if entry.server == server and entry.version == version:
                return entry.status == "allowed"
        return False

    def describe(self) -> Dict[str, str]:
        return {f"{server}:{version}": entry.status for (server, version), entry in self._entries.items()}


class SessionRegistry(RegistryProtocol):
    def __init__(self, defaults: List[RegistryEntry]) -> None:
        self._defaults = [entry.model_copy(deep=True) for entry in defaults]
        self._entries: Dict[Tuple[str, str], RegistryEntry] = {}
        self.reset_to_defaults()

    def reset_to_defaults(self) -> None:
        self._entries = {
            (entry.server, entry.version): entry.model_copy(deep=True)
            for entry in self._defaults
        }

    def snapshot(self) -> RegistrySnapshot:
        return RegistrySnapshot(
            entries=list(self._entries.values()),
            updated_at=datetime.utcnow(),
        )

    def update_status(self, server: str, version: str, status: str, notes: str | None = None) -> RegistryEntry:
        entry = RegistryEntry(server=server, version=version, status=status, notes=notes)
        self._entries[(server, version)] = entry
        return entry

    def ban(self, server: str, version: str, reason: str) -> RegistryEntry:
        return self.update_status(server, version, "banned", notes=reason)

    def quarantine(self, server: str, version: str, reason: str) -> RegistryEntry:
        return self.update_status(server, version, "quarantined", notes=reason)

    def allow(self, server: str, version: str, notes: str | None = None) -> RegistryEntry:
        return self.update_status(server, version, "allowed", notes=notes)

    def is_allowed(self, server: str, version: str) -> bool:
        entry = self._entries.get((server, version))
        return entry.status == "allowed" if entry else False

    def describe(self) -> Dict[str, str]:
        return {f"{server}:{version}": entry.status for (server, version), entry in self._entries.items()}
