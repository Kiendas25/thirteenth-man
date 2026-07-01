from __future__ import annotations

from app.agents.base import BaseAgent


class AuditingAgent(BaseAgent):
    id = "auditing"
    name = "AI Auditing"
    role = "Trust Layer - Evaluation"
    description = (
        "Evaluates AI outputs, trajectories and policies. Part of "
        "the trust layer that ensures quality and alignment of the "
        "system's behaviour with intended goals."
    )
    capabilities = [
        "output_evaluation",
        "trajectory_analysis",
        "policy_compliance",
        "bias_detection",
        "quality_assurance",
        "alignment_check",
    ]
    system_prompt = (
        "You are an AI auditor. You evaluate AI-generated outputs for quality, "
        "accuracy, bias, alignment with intended goals, and policy compliance. "
        "You analyse decision trajectories to identify problematic patterns. "
        "Be systematic, evidence-based, and specific in your assessments."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Audit request: {task}"]
        if outputs := context.get("outputs_to_audit"):
            parts.append(f"Outputs to evaluate:\n{outputs}")
        if policies := context.get("policies"):
            parts.append(f"Applicable policies: {policies}")
        return "\n".join(parts)
