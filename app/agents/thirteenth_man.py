"""The 13th Man — adversarial verifier.

Operates with different rules from the rest of the team:
- Searches for flaws, counter-examples, and inconsistencies
- Verifies sources and assumptions
- Checks for operational risks (prompt injection, data exfiltration, etc.)
- Only "lets pass" a decision when it cannot refute it with evidence

This is NOT just "another opinion" — it's a formal falsification mechanism.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.llm import chat_json
from app.models import Severity, SpecialistResult, TraceEntry, VerificationResult

log = logging.getLogger(__name__)

VERIFICATION_SYSTEM = """\
You are the 13th Man — an adversarial verifier in a multi-agent system.

Your SOLE PURPOSE is to find flaws, challenge conclusions, and verify quality.
You are NOT here to agree. You are here to FALSIFY.

Your verification protocol:
1. CHECK LOGICAL CONSISTENCY — are there contradictions between specialist outputs?
2. CHALLENGE ASSUMPTIONS — what unstated assumptions could be wrong?
3. FIND COUNTER-EXAMPLES — what scenarios would break the proposed solution?
4. VERIFY SOURCES — are claims supported by evidence or just asserted?
5. ASSESS OPERATIONAL RISKS — could this action cause unintended harm?
   - Prompt injection risks
   - Data exfiltration possibilities
   - Excessive autonomy / scope creep
   - Security vulnerabilities
6. CHECK COMPLETENESS — what important aspects were missed?

Respond with a JSON object:
{{
  "passed": true/false,
  "issues": ["list of specific issues found"],
  "risk_level": "low|medium|high|critical",
  "recommendations": ["specific actionable recommendations"],
  "reasoning": "detailed reasoning for your verdict"
}}

Rules:
- You MUST cite specific evidence for each issue.
- Vague objections ("could be better") are NOT acceptable.
- If you find NO concrete issues, set passed=true.
- A single critical issue should set passed=false.
- Be thorough but fair — don't block good work over trivial concerns.
"""


def _to_str_list(items: Any) -> list[str]:
    """Normalise a list that may contain dicts/objects into plain strings."""
    if not isinstance(items, list):
        return [str(items)] if items else []
    result: list[str] = []
    for item in items:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict):
            # Local models sometimes return {"type": ..., "description": ...}
            parts = [str(v) for v in item.values() if v]
            result.append(" — ".join(parts))
        else:
            result.append(str(item))
    return result


def _safe_severity(val: Any) -> Severity:
    """Parse a severity value, handling unexpected formats."""
    if isinstance(val, str) and val.lower() in ("low", "medium", "high", "critical"):
        return Severity(val.lower())
    return Severity.low


class ThirteenthMan:
    """Adversarial verification agent."""

    async def verify(
        self,
        original_task: str,
        specialist_results: list[SpecialistResult],
    ) -> tuple[VerificationResult, TraceEntry]:
        """Review specialist outputs and challenge their conclusions."""
        parts = [f"Original task: {original_task}", "", "Specialist outputs:"]
        for r in specialist_results:
            parts.append(
                f"\n--- {r.agent_name} (confidence: {r.confidence}) ---\n"
                f"{r.content}"
            )

        user_msg = "\n".join(parts)

        t0 = time.monotonic()
        data = await chat_json(VERIFICATION_SYSTEM, user_msg, temperature=0.3)
        elapsed = int((time.monotonic() - t0) * 1000)

        result = VerificationResult(
            passed=bool(data.get("passed", True)),
            issues=_to_str_list(data.get("issues", [])),
            risk_level=_safe_severity(data.get("risk_level", "low")),
            recommendations=_to_str_list(data.get("recommendations", [])),
            reasoning=str(data.get("reasoning", "")),
        )

        trace = TraceEntry(
            agent="13th Man",
            action="verify",
            detail=(
                f"Verdict: {'PASSED' if result.passed else 'FAILED'} | "
                f"Issues: {len(result.issues)} | Risk: {result.risk_level}"
            ),
            duration_ms=elapsed,
        )

        status = "PASSED" if result.passed else f"FAILED ({len(result.issues)} issues)"
        log.info("13th Man verdict: %s", status)
        return result, trace
