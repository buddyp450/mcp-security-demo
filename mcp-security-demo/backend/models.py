from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class EventLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


class EventRecord(BaseModel):
    session_id: str
    test_case: str
    timestamp: datetime
    level: EventLevel
    phase: str
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    stage_id: str | None = None
    scenario_id: str | None = None
    server_variant_id: str | None = None


class TestOutcome(str, Enum):
    PASSED = "passed"
    BLOCKED = "blocked"
    BREACHED = "breached"


class TestResult(BaseModel):
    test_case: str
    client: str
    server: str
    outcome: TestOutcome
    summary: str


class SessionLog(BaseModel):
    session_id: str
    created_at: datetime
    events: List[EventRecord]
    results: List[TestResult]


class RunAllResponse(BaseModel):
    session_id: str
    ws_url: str


class RunCaseRequest(BaseModel):
    stage_id: str
    scenario_id: str
    client_id: str
    server_variant_id: str
    scenario_label: str | None = None

class ResetStateRequest(BaseModel):
    stage_id: str
    scenario_id: str | None = None
    client_id: str | None = None
    server_variant_id: str | None = None
    reason: str | None = None


class RemediationAction(str, Enum):
    BAN = "ban"
    QUARANTINE = "quarantine"
    REPORT = "report"
    ROLLBACK = "rollback"
    AUDIT = "audit"


class RemediationRequest(BaseModel):
    action: RemediationAction
    server: str
    reason: str


class RemediationResponse(BaseModel):
    status: Literal["accepted", "rejected"]
    action: RemediationAction
    server: str
    reason: str
    timestamp: datetime


class RegistryEntry(BaseModel):
    server: str
    version: str
    status: Literal["allowed", "banned", "quarantined"] = "allowed"
    notes: Optional[str] = None


class RegistrySnapshot(BaseModel):
    entries: List[RegistryEntry]
    updated_at: datetime


class TailMetadata(BaseModel):
    session_id: str
    stage_id: str | None = None
    scenario_id: str | None = None
    client_id: str
    server_variant_id: str
    created_at: datetime


class TailSnapshot(BaseModel):
    metadata: TailMetadata
    events: List[EventRecord]


class CodeAnnotation(BaseModel):
    symbol: str
    summary: str
    start_line: int
    end_line: int


class CodeDiffResponse(BaseModel):
    file: str
    baseline: str
    variant: str
    diff: str
    annotations: List[CodeAnnotation]
