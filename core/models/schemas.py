from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


class ModelProvider(str, Enum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"
    BGGPT = "bggpt"


class StreamRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=32000)
    model: Optional[str] = None
    provider: Optional[ModelProvider] = None
    tools: List[str] = Field(default_factory=list)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    stream: bool = False
    system_prompt: Optional[str] = None
    session_id: Optional[str] = None

    @field_validator("prompt")
    @classmethod
    def strip_prompt(cls, v: str) -> str:
        return v.strip()


class Message(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]
    call_id: Optional[str] = None


class FactCheckResult(BaseModel):
    verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    sources: List[str] = Field(default_factory=list)
    entities_checked: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class OrchestratorResponse(BaseModel):
    response: str
    model_used: str
    provider: str
    fact_check: Optional[FactCheckResult] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    reasoning: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class OpenAPITool(BaseModel):
    name: str
    description: str
    method: str
    path: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    base_url: str
