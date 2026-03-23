import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    Column,
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


class EntityType(str, enum.Enum):
    technology = "technology"
    method = "method"
    material = "material"
    algorithm = "algorithm"
    framework = "framework"


class ExtractionMethod(str, enum.Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    canonical_name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    entity_type: Mapped[EntityType] = mapped_column(
        Enum(EntityType), nullable=False
    )
    aliases: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    wikidata_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    openalex_concept_id: Mapped[str | None] = mapped_column(
        String(256), nullable=True
    )
    embedding = Column(Vector(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    document_entities: Mapped[list["DocumentEntity"]] = relationship(
        "DocumentEntity", back_populates="entity", lazy="selectin"
    )


class DocumentEntity(Base):
    __tablename__ = "document_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_method: Mapped[ExtractionMethod | None] = mapped_column(
        Enum(ExtractionMethod), nullable=True
    )
    raw_mention: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(  # noqa: F821
        "Document", back_populates="entities", lazy="selectin"
    )
    entity: Mapped["Entity"] = relationship(
        "Entity", back_populates="document_entities", lazy="selectin"
    )
