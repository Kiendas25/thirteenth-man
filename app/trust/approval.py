"""Human-in-the-loop approval system.

Manages approval requests for sensitive actions.
In a production system this would integrate with notifications,
email, Slack, etc. Here we use an in-memory store with API endpoints.
"""

from __future__ import annotations

import logging

from app.models import ApprovalRequest, ApprovalStatus

log = logging.getLogger(__name__)

_pending: dict[str, ApprovalRequest] = {}


def submit_approval(request: ApprovalRequest) -> None:
    """Queue an approval request."""
    _pending[request.id] = request
    log.info(
        "Approval requested: %s (risk: %s) — %s",
        request.id, request.risk_level.value, request.action_description,
    )


def list_pending() -> list[ApprovalRequest]:
    """Return all pending approvals."""
    return [r for r in _pending.values() if r.status == ApprovalStatus.pending]


def decide(approval_id: str, approved: bool) -> ApprovalRequest | None:
    """Approve or reject a pending request."""
    req = _pending.get(approval_id)
    if req is None:
        return None
    req.status = ApprovalStatus.approved if approved else ApprovalStatus.rejected
    log.info("Approval %s: %s", approval_id, req.status.value)
    return req
