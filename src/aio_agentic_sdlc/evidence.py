"""Explicit evidence model: what justifies, or limits, a completion claim.

A source mapping says which symbol implements an Intention node. It does not
say the node's acceptance criteria hold. This module grades each required
evidence reference of each acceptance criterion on one ordered scale
(ADR 0003):

    declared < mapped < structural < tested < behaviorally_verified < approved

`declared` and `mapped` are derived: every criterion is declared, and a
criterion is mapped when its node's canonical GUID is confirmed in Reality.
The higher levels come only from records in the evidence ledger
(`.aio-agentic-sdlc/evidence.json`), each bound to one exact
(intent, criterion, reference) triple. A reference is satisfied when its
achieved level reaches the level its kind requires. A node is complete only
when it is mapped and every reference of every criterion is satisfied.

Grading is read-only. Recording goes through `record_evidence`, which locks,
validates and atomically replaces the ledger. Evidence never edits intent.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Self
from uuid import UUID

from filelock import FileLock
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Node
from aio_agentic_sdlc.dag_store import guarded_file_path
from aio_agentic_sdlc.intent_ir import NonEmptyStr

EVIDENCE_SCHEMA_VERSION = 1
EVIDENCE_LEDGER_FILE = ".aio-agentic-sdlc/evidence.json"
DEFAULT_MAX_CRITERIA = 20


class EvidenceError(ValueError):
    """The evidence ledger or a record cannot be used."""


class EvidenceLevel(str, Enum):
    DECLARED = "declared"
    MAPPED = "mapped"
    STRUCTURAL = "structural"
    TESTED = "tested"
    BEHAVIORALLY_VERIFIED = "behaviorally_verified"
    APPROVED = "approved"

    @property
    def rank(self) -> int:
        return LEVEL_ORDER.index(self)


LEVEL_ORDER = tuple(EvidenceLevel)
DERIVED_LEVELS = {EvidenceLevel.DECLARED, EvidenceLevel.MAPPED}

# The level a reference must reach, chosen by the kind before its first colon.
# Kinds not listed need structural evidence: the artifact exists as named.
REQUIRED_LEVEL_BY_KIND = {
    "reconciliation": EvidenceLevel.MAPPED,
    "test": EvidenceLevel.TESTED,
    "ci": EvidenceLevel.BEHAVIORALLY_VERIFIED,
    "demo": EvidenceLevel.BEHAVIORALLY_VERIFIED,
    "fixture": EvidenceLevel.BEHAVIORALLY_VERIFIED,
    "qa": EvidenceLevel.BEHAVIORALLY_VERIFIED,
    "approval": EvidenceLevel.APPROVED,
    "review": EvidenceLevel.APPROVED,
}


def required_level(reference: str) -> EvidenceLevel:
    """Return the level a required evidence reference must reach."""

    kind = reference.split(":", 1)[0].strip().casefold()
    return REQUIRED_LEVEL_BY_KIND.get(kind, EvidenceLevel.STRUCTURAL)


class EvidenceRecord(BaseModel):
    """One observation that one required evidence reference reached a level."""

    model_config = ConfigDict(extra="forbid")

    intent_id: NonEmptyStr
    criterion_id: NonEmptyStr
    reference: NonEmptyStr
    level: EvidenceLevel
    locator: NonEmptyStr
    summary: NonEmptyStr
    recorded_by: NonEmptyStr
    recorded_at: datetime
    approved_by: NonEmptyStr | None = None

    @field_validator("intent_id")
    @classmethod
    def canonical_intent_id(cls, value: str) -> str:
        try:
            canonical = str(UUID(value))
        except ValueError as exc:
            raise EvidenceError("intent_id must be a canonical UUID") from exc
        if canonical != value:
            raise EvidenceError("intent_id must be a canonical lowercase UUID")
        return value

    @field_validator("recorded_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise EvidenceError("recorded_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def recorded_level_rules(self) -> Self:
        if self.level in DERIVED_LEVELS:
            raise EvidenceError(
                f"{self.level.value} is derived from intent and mapping; "
                "it cannot be recorded"
            )
        if self.level == EvidenceLevel.APPROVED and not self.approved_by:
            raise EvidenceError("approved evidence requires approved_by")
        if self.level != EvidenceLevel.APPROVED and self.approved_by:
            raise EvidenceError("approved_by is only valid on approved evidence")
        return self

    def key(self) -> tuple[str, str, str]:
        return (self.intent_id, self.criterion_id, self.reference)


QA_DISPOSITIONS = ("revert-node", "bug-handoff")


class QADisposition(BaseModel):
    """The disposition this framework chose for one QA finding (Seam B).

    `revert-node` reopens one acceptance criterion of an approved Intention
    node: evidence recorded before it no longer counts for that criterion, so
    the node returns to the diff until fresh evidence is recorded. It needs a
    named approver and never edits the Intention DAG. `bug-handoff` reopens
    nothing; the finding goes to agentic-backlog-kit as a Bug payload. Choosing
    other than the proposed disposition also needs a named approver.
    """

    model_config = ConfigDict(extra="forbid")

    source: NonEmptyStr
    session_id: NonEmptyStr
    finding_id: NonEmptyStr
    findings_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    title: NonEmptyStr
    disposition: Literal["revert-node", "bug-handoff"]
    proposed_disposition: Literal["revert-node", "bug-handoff"]
    intent_id: NonEmptyStr | None = None
    criterion_id: NonEmptyStr | None = None
    reason: NonEmptyStr
    recorded_by: NonEmptyStr
    recorded_at: datetime
    approved_by: NonEmptyStr | None = None

    @field_validator("intent_id")
    @classmethod
    def canonical_intent_id(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            canonical = str(UUID(value))
        except ValueError as exc:
            raise EvidenceError("intent_id must be a canonical UUID") from exc
        if canonical != value:
            raise EvidenceError("intent_id must be a canonical lowercase UUID")
        return value

    @field_validator("recorded_at")
    @classmethod
    def timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise EvidenceError("recorded_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def disposition_rules(self) -> Self:
        if self.disposition == "revert-node":
            if self.intent_id is None or self.criterion_id is None:
                raise EvidenceError(
                    "revert-node names the Intention node and the acceptance "
                    "criterion it reopens"
                )
            if not self.approved_by:
                raise EvidenceError(
                    "revert-node requires approved_by: a person approves it"
                )
        elif self.criterion_id is not None:
            raise EvidenceError("bug-handoff reopens no criterion")
        if self.disposition != self.proposed_disposition and not self.approved_by:
            raise EvidenceError(
                "choosing other than the proposed disposition requires approved_by"
            )
        return self


class EvidenceLedger(BaseModel):
    """The committed evidence ledger, schema version 1.

    `qa_dispositions` is additive: a ledger without any is written, and
    digested, exactly as before the field existed.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = EVIDENCE_SCHEMA_VERSION
    records: list[EvidenceRecord] = Field(default_factory=list)
    qa_dispositions: list[QADisposition] = Field(default_factory=list)

    def digest_payload(self) -> dict[str, Any]:
        """The JSON form triage digests; empty dispositions are left out."""

        payload = self.model_dump(mode="json")
        if not payload["qa_dispositions"]:
            del payload["qa_dispositions"]
        return payload


