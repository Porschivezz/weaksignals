from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class EntityResponse(BaseModel):
    id: UUID
    canonical_name: str
    entity_type: str
    aliases: list[str] | None = None
    first_seen: datetime | None = None
    wikidata_id: str | None = None
    openalex_concept_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EntityBrief(BaseModel):
    id: UUID
    canonical_name: str
    entity_type: str

    model_config = {"from_attributes": True}
