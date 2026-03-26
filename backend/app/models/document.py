import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Column, DateTime, Enum, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class DocumentSource(str, enum.Enum):
    openalex = "openalex"
    arxiv = "arxiv"
    semantic_scholar = "semantic_scholar"
    pubmed = "pubmed"
    clinicaltrials = "clinicaltrials"
    rss = "rss"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    external_id: Mapped[str | None] = mapped_column(
        String(512), unique=True, nullable=True
    )
    source: Mapped[DocumentSource] = mapped_column(
        Enum(DocumentSource, name="documentsource", create_constraint=False),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    authors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    institutions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    embedding = Column(Vector(1024), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    entities: Mapped[list["DocumentEntity"]] = relationship(  # noqa: F821
        "DocumentEntity", back_populates="document", lazy="selectin"
    )
