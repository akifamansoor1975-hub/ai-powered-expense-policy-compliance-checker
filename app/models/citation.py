from pydantic import BaseModel


class PolicyCitation(BaseModel):
    version_id: str
    source_document: str
    section_reference: str | None = None
    clause_text: str