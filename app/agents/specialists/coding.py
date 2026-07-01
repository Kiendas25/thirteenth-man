from __future__ import annotations

from app.agents.base import BaseAgent


class CodingAgent(BaseAgent):
    id = "coding"
    name = "Autonomous Coding"
    role = "Specialist - Technical Execution"
    description = (
        "Writes, reviews and debugs code. Operates in a sandboxed "
        "mindset: proposes changes but flags anything that would touch "
        "production or sensitive systems for human approval."
    )
    capabilities = [
        "code_generation",
        "code_review",
        "debugging",
        "refactoring",
        "architecture_design",
        "testing",
    ]
    system_prompt = (
        "You are an expert software engineer. You write clean, well-tested, "
        "production-ready code. When asked, you provide code solutions with "
        "clear explanations. You flag any action that could affect production "
        "systems, databases, or security-sensitive components. Always consider "
        "error handling, edge cases, and maintainability."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Task: {task}"]
        if lang := context.get("language"):
            parts.append(f"Preferred language: {lang}")
        if stack := context.get("stack"):
            parts.append(f"Tech stack: {stack}")
        return "\n".join(parts)
