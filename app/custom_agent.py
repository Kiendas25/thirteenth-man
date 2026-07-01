"""Runtime for user-defined custom agents.

Custom agents are defined by the user via the API and stored in SQLite.
They use the same BaseAgent interface as built-in specialists.
"""

from __future__ import annotations

import logging

from app.agents.base import BaseAgent
from app.knowledge_base import get_custom_agents

log = logging.getLogger(__name__)


class CustomAgent(BaseAgent):
    """A dynamically-created specialist agent."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        role: str,
        description: str,
        capabilities: list[str],
        system_prompt: str,
    ) -> None:
        self.id = agent_id
        self.name = name
        self.role = role
        self.description = description
        self.capabilities = capabilities
        self.system_prompt = system_prompt

    def _build_user_prompt(self, task: str, context: dict) -> str:
        ctx_str = ""
        if context:
            ctx_str = f"\n\nAdditional context: {context}"
        return f"Task: {task}{ctx_str}"


async def load_custom_agents(username: str = "default") -> dict[str, CustomAgent]:
    """Load all custom agents for a user from the database."""
    rows = await get_custom_agents(username)
    agents = {}
    for r in rows:
        agent = CustomAgent(
            agent_id=r["id"],
            name=r["name"],
            role=r["role"],
            description=r["description"],
            capabilities=r.get("capabilities", []),
            system_prompt=r["system_prompt"],
        )
        agents[r["id"]] = agent
    return agents
