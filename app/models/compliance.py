from enum import Enum

from pydantic import BaseModel

from app.models.citation import PolicyCitation


class ComplianceStatus(str, Enum):
    compliant = "compliant"
    non_compliant = "non_compliant"
    needs_approval = "needs_approval"
    policy_silent = "policy_silent"


class ComplianceResult(BaseModel):
    status: ComplianceStatus
    explanation: str
    citation: PolicyCitation | None = None
    policy_version: str
    needs_human_review: bool
    review_reason: str | None = None