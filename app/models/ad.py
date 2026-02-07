from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ViewAdResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    keywords: list[str] | None
    image_url: str | None
