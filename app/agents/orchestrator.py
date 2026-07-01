"""Jarvis — the orchestrator / planner / router.

Receives user tasks, decomposes them, decides which specialists to activate,
aggregates results, and coordinates the 13th Man verification.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

from app.agents.specialists import get_specialist, list_specialists
from app.agents.thirteenth_man import ThirteenthMan
from app.llm import chat_json
from app.models import (
    ApprovalRequest,
    RoutingDecision,
    Severity,
    SpecialistResult,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TraceEntry,
    VerificationResult,
)

log = logging.getLogger(__name__)

ROUTING_SYSTEM = """\
You are Jarvis, the orchestrator of a multi-agent cognitive operating system.

Your job is to analyse the user's request and decide:
1. Which specialist agents to activate (pick ONLY those truly needed).
2. A brief execution plan.
3. Whether the task involves sensitive actions requiring human approval.
4. The risk level (low / medium / high / critical).

Available specialists:
{specialists}

Respond with a JSON object:
{{
  "specialists": ["agent_id", ...],
  "plan": "brief plan description",
  "requires_approval": true/false,
  "risk_level": "low|medium|high|critical"
}}

Rules:
- Activate the MINIMUM number of specialists needed.
- If the task is simple, a single specialist may suffice.
- Flag as requires_approval if it involves: financial transactions, code deployment,
  data deletion, email sending, or any irreversible action.
- Prefer low risk unless there's genuine reason for higher.
"""

SYNTHESIS_SYSTEM = """\
You are Jarvis, synthesising results from specialist agents into a coherent,
actionable final answer for the user. Integrate all specialist outputs,
resolve any contradictions, and present a unified response.

If the 13th Man raised issues, address them explicitly.
Be clear, structured and concise.
"""


class Orchestrator:
    """Jarvis — the brain of the system."""

    def __init__(self) -> None:
        self.thirteenth_man = ThirteenthMan()

    async def route(self, task: TaskRequest) -> tuple[RoutingDecision, TraceEntry]:
        """Classify the task and decide which specialists to call."""
        specialists_info = "\n".join(
            f"- {s.id}: {s.name} — {s.description}"
            for s in list_specialists()
        )
        system = ROUTING_SYSTEM.format(specialists=specialists_info)
        user_msg = f"User request: {task.content}"
        if task.context:
            user_msg += f"\nAdditional context: {json.dumps(task.context)}"

        t0 = time.monotonic()
        data = await chat_json(system, user_msg)
        elapsed = int((time.monotonic() - t0) * 1000)

        # Normalise specialists list (local models may return dicts or strings)
        raw_specs = data.get("specialists", [])
        specs: list[str] = []
        if isinstance(raw_specs, list):
            for s in raw_specs:
                sid = s.get("id", s) if isinstance(s, dict) else str(s)
                if sid in {
                    "coding", "research", "writing", "security", "financial",
                    "ml", "creativity", "auditing", "automation", "knowledge",
                }:
                    specs.append(sid)
        if not specs:
            specs = ["research", "writing"]  # safe fallback

        raw_risk = data.get("risk_level", "low")
        if isinstance(raw_risk, str) and raw_risk.lower() in (
            "low", "medium", "high", "critical"
        ):
            risk = Severity(raw_risk.lower())
        else:
            risk = Severity.low

        decision = RoutingDecision(
            specialists=specs,
            plan=str(data.get("plan", "")),
            requires_approval=bool(data.get("requires_approval", False)),
            risk_level=risk,
        )
        trace = TraceEntry(
            agent="Jarvis",
            action="route",
            detail=f"Plan: {decision.plan} | Specialists: {decision.specialists}",
            duration_ms=elapsed,
        )
        log.info("Routing: %s -> %s", task.content[:60], decision.specialists)
        return decision, trace

    async def _run_specialists(
        self, task: str, specialists: list[str], context: dict
    ) -> tuple[list[SpecialistResult], list[TraceEntry]]:
        """Run selected specialists in parallel."""
        async def _run_one(agent_id: str):
            agent = get_specialist(agent_id)
            return await agent.execute(task, context)

        tasks = [_run_one(sid) for sid in specialists]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[SpecialistResult] = []
        traces: list[TraceEntry] = []
        for i, outcome in enumerate(outcomes):
            if isinstance(outcome, Exception):
                log.error("Specialist %s failed: %s", specialists[i], outcome)
                traces.append(TraceEntry(
                    agent=specialists[i],
                    action="error",
                    detail=str(outcome),
                ))
            else:
                result, trace = outcome
                results.append(result)
                traces.append(trace)
        return results, traces

    async def _synthesise(
        self,
        task: str,
        results: list[SpecialistResult],
        verification: VerificationResult | None,
    ) -> tuple[str, TraceEntry]:
        """Combine specialist outputs into a final answer."""
        parts = [f"Original task: {task}", "", "Specialist outputs:"]
        for r in results:
            parts.append(f"\n--- {r.agent_name} ---\n{r.content}")

        if verification and not verification.passed:
            parts.append("\n--- 13th Man Issues ---")
            for issue in verification.issues:
                parts.append(f"- {issue}")
            parts.append(f"Recommendations: {verification.recommendations}")

        user_msg = "\n".join(parts)

        t0 = time.monotonic()
        from app.llm import chat
        answer = await chat(SYNTHESIS_SYSTEM, user_msg)
        elapsed = int((time.monotonic() - t0) * 1000)

        trace = TraceEntry(
            agent="Jarvis",
            action="synthesise",
            detail=f"Final answer ({len(answer)} chars)",
            duration_ms=elapsed,
        )
        return answer, trace

    async def process(self, task: TaskRequest) -> TaskResponse:
        """Full pipeline: route -> specialists -> verify -> synthesise."""
        response = TaskResponse(status=TaskStatus.routing)

        # 1. Route
        decision, route_trace = await self.route(task)
        response.trace.append(route_trace)
        response.specialists_used = decision.specialists

        # 2. Run specialists
        response.status = TaskStatus.processing
        results, spec_traces = await self._run_specialists(
            task.content, decision.specialists, task.context
        )
        response.specialist_results = results
        response.trace.extend(spec_traces)

        # 3. Verify with 13th Man
        response.status = TaskStatus.verifying
        verification, ver_trace = await self.thirteenth_man.verify(
            task.content, results
        )
        response.verification = verification
        response.trace.append(ver_trace)

        # 4. Check if approval is needed
        if decision.requires_approval or decision.risk_level in (
            Severity.high, Severity.critical
        ):
            response.status = TaskStatus.awaiting_approval
            response.approval = ApprovalRequest(
                task_id=response.task_id,
                action_description=decision.plan,
                risk_level=decision.risk_level,
            )

        # 5. Synthesise final answer
        answer, synth_trace = await self._synthesise(
            task.content, results, verification
        )
        response.final_answer = answer
        response.trace.append(synth_trace)

        if response.status != TaskStatus.awaiting_approval:
            response.status = TaskStatus.completed

        return response