def load_evidence_ledger(path: str | Path) -> EvidenceLedger:
    """Load and validate a ledger; a missing file is an empty ledger."""

    target = guarded_file_path(path)
    if not target.exists():
        return EvidenceLedger()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise EvidenceError(f"evidence ledger is not valid JSON: {exc}") from exc
    return EvidenceLedger.model_validate(payload)


def _write_ledger(target: Path, ledger: EvidenceLedger) -> None:
    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            payload = ledger.model_dump(mode="json", exclude_none=True)
            if not payload["qa_dispositions"]:
                del payload["qa_dispositions"]
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _criterion(intention: DAGManager, record: EvidenceRecord):
    node = next(
        (n for n in intention.nodes.values() if str(UUID(n.id)) == record.intent_id),
        None,
    )
    if node is None or node.intent is None:
        raise EvidenceError(
            f"no Intention node with Intent IR has id {record.intent_id}"
        )
    criterion = next(
        (c for c in node.intent.acceptance_criteria if c.id == record.criterion_id),
        None,
    )
    if criterion is None:
        raise EvidenceError(
            f"'{node.name}' has no acceptance criterion {record.criterion_id}"
        )
    if record.reference not in criterion.required_evidence:
        raise EvidenceError(
            f"criterion {record.criterion_id} does not require '{record.reference}'"
        )
    return node, criterion


