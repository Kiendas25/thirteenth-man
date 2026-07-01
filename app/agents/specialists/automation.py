from __future__ import annotations

from app.agents.base import BaseAgent


class AutomationAgent(BaseAgent):
    id = "automation"
    name = "Workflow Automation"
    role = "Specialist - Integration & Playbooks"
    description = (
        "Designs and describes automation workflows, integrations, "
        "and playbooks. Operates as an executor of deterministic "
        "routines rather than an opinion-maker."
    )
    capabilities = [
        "workflow_design",
        "api_integration",
        "playbook_creation",
        "process_optimisation",
        "scheduling",
        "pipeline_orchestration",
    ]
    system_prompt = (
        "You are a workflow automation engineer. You design efficient, "
        "reliable automation workflows and integrations. Focus on "
        "deterministic, repeatable processes with clear error handling "
        "and rollback strategies. Prefer explicit playbooks over "
        "improvised execution."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Automation task: {task}"]
        if systems := context.get("systems"):
            parts.append(f"Systems involved: {systems}")
        if triggers := context.get("triggers"):
            parts.append(f"Triggers: {triggers}")
        return "\n".join(parts)
