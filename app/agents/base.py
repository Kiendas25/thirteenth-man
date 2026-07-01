"""Base class for all specialist agents."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod

from app.llm import chat
from app.models import AgentInfo, SpecialistResult, TraceEntry

log = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Every specialist agent inherits from this."""

    id: str
    name: str
    role: str
    description: str
    capabilities: list[str]
    system_prompt: str

    def info(self) -> AgentInfo:
        return AgentInfo(
            id=self.id,
            name=self.name,
            role=self.role,
            description=self.description,
            capabilities=self.capabilities,
        )

    @abstractmethod
    def _build_user_prompt(self, task: str, context: dict) -> str:
        """Build the user-facing prompt for the LLM call."""

    async def execute(
        self, task: str, context: dict | None = None
    ) -> tuple[SpecialistResult, TraceEntry]:
        """Run the agent on a task and return result + trace."""
        ctx = context or {}
        user_prompt = self._build_user_prompt(task, ctx)

        t0 = time.monotonic()
        content = await chat(self.system_prompt, user_prompt)
        elapsed = int((time.monotonic() - t0) * 1000)

        result = SpecialistResult(
            agent_id=self.id,
            agent_name=self.name,
            content=content,
            confidence=0.85,
        )
        trace = TraceEntry(
            agent=self.name,
            action="execute",
            detail=f"Processed task ({len(content)} chars)",
            duration_ms=elapsed,
        )
        log.info("%s completed in %dms", self.name, elapsed)
        return result, trace
