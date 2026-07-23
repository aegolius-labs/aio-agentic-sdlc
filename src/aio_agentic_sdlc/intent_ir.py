"""Versioned intermediate representation for auditable human intent."""

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class IntentModel(BaseModel):
    """Strict base model for the stable Intent IR contract."""

    model_config = ConfigDict(extra="forbid")


class ProvenanceType(str, Enum):
    HUMAN_STATEMENT = "human_statement"
    CONVERSATION = "conversation"
    DOCUMENT = "document"
    IMPORTED_SPEC = "imported_spec"


class AmbiguityStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class ApprovalState(str, Enum):
    DRAFT = "draft"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"


class Provenance(IntentModel):
    source_type: ProvenanceType
    reference: NonEmptyStr
    statement: NonEmptyStr


class Ambiguity(IntentModel):
    question: NonEmptyStr
    status: AmbiguityStatus = AmbiguityStatus.OPEN
    resolution: NonEmptyStr | None = None

    @model_validator(mode="after")
    def require_resolution_when_resolved(self) -> Self:
        if self.status == AmbiguityStatus.RESOLVED and not self.resolution:
            raise ValueError("resolved ambiguity requires a resolution")
        return self


class AcceptanceCriterion(IntentModel):
    id: NonEmptyStr
    statement: NonEmptyStr
    required_evidence: list[NonEmptyStr] = Field(min_length=1)


class IntentRevision(IntentModel):
    revision: int = Field(ge=1)
    recorded_at: datetime
    actor: NonEmptyStr
    generator_version: NonEmptyStr
    summary: NonEmptyStr

    @field_validator("recorded_at")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("revision recorded_at must be timezone-aware")
        return value


class Approval(IntentModel):
    state: ApprovalState
    approved_by: NonEmptyStr | None = None
    approved_at: datetime | None = None
    rationale: NonEmptyStr | None = None

    @field_validator("approved_at")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("approval approved_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_approval_audit_fields(self) -> Self:
        if self.state == ApprovalState.APPROVED:
            if not self.approved_by:
                raise ValueError("approved intent requires approved_by")
            if self.approved_at is None:
                raise ValueError("approved intent requires approved_at")
        return self


class IntentIR(IntentModel):
    """Canonical Intent IR v1 payload attached to an Intention DAG node."""

    schema_version: Literal[1] = 1
    provenance: list[Provenance] = Field(min_length=1)
    assumptions: list[NonEmptyStr] = Field(default_factory=list)
    ambiguities: list[Ambiguity] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    acceptance_criteria: list[AcceptanceCriterion] = Field(min_length=1)
    revision_history: list[IntentRevision] = Field(min_length=1)
    responsible_agent: NonEmptyStr
    generator_version: NonEmptyStr
    approval: Approval

    @model_validator(mode="after")
    def validate_revision_history(self) -> Self:
        criterion_ids = [criterion.id for criterion in self.acceptance_criteria]
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError("acceptance criterion IDs must be unique")

        revisions = [entry.revision for entry in self.revision_history]
        if revisions[0] != 1 or any(
            current <= previous for previous, current in zip(revisions, revisions[1:])
        ):
            raise ValueError("revision history must start at 1 and be strictly increasing")
        if self.revision_history[-1].generator_version != self.generator_version:
            raise ValueError("latest revision generator_version must match Intent IR generator_version")
        return self
