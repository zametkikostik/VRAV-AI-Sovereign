"""Example specialized agent: Bulgarian / EU Legal Assistant"""

from core.agents.base import BaseAgent
from core.models.schemas import OrchestratorResponse


class LegalBgAgent(BaseAgent):
    name = "legal_bg"
    description = "Specialized agent for Bulgarian and EU legal questions"
    preferred_model = "bggpt"
    system_prompt = (
        "Ти си специализиран правен асистент за България и ЕС. "
        "Отговаряй точно, цитирай нормативни актове когато е възможно, "
        "и винаги указвай нивото на сигурност. "
        "Ако не си сигурен — кажи го. Не измисляй членове на закони."
    )
    tools = []

    async def preprocess(self, user_input: str) -> str:
        return (
            f"[Контекст: българско/европейско право]\n"
            f"Въпрос на потребителя: {user_input}\n\n"
            f"Моля, отговори структурирано и посочи източници ако знаеш."
        )

    async def postprocess(self, response: OrchestratorResponse) -> OrchestratorResponse:
        if response.confidence < 0.7:
            response.response += (
                "\n\n⚖️ *Това не е правен съвет. Консултирайте се с адвокат.*"
            )
        return response
