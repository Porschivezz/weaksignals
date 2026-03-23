from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., max_length=255)
    industry_verticals: list[str] | None = None
    competitor_list: dict | None = None
    technology_watchlist: list[str] | None = None
    signal_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    language_preferences: list[str] | None = None


class TenantUpdate(BaseModel):
    name: str | None = None
    industry_verticals: list[str] | None = None
    competitor_list: dict | None = None
    technology_watchlist: list[str] | None = None
    signal_sensitivity: float | None = Field(default=None, ge=0.0, le=1.0)
    language_preferences: list[str] | None = None


class TenantResponse(BaseModel):
    id: UUID
    name: str
    industry_verticals: list[str] | None = None
    competitor_list: dict | None = None
    technology_watchlist: list[str] | None = None
    signal_sensitivity: float
    language_preferences: list[str] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
