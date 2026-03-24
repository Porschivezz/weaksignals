"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("industry_verticals", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("competitor_list", postgresql.JSONB(), nullable=True),
        sa.Column("technology_watchlist", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("signal_sensitivity", sa.Float(), server_default="0.5"),
        sa.Column("language_preferences", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(320), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(512), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("ceo", "analyst", "admin", name="userrole"), server_default="analyst"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])

    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("external_id", sa.String(512), unique=True, nullable=True),
        sa.Column("source", sa.Enum("openalex", "arxiv", "semantic_scholar", name="documentsource"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("authors", postgresql.JSONB(), nullable=True),
        sa.Column("institutions", postgresql.JSONB(), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ingested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("processed", sa.Boolean(), server_default="false"),
    )
    op.execute("ALTER TABLE documents ADD COLUMN embedding vector(1024)")
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])
    op.create_index("ix_documents_external_id", "documents", ["external_id"])
    op.create_index("ix_documents_published_date", "documents", ["published_date"])

    # Create entities table
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_name", sa.String(512), nullable=False),
        sa.Column("entity_type", sa.Enum("technology", "method", "material", "algorithm", "framework", name="entitytype"), nullable=False),
        sa.Column("aliases", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("first_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("wikidata_id", sa.String(64), nullable=True),
        sa.Column("openalex_concept_id", sa.String(256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE entities ADD COLUMN embedding vector(1024)")
    op.create_index("ix_entities_canonical_name", "entities", ["canonical_name"])

    # Create document_entities table
    op.create_table(
        "document_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("extraction_method", sa.Enum("L1", "L2", "L3", name="extractionmethod"), nullable=True),
        sa.Column("raw_mention", sa.Text(), nullable=True),
    )
    op.create_index("ix_document_entities_document_id", "document_entities", ["document_id"])
    op.create_index("ix_document_entities_entity_id", "document_entities", ["entity_id"])

    # Create signals table
    op.create_table(
        "signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("signal_type", sa.Enum("weak_signal", "emerging_trend", "strong_signal", name="signaltype"), nullable=False),
        sa.Column("novelty_score", sa.Float(), server_default="0.0"),
        sa.Column("momentum_score", sa.Float(), server_default="0.0"),
        sa.Column("composite_score", sa.Float(), server_default="0.0"),
        sa.Column("confidence_level", sa.Float(), server_default="0.0"),
        sa.Column("time_horizon", sa.String(16), nullable=True),
        sa.Column("impact_domains", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("evidence_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("first_detected", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_updated", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.Enum("active", "confirmed", "dismissed", name="signalstatus"), server_default="active"),
    )

    # Create tenant_signals table
    op.create_table(
        "tenant_signals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("signal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("signals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relevance_score", sa.Float(), server_default="0.0"),
        sa.Column("industry_relevance", sa.Float(), server_default="0.0"),
        sa.Column("competitor_activity", sa.Float(), server_default="0.0"),
        sa.Column("opportunity_score", sa.Float(), server_default="0.0"),
        sa.Column("is_dismissed", sa.Boolean(), server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tenant_signals_tenant_id", "tenant_signals", ["tenant_id"])
    op.create_index("ix_tenant_signals_signal_id", "tenant_signals", ["signal_id"])

    # Create vector indexes using HNSW for approximate nearest neighbor search
    op.execute(
        "CREATE INDEX ix_documents_embedding ON documents USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX ix_entities_embedding ON entities USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entities_embedding")
    op.execute("DROP INDEX IF EXISTS ix_documents_embedding")

    op.drop_table("tenant_signals")
    op.drop_table("signals")
    op.drop_table("document_entities")
    op.drop_table("entities")
    op.drop_table("documents")
    op.drop_table("users")
    op.drop_table("tenants")

    op.execute("DROP TYPE IF EXISTS signalstatus")
    op.execute("DROP TYPE IF EXISTS signaltype")
    op.execute("DROP TYPE IF EXISTS extractionmethod")
    op.execute("DROP TYPE IF EXISTS entitytype")
    op.execute("DROP TYPE IF EXISTS documentsource")
    op.execute("DROP TYPE IF EXISTS userrole")

    op.execute("DROP EXTENSION IF EXISTS vector")
