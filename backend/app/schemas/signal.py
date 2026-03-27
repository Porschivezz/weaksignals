from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class SignalResponse(BaseModel):
    id: UUID
    title: str
    description: str | None = None
    cluster: str | None = None
    signal_type: str
    novelty_score: float
    momentum_score: float
    composite_score: float
    confidence_level: float
    time_horizon: str | None = None
    impact_domains: list[str] | None = None
    evidence_ids: list[UUID] | None = None
    first_detected: datetime
    last_updated: datetime
    status: str

    model_config = {"from_attributes": True}


class SignalBrief(BaseModel):
    id: UUID
    title: str
    signal_type: str
    composite_score: float
    confidence_level: float
    status: str
    first_detected: datetime

    model_config = {"from_attributes": True}


class TenantSignalResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    signal_id: UUID
    relevance_score: float
    industry_relevance: float
    competitor_activity: float
    opportunity_score: float
    is_dismissed: bool
    created_at: datetime
    signal: SignalResponse

    model_config = {"from_attributes": True}


class SourceDocumentResponse(BaseModel):
    id: UUID
    external_id: str | None = None
    source: str
    title: str
    abstract: str | None = None
    authors: dict | list | None = None
    published_date: datetime | None = None
    url: str | None = None

    model_config = {"from_attributes": True}


class SignalTrajectoryPoint(BaseModel):
    timestamp: datetime
    metric_name: str
    value: float


class SignalTrajectory(BaseModel):
    signal_id: UUID
    title: str
    points: list[SignalTrajectoryPoint]
