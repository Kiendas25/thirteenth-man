"""Tracing and observability for the agent system."""

from __future__ import annotations

import logging
from typing import Any

from app.models import TaskResponse, TraceEntry

log = logging.getLogger(__name__)


def format_trace(response: TaskResponse) -> str:
    """Format the execution trace as a human-readable string."""
    lines = [
        f"Task: {response.task_id}",
        f"Status: {response.status.value}",
        f"Specialists: {', '.join(response.specialists_used)}",
        "",
        "Execution Trace:",
        "-" * 60,
    ]
    total_ms = 0
    for entry in response.trace:
        total_ms += entry.duration_ms
        lines.append(
            f"  [{entry.timestamp}] {entry.agent:20s} | "
            f"{entry.action:12s} | {entry.duration_ms:>6d}ms | {entry.detail}"
        )
    lines.append("-" * 60)
    lines.append(f"Total execution time: {total_ms}ms")

    if response.verification:
        v = response.verification
        lines.extend([
            "",
            f"13th Man Verdict: {'PASSED' if v.passed else 'FAILED'}",
            f"Risk Level: {v.risk_level.value}",
        ])
        if v.issues:
            lines.append("Issues:")
            for issue in v.issues:
                lines.append(f"  - {issue}")

    return "\n".join(lines)


def log_trace(response: TaskResponse) -> None:
    """Log the execution trace."""
    log.info("\n%s", format_trace(response))
