from __future__ import annotations

from app.agents.base import BaseAgent


class KnowledgeAgent(BaseAgent):
    id = "knowledge"
    name = "Knowledge Management"
    role = "Infrastructure - Memory & Retrieval"
    description = (
        "Manages knowledge organisation, retrieval and synthesis. "
        "More of an infrastructure service than a deliberative actor: "
        "indexes, retrieves and connects information across sessions."
    )
    capabilities = [
        "knowledge_organisation",
        "information_retrieval",
        "summarisation",
        "tagging",
        "connection_mapping",
        "context_building",
    ]
    system_prompt = (
        "You are a knowledge management specialist. You organise information "
        "into structured, retrievable formats. You identify connections between "
        "pieces of knowledge, suggest tags and categories, create summaries, "
        "and help build contextual understanding from disparate sources."
    )

    def _build_user_prompt(self, task: str, context: dict) -> str:
        parts = [f"Knowledge task: {task}"]
        if sources := context.get("sources"):
            parts.append(f"Available sources: {sources}")
        if existing := context.get("existing_knowledge"):
            parts.append(f"Existing knowledge base:\n{existing}")
        return "\n".join(parts)
