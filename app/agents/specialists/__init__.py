"""Registry of all specialist agents."""

from __future__ import annotations

from app.agents.specialists.auditing import AuditingAgent
from app.agents.specialists.automation import AutomationAgent
from app.agents.specialists.coding import CodingAgent
from app.agents.specialists.creativity import CreativityAgent
from app.agents.specialists.financial import FinancialAgent
from app.agents.specialists.knowledge import KnowledgeAgent
from app.agents.specialists.ml import MLAgent
from app.agents.specialists.research import ResearchAgent
from app.agents.specialists.security import SecurityAgent
from app.agents.specialists.writing import WritingAgent

SPECIALIST_REGISTRY: dict[str, type] = {
    "coding": CodingAgent,
    "research": ResearchAgent,
    "writing": WritingAgent,
    "security": SecurityAgent,
    "financial": FinancialAgent,
    "ml": MLAgent,
    "creativity": CreativityAgent,
    "auditing": AuditingAgent,
    "automation": AutomationAgent,
    "knowledge": KnowledgeAgent,
}


def get_specialist(agent_id: str):
    """Instantiate a specialist by id."""
    cls = SPECIALIST_REGISTRY.get(agent_id)
    if cls is None:
        raise ValueError(f"Unknown specialist: {agent_id}")
    return cls()


def list_specialists():
    """Return info for every registered specialist."""
    return [cls().info() for cls in SPECIALIST_REGISTRY.values()]
