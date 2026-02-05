from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.chat import ChatMessage


class RagRequest(BaseModel):
    message: str
    history: list[ChatMessage] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=50)


class AdCitation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str

    keywords: list[str] | None = None
    url: str
    image_url: str | None = None

    cpc: Decimal


class RagCitation(BaseModel):
    score: float
    distance: float
    ad: AdCitation


class RagResponse(BaseModel):
    response: str
    generation_time: float = 0.0
    used_tokens: int = 0
    citations: list[RagCitation] = Field(default_factory=list)
