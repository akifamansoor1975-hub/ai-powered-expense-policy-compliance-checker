from datetime import date, datetime

from pydantic import BaseModel


class PolicyVersion(BaseModel):
    version_id: str
    effective_date: date
    source_document: str
    uploaded_at: datetime