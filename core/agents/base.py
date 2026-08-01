"""
Base Agent template for VRAV AI.
Extend this class to create specialized agents (legal, coding, research, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from core.models.schemas import Message, OrchestratorResponse, ToolCall
from core.orchestrator import AgentOrchestrator


class BaseAgent(ABC):
    name: str = "base"
    description: str = "Generic agent"
    system_prompt: str = "You are a helpful sovereign AI agent."
    preferred_model: Optional[str] = None
    tools: List[str] = []

    def __init__(self, orchestrator: Optional[AgentOrchestrator] = None):
        self.orchestrator = orchestrator or AgentOrchestrator()

    @abstractmethod
    async def preprocess(self, user_input: str) -> str:
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
        return response
