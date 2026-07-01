from __future__ import annotations

from app.agents.base import BaseAgent


class CreativityAgent(BaseAgent):
    id = "creativity"
    name = "Creativity & Ideation"
    role = "Specialist - Creative Thinking"
    description = (
        "Generates creative solutions, alternatives, naming ideas, "
        "brainstorming, roadmaps. Useful for divergent thinking and "
        "exploring unconventional approaches."
    )
    capabilities = [
        "brainstorming",
        "naming",
        "roadmap_design",
        "alternative_generation",
        "creative_writing",
        "concept_development",
    ]
    system_prompt = (
        "You are a creative strategist and ideation specialist. You think "
        "laterally, generate diverse alternatives, challenge assumptions, "
        "and explore unconventional solutions. Provide multiple options "
        "ranked by feasibility and impact. Think big but stay grounded."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Creative challenge: {task}"]
        if constraints := context.get("constraints"):
            parts.append(f"Constraints: {constraints}")
        if domain := context.get("domain"):
            parts.append(f"Domain: {domain}")
        return "\n".join(parts)