def record_evidence(
    ledger_path: str | Path,
    intention: DAGManager,
    record: EvidenceRecord,
    *,
    project_root: str | Path | None = None,
) -> int:
    """Append one record bound to an existing criterion; return the record count."""

    _criterion(intention, record)
    if project_root is not None and _locator_missing(record.locator, project_root):
        raise EvidenceError(f"locator does not exist: {record.locator}")
    target = guarded_file_path(ledger_path)
    with FileLock(f"{target}.lock", timeout=30):
        ledger = load_evidence_ledger(target)
        reopened_at = max(
            (
                d.recorded_at
                for d in ledger.qa_dispositions
                if d.disposition == "revert-node"
                and (d.intent_id, d.criterion_id)
                == (record.intent_id, record.criterion_id)
            ),
            default=None,
        )
        # A record that predates a QA reopening of its criterion no longer
        # counts, so fresh evidence at the same level is not a duplicate.
        if any(
            existing.key() == record.key()
            and existing.level == record.level
            and (reopened_at is None or existing.recorded_at > reopened_at)
            for existing in ledger.records
        ):
            raise EvidenceError(
                f"{record.reference} already has {record.level.value} evidence "
                f"for {record.criterion_id}"
            )
        ledger.records.append(record)
        _write_ledger(target, ledger)
        return len(ledger.records)


def record_qa_disposition(
    ledger_path: str | Path,
    intention: DAGManager,
    disposition: QADisposition,
) -> int:
    """Append one finding's disposition; a finding takes exactly one."""

    if disposition.disposition == "revert-node":
        node = next(
            (
                n
                for n in intention.nodes.values()
                if str(UUID(n.id)) == disposition.intent_id
            ),
            None,
        )
        if node is None or node.intent is None:
            raise EvidenceError(
                f"no Intention node with Intent IR has id {disposition.intent_id}"
            )
        if not any(
            c.id == disposition.criterion_id for c in node.intent.acceptance_criteria
        ):
            raise EvidenceError(
                f"'{node.name}' has no acceptance criterion {disposition.criterion_id}"
            )
    target = guarded_file_path(ledger_path)
    with FileLock(f"{target}.lock", timeout=30):
        ledger = load_evidence_ledger(target)
        existing = next(
            (d for d in ledger.qa_dispositions if d.source == disposition.source),
            None,
        )
        if existing is not None:
            raise EvidenceError(
                f"{disposition.source} already has disposition {existing.disposition}"
            )
        ledger.qa_dispositions.append(disposition)
        _write_ledger(target, ledger)
        return len(ledger.qa_dispositions)


def _locator_path(locator: str) -> str | None:
    if "://" in locator:
        return None
    path = locator.split("::", 1)[0].split("#", 1)[0].strip()
    return path if "/" in path or "." in path else None


def _locator_missing(locator: str, project_root: str | Path) -> bool:
    path = _locator_path(locator)
    if path is None:
        return False
    root = Path(project_root).resolve()
    candidate = (root / path).resolve()
    if root != candidate and root not in candidate.parents:
        return True
    return not candidate.exists()


