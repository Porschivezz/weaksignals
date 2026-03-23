import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SignalType(str, enum.Enum):
    weak_signal = "weak_signal"
    emerging_trend = "emerging_trend"
    strong_signal = "strong_signal"


class SignalStatus(str, enum.Enum):
    active = "active"
    confirmed = "confirmed"
    dismissed = "dismissed"


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    signal_type: Mapped[SignalType] = mapped_column(
        Enum(SignalType), nullable=False
    )
    novelty_score: Mapped[float] = mapped_column(Float, default=0.0)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_level: Mapped[float] = mapped_column(Float, default=0.0)
    time_horizon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    impact_domains: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    evidence_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=True
    )
    first_detected: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    status: Mapped[SignalStatus] = mapped_column(
        Enum(SignalStatus), default=SignalStatus.active
    )

    tenant_signals: Mapped[list["TenantSignal"]] = relationship(
        "TenantSignal", back_populates="signal", lazy="selectin"
    )


class TenantSignal(Base):
    __tablename__ = "tenant_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    signal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("signals.id", ondelete="CASCADE"), nullable=False
    )
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    industry_relevance: Mapped[float] = mapped_column(Float, default=0.0)
    competitor_activity: Mapped[float] = mapped_column(Float, default=0.0)
    opportunity_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    tenant: Mapped["Tenant"] = relationship(  # noqa: F821
        "Tenant", back_populates="tenant_signals", lazy="selectin"
    )
    signal: Mapped["Signal"] = relationship(
        "Signal", back_populates="tenant_signals", lazy="selectin"
    )
