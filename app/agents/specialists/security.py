from __future__ import annotations

from app.agents.base import BaseAgent


class SecurityAgent(BaseAgent):
    id = "security"
    name = "Security & Compliance"
    role = "Gatekeeper"
    description = (
        "Evaluates security implications, compliance requirements, "
        "and risk posture. Has veto/escalation power over actions "
        "that could compromise security or violate regulations."
    )
    capabilities = [
        "security_review",
        "compliance_check",
        "risk_assessment",
        "vulnerability_analysis",
        "gdpr_evaluation",
        "threat_modelling",
    ]
    system_prompt = (
        "You are a senior security and compliance specialist. You evaluate "
        "actions, code, and proposals for security risks, regulatory compliance "
        "(GDPR, AI Act, MiFID II where applicable), and operational safety. "
        "You have the authority to flag, escalate, or recommend blocking any "
        "action that poses unacceptable risk. Be specific about risks and "
        "recommend concrete mitigations."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Security evaluation request: {task}"]
        if domain := context.get("domain"):
            parts.append(f"Domain: {domain}")
        if regulations := context.get("regulations"):
            parts.append(f"Applicable regulations: {regulations}")
        return "\n".join(parts)
