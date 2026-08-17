from datetime import date, datetime

from pydantic import BaseModel


class PolicyVersion(BaseModel):
    version_id: str
    effective_date: date
    source_document: str
    uploaded_at: datetime


class PolicyChunkMetadata(BaseModel):
    chunk_id: str
    version_id: str
    source_document: str
    section_reference: str | None = None
    text: str