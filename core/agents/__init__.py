"""Domain agents — import submodules explicitly to avoid circular imports."""

from __future__ import annotations

__all__ = ["BaseAgent", "LegalBgAgent"]


def __getattr__(name: str):
    if name == "BaseAgent":
        from core.agents.base import BaseAgent
        return BaseAgent
    if name == "LegalBgAgent":
        from core.agents.legal_bg import LegalBgAgent
        return LegalBgAgent
    raise AttributeError(name)