# aio-sdlc-mapping-approval: {"candidate_reality_id":"246e0cb3-0815-5d3f-a08c-1b66539a8121","identity_approval":{"approved_at":"2026-11-05T19:30:00+00:00","approved_by":"Felix","candidate_reality_id":"246e0cb3-0815-5d3f-a08c-1b66539a8121","evidence_digest":"074fd7132e7343161ef9a1ddf66b74e213fdef07d2a2aa26f0d11c851ff51564","intent_id":"6b1b3459-38a0-5cd5-8ff4-1453f17c3d76","rationale":"EvidenceEvaluator grades acceptance evidence, which is this node's responsibility. Approved by Claude under Felix's standing approval of 2026-11-05. Identity only; acceptance criteria are graded separately.","schema_version":1,"source_path":"src/aio_agentic_sdlc/evidence.py","source_sha256":"3da3ed486a426e083c19e225c638f6b0eabd2488f80646ad52568c14a5f152b4","symbol_kind":"class","symbol_name":"EvidenceEvaluator"},"intent_id":"6b1b3459-38a0-5cd5-8ff4-1453f17c3d76","maintenance_approval":{"approved_at":"2026-11-10T12:17:12+00:00","approved_by":"Felix","evidence_digest":"756ba51565a3fe332f42d65d53db9bd5fa229c592c0133a12567ff38fb902b7f","rationale":"Felix approved the batch refresh of the 15 older mapping receipts on the 2026-11-10 decision card, at the review digests listed in .aio-agentic-sdlc/changes/symbol-receipts-2026-11-09/refresh-batch.json. Rebinds the receipt to its symbol; the approved identity is unchanged and no behavior or acceptance is claimed.","supersedes_receipt_sha256":"4568d7405351e6ba9f3330c2e1fd7afc14fc19f57339b65a59fbf063dde6070f"},"schema_version":2,"source_path":"src/aio_agentic_sdlc/evidence.py","source_sha256":"3da3ed486a426e083c19e225c638f6b0eabd2488f80646ad52568c14a5f152b4","symbol_kind":"class","symbol_name":"EvidenceEvaluator","symbol_sha256":"498b703275c728be41f070d2b724e1202472b585f269f172df3fcd353f0e79e0"}
# aio-sdlc-node: 6b1b3459-38a0-5cd5-8ff4-1453f17c3d76
class EvidenceEvaluator:
    """Grade acceptance criteria against derived levels and ledger records."""

    def __init__(
        self,
        ledger: EvidenceLedger,
        *,
        project_root: str | Path | None = None,
    ):
        self.ledger = ledger
        self.project_root = project_root
        self._records: dict[tuple[str, str, str], list[EvidenceRecord]] = {}
        for record in ledger.records:
            self._records.setdefault(record.key(), []).append(record)
        # An approved revert-node QA finding reopens one criterion: only
        # evidence recorded after the latest such finding counts for it.
        self._reopened: dict[tuple[str, str], list[QADisposition]] = {}
        for disposition in ledger.qa_dispositions:
            if disposition.disposition == "revert-node":
                self._reopened.setdefault(
                    (disposition.intent_id, disposition.criterion_id), []
                ).append(disposition)

    def _usable(self, record: EvidenceRecord) -> bool:
        return self.project_root is None or not _locator_missing(
            record.locator, self.project_root
        )

    def evaluate(
        self,
        node: Node,
        *,
        mapped: bool,
        max_criteria: int = DEFAULT_MAX_CRITERIA,
    ) -> dict[str, Any] | None:
        """Return the node's acceptance grading, or None without Intent IR."""

        if node.intent is None:
            return None
        intent_id = str(UUID(node.id))
        base = EvidenceLevel.MAPPED if mapped else EvidenceLevel.DECLARED
        criteria = []
        unverified_criteria = 0
        broken_records = 0
        for criterion in node.intent.acceptance_criteria:
            references = []
            reopened_by = self._reopened.get((intent_id, criterion.id), [])
            reopened_at = max((d.recorded_at for d in reopened_by), default=None)
            for reference in criterion.required_evidence:
                records = self._records.get((intent_id, criterion.id, reference), [])
                usable = [r for r in records if self._usable(r)]
                broken_records += len(records) - len(usable)
                if reopened_at is not None:
                    usable = [r for r in usable if r.recorded_at > reopened_at]
                achieved = max(
                    [base, *(r.level for r in usable)], key=lambda level: level.rank
                )
                needed = required_level(reference)
                satisfied = mapped and achieved.rank >= needed.rank
                if (
                    needed == EvidenceLevel.MAPPED
                    and reference != f"reconciliation:intent:{intent_id}"
                    and not any(r.level.rank >= needed.rank for r in usable)
                ):
                    satisfied = False
                if reopened_at is not None and not any(
                    r.level.rank >= needed.rank for r in usable
                ):
                    satisfied = False
                entry = {
                    "reference": reference,
                    "required_level": needed.value,
                    "achieved_level": achieved.value,
                    "satisfied": satisfied,
                }
                supporting = [
                    {"level": r.level.value, "locator": r.locator, "summary": r.summary}
                    for r in sorted(usable, key=lambda r: -r.level.rank)
                ]
                if supporting:
                    entry["supporting"] = supporting
                references.append(entry)
            satisfied = all(entry["satisfied"] for entry in references)
            if not satisfied:
                unverified_criteria += 1
            entry = {
                "id": criterion.id,
                "level": min(
                    (EvidenceLevel(e["achieved_level"]) for e in references),
                    key=lambda level: level.rank,
                ).value,
                "satisfied": satisfied,
                "references": references,
            }
            if reopened_by:
                entry["reopened_by"] = sorted(d.source for d in reopened_by)
            criteria.append(entry)
        returned = criteria[:max_criteria]
        result = {
            "complete": mapped and unverified_criteria == 0,
            "level": min(
                (EvidenceLevel(c["level"]) for c in criteria),
                key=lambda level: level.rank,
            ).value,
            "criteria_total": len(criteria),
            "criteria_unverified": unverified_criteria,
            "unverified_criteria": [c["id"] for c in criteria if not c["satisfied"]],
            "criteria": returned,
            "criteria_truncated": len(returned) < len(criteria),
        }
        if broken_records:
            result["records_with_missing_locator"] = broken_records
        return result

    def orphaned_records(self, intention: DAGManager) -> list[dict[str, str]]:
        """Records whose intent, criterion or reference no longer exists."""

        orphaned = []
        for record in self.ledger.records:
            try:
                _criterion(intention, record)
            except EvidenceError as exc:
                orphaned.append(
                    {
                        "intent_id": record.intent_id,
                        "criterion_id": record.criterion_id,
                        "reference": record.reference,
                        "reason": str(exc),
                    }
                )
        return orphaned
