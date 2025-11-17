from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from typing import Deque, Dict, Optional

from .models import EventRecord, TailMetadata, TailSnapshot


class TailBufferService:
    """In-memory append-only tails per session to avoid websocket race conditions."""

    def __init__(self, max_events: int = 400) -> None:
        self.max_events = max_events
        self._buffers: Dict[str, Deque[EventRecord]] = {}
        self._metadata: Dict[str, TailMetadata] = {}
        self._lock = asyncio.Lock()

    async def register_session(
        self,
        session_id: str,
        *,
        stage_id: str | None,
        scenario_id: str | None,
        client_id: str,
        server_variant_id: str,
    ) -> None:
        async with self._lock:
            self._metadata[session_id] = TailMetadata(
                session_id=session_id,
                stage_id=stage_id,
                scenario_id=scenario_id,
                client_id=client_id,
                server_variant_id=server_variant_id,
                created_at=datetime.utcnow(),
            )
            self._buffers.setdefault(session_id, deque(maxlen=self.max_events))

    async def append(self, event: EventRecord) -> None:
        async with self._lock:
            buffer = self._buffers.setdefault(event.session_id, deque(maxlen=self.max_events))
            buffer.append(event)

    async def read(self, session_id: str) -> Optional[TailSnapshot]:
        async with self._lock:
            metadata = self._metadata.get(session_id)
            buffer = list(self._buffers.get(session_id, ()))
        if not metadata:
            return None
        return TailSnapshot(metadata=metadata, events=buffer)

