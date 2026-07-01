from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    pending = "pending"
    routing = "routing"
    processing = "processing"
    verifying = "verifying"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    failed = "failed"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


# ---------------------------------------------------------------------------
# Core domain models
# ---------------------------------------------------------------------------

class AgentInfo(BaseModel):
    id: str
    name: str
    role: str
    description: str
    capabilities: list[str] = Field(default_factory=list)


class TaskRequest(BaseModel):
    """Incoming user request."""
    content: str
    context: dict[str, Any] = Field(default_factory=dict)


class SpecialistResult(BaseModel):
    """Output produced by a specialist agent."""
    agent_id: str
    agent_name: str
    content: str
    confidence: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    """Output produced by the 13th Man."""
    passed: bool
    issues: list[str] = Field(default_factory=list)
    risk_level: Severity = Severity.low
    recommendations: list[str] = Field(default_factory=list)
    reasoning: str = ""


class ApprovalRequest(BaseModel):
    """Human-in-the-loop approval gate."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str
    action_description: str
    risk_level: Severity
    status: ApprovalStatus = ApprovalStatus.pending
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class TraceEntry(BaseModel):
    """Single entry in the execution trace."""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    agent: str
    action: str
    detail: str = ""
    duration_ms: int = 0


class TaskResponse(BaseModel):
    """Full response returned to the user."""
    task_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: TaskStatus = TaskStatus.pending
    final_answer: str = ""
    specialists_used: list[str] = Field(default_factory=list)
    specialist_results: list[SpecialistResult] = Field(default_factory=list)
    verification: VerificationResult | None = None
    approval: ApprovalRequest | None = None
    trace: list[TraceEntry] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class RoutingDecision(BaseModel):
    """Jarvis decides which specialists to activate."""
    specialists: list[str] = Field(default_factory=list)
    plan: str = ""
    requires_approval: bool = False
    risk_level: Severity = Severity.low


class MemoryEntry(BaseModel):
    """Persistent memory item."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    task_id: str
    summary: str
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
