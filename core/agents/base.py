"""
Base Agent template for VRAV AI.
Extend this class to create specialized agents (legal, coding, research, etc).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from core.models.schemas import Message, OrchestratorResponse, ToolCall

if TYPE_CHECKING:
    from core.orchestrator import AgentOrchestrator


class BaseAgent(ABC):
    """
    Abstract base for domain-specific agents.

    Usage:
        class LegalAgent(BaseAgent):
            name = "legal_bg"
            system_prompt = "You are a Bulgarian legal assistant..."
            ...
    """

    name: str = "base"
    description: str = "Generic agent"
    system_prompt: str = "You are a helpful sovereign AI agent."
    preferred_model: Optional[str] = None  # e.g. "bggpt" or "ollama/llama3.1"
    tools: List[str] = []

    def __init__(self, orchestrator: Optional["AgentOrchestrator"] = None):
        if orchestrator is None:
            # Lazy import avoids circular dependency with core.orchestrator
            from core.orchestrator import AgentOrchestrator as _AO
            orchestrator = _AO()
        self.orchestrator = orchestrator

    @abstractmethod
    async def preprocess(self, user_input: str) -> str:
        """Optional rewriting / enrichment of the user prompt."""
        ...

    async def run(self, user_input: str, **kwargs) -> OrchestratorResponse:
        from core.models.schemas import StreamRequest

        processed = await self.preprocess(user_input)
        req = StreamRequest(
            prompt=processed,
            model=self.preferred_model,
            system_prompt=self.system_prompt,
            tools=self.tools,
            temperature=kwargs.get("temperature", 0.5),
        )
        return await self.orchestrator.execute(req)

    async def postprocess(self, response: OrchestratorResponse) -> OrchestratorResponse:
        """Optional final polishing."""
        return response
