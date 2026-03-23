import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    industry_verticals: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    competitor_list: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    technology_watchlist: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    signal_sensitivity: Mapped[float] = mapped_column(Float, default=0.5)
    language_preferences: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="tenant", lazy="selectin"
    )
    tenant_signals: Mapped[list["TenantSignal"]] = relationship(  # noqa: F821
        "TenantSignal", back_populates="tenant", lazy="selectin"
    )
