from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" or "model"
    parts: list[str]


class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response: str
    generation_time: float = 0.0
    used_tokens: int = 0


class ChatMessageWithMetadata(BaseModel):
    """Extended chat message with generation metadata."""
    role: str
    parts: list[str]
    generation_time: float = 0.0
    used_tokens: int = 0


class SaveChatRequest(BaseModel):
    """Request to save a complete chat session."""
    mode: str  # "basic", "rag", "mcp", "agent"
    history: list[ChatMessageWithMetadata]
    version: float | None = None
    helpful: bool = False


class SaveChatResponse(BaseModel):
    """Response after saving a chat session."""
    id: int
    created_at: datetime
    mode: str
    version: float | None
    helpful: bool
