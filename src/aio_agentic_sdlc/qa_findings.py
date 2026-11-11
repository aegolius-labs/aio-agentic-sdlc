"""Consume agentic-qa-kit findings as evidence and choose their disposition (Seam B).

The kit exports confirmed findings as an `aqk-findings` document. This module
validates such a document, proposes a disposition for each finding, and records
the disposition a person chose, with its reason, in the evidence ledger.

A finding has exactly two dispositions (owner decision, 2026-11-11):

- `revert-node`: the defect falls inside the accepted intent of the Intention
  node the finding names. Recording it reopens one acceptance criterion of that
  node, so the diff regenerates the work as a `verify_acceptance` task. No new
  work item is created. It needs a named approver.
- `bug-handoff`: the defect falls outside modeled intent. The kit's own
  `backlog-export` then emits one Bug payload for agentic-backlog-kit.

A finding names its node by canonical GUID when the QA session knew it. A
finding with no GUID, a GUID the Intention DAG does not define, or a GUID whose
node is not approved intent is proposed as `bug-handoff` and reported. It is
never matched by title or id, because that would be a guess.

Everything here is evidence. Proposing is read-only, and recording never edits
the Intention DAG: approved intent stays approved, and the node returns to the
diff only because its acceptance evidence no longer holds.

The contract is pinned by `tests/fixtures/seam-b/findings.json`, which the kit
holds byte-identically. Neither repository imports the other.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.evidence import (
    EvidenceLedger,
    QADisposition,
    record_qa_disposition,
)
from aio_agentic_sdlc.intent_ir import ApprovalState

CONTRACT = "aqk-findings"
# Additive fields keep the version; removals and renames bump it. An unknown
# version is rejected rather than read on a best-effort basis.
SUPPORTED_CONTRACT_VERSIONS = frozenset({1})

_TOP_LEVEL_FIELDS = (
    "contract",
    "contract_version",
    "exported_at",
    "source",
    "findings",
    "digest",
)
_FINDING_FIELDS = (
    "session_id",
    "finding_id",
    "source",
    "intent_guid",
    "status",
    "session",
    "title",
    "quality_attribute",
    "severity",
    "confidence",
    "summary",
    "expected",
    "actual",
    "oracle",
    "reproduction",
    "attempt_ids",
    "evidence",
    "limitations",
    "acceptance_criteria",
    "suspected_root_cause",
)
_TEXT_FIELDS = (
    "title",
    "quality_attribute",
    "severity",
    "confidence",
    "summary",
    "expected",
    "actual",
    "oracle",
    "suspected_root_cause",
)
_REPRODUCIBILITY = {"always", "intermittent", "once"}
_INTEGRITY = {"chained", "unchained"}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class FindingsError(ValueError):
    """Raised when a findings document or a disposition violates Seam B."""


def findings_digest(document: dict[str, Any]) -> str:
    """Return the kit's digest of a document: canonical JSON without `digest`."""

    body = {key: value for key, value in document.items() if key != "digest"}
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def finding_source(session_id: str, finding_id: str) -> str:
    """The kit's stable source string for one finding."""

    return f"agentic-qa-kit:session={session_id};finding={finding_id}"


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _texts(value: Any) -> bool:
    return isinstance(value, list) and all(_text(item) for item in value)


def _validate_finding(index: int, finding: Any) -> None:
    where = f"findings[{index}]"
    if not isinstance(finding, dict):
        raise FindingsError(f"{where} must be an object")
    missing = [field for field in _FINDING_FIELDS if field not in finding]
    if missing:
        raise FindingsError(f"{where} is missing {', '.join(missing)}")
    for field in ("session_id", "finding_id"):
        if not isinstance(finding[field], str) or not _ID.match(finding[field]):
            raise FindingsError(f"{where}.{field} must be a kit ID")
    if finding["source"] != finding_source(
        finding["session_id"], finding["finding_id"]
    ):
        raise FindingsError(f"{where}.source must name its session and finding")
    guid = finding["intent_guid"]
    if guid is not None and (not isinstance(guid, str) or not _GUID.match(guid)):
        raise FindingsError(
            f"{where}.intent_guid must be a lowercase canonical GUID or null"
        )
    if finding["status"] != "confirmed":
        raise FindingsError(
            f"{where}.status is {finding['status']!r}; only confirmed findings "
            "cross Seam B"
        )
    session = finding["session"]
    if not isinstance(session, dict) or not all(
        key in session for key in ("mode", "integrity", "target")
    ):
        raise FindingsError(f"{where}.session must carry mode, integrity and target")
    if session["integrity"] not in _INTEGRITY:
        raise FindingsError(
            f"{where}.session.integrity must be 'chained' or 'unchained'; "
            "a broken session is not evidence"
        )
    target = session["target"]
    if (
        not isinstance(target, dict)
        or not _text(target.get("revision"))
        or not isinstance(target.get("dirty"), bool)
    ):
        raise FindingsError(f"{where}.session.target needs a revision and dirty flag")
    for field in _TEXT_FIELDS:
        if not _text(finding[field]):
            raise FindingsError(f"{where}.{field} must be a non-empty string")
    reproduction = finding["reproduction"]
    if not isinstance(reproduction, dict):
        raise FindingsError(f"{where}.reproduction must be an object")
    steps = reproduction.get("steps")
    if not _texts(steps) or not steps:
        raise FindingsError(f"{where} needs reproduction steps to be confirmed")
    if not _texts(reproduction.get("preconditions")):
        raise FindingsError(f"{where}.reproduction.preconditions must be strings")
    if reproduction.get("reproducibility") not in _REPRODUCIBILITY:
        raise FindingsError(
            f"{where}.reproduction.reproducibility must be one of "
            + ", ".join(sorted(_REPRODUCIBILITY))
        )
    attempts = reproduction.get("attempts")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise FindingsError(f"{where}.reproduction.attempts must be at least 1")
    for field in ("attempt_ids", "limitations"):
        if not _texts(finding[field]):
            raise FindingsError(f"{where}.{field} must be a list of strings")
    if not _texts(finding["acceptance_criteria"]) or not finding["acceptance_criteria"]:
        raise FindingsError(f"{where}.acceptance_criteria must not be empty")
    evidence = finding["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise FindingsError(f"{where}.evidence must not be empty")
    for position, entry in enumerate(evidence):
        if (
            not isinstance(entry, dict)
            or not _text(entry.get("kind"))
            or not _text(entry.get("location"))
        ):
            raise FindingsError(
                f"{where}.evidence[{position}] needs a kind and a location"
            )


def validate_findings(document: Any) -> dict[str, Any]:
    """Return the document unchanged if it honours contract v1, else raise."""

    if not isinstance(document, dict):
        raise FindingsError("A findings document must be a JSON object")
    if document.get("contract") != CONTRACT:
        raise FindingsError(
            f"Not an {CONTRACT} document: contract is {document.get('contract')!r}"
        )
    version = document.get("contract_version")
    if (
        not isinstance(version, int)
        or isinstance(version, bool)
        or version not in SUPPORTED_CONTRACT_VERSIONS
    ):
        supported = ", ".join(
            str(value) for value in sorted(SUPPORTED_CONTRACT_VERSIONS)
        )
        raise FindingsError(
            f"Unknown {CONTRACT} contract_version {version!r}; "
            f"this framework reads version {supported}"
        )
    missing = [field for field in _TOP_LEVEL_FIELDS if field not in document]
    if missing:
        raise FindingsError(f"Findings document is missing {', '.join(missing)}")
    if not isinstance(document["findings"], list):
        raise FindingsError("findings must be an array")
    seen: set[str] = set()
    for index, finding in enumerate(document["findings"]):
        _validate_finding(index, finding)
        if finding["source"] in seen:
            raise FindingsError(f"{finding['source']} appears more than once")
        seen.add(finding["source"])
    digest = document["digest"]
    if not isinstance(digest, str) or not _DIGEST.match(digest):
        raise FindingsError("digest must be 'sha256:' followed by 64 hex digits")
    if findings_digest(document) != digest:
        raise FindingsError(
            "Findings digest does not match its content; "
            "the document was edited after the kit produced it"
        )
    return document


def load_findings(path: str | Path) -> dict[str, Any]:
    """Read and validate one findings document from disk."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise FindingsError(f"Findings document is not valid JSON: {error}") from error
    return validate_findings(document)


def _propose(finding: dict[str, Any], nodes_by_guid: dict[str, Any]) -> dict[str, Any]:
    guid = finding["intent_guid"]
    node = nodes_by_guid.get(guid) if guid else None
    proposal: dict[str, Any] = {
        "session_id": finding["session_id"],
        "finding_id": finding["finding_id"],
        "source": finding["source"],
        "title": finding["title"],
        "severity": finding["severity"],
        "intent_guid": guid,
        "intent_id": node.id if node is not None else None,
        "node_name": node.name if node is not None else None,
    }
    if guid is None:
        code, disposition = "no_guid", "bug-handoff"
        reason = (
            "The QA session named no Intention node, so the defect is outside "
            "modeled intent. It is never matched by title or id."
        )
    elif node is None:
        code, disposition = "guid_not_in_intention", "bug-handoff"
        reason = f"No Intention node has GUID {guid}; reported, not guessed."
    elif node.intent is None or node.intent.approval.state != ApprovalState.APPROVED:
        state = "none" if node.intent is None else node.intent.approval.state.value
        code, disposition = "intent_not_approved", "bug-handoff"
        reason = (
            f"'{node.name}' is not accepted intent (approval state {state}), "
            "so there is no accepted node to revert."
        )
    else:
        code, disposition = "inside_accepted_intent", "revert-node"
        reason = (
            f"The finding names '{node.name}', which is approved intent. Reopen "
            "the acceptance criterion it violates so the diff regenerates the work."
        )
    proposal.update(
        {
            "proposed_disposition": disposition,
            "reason_code": code,
            "reason": reason,
        }
    )
    if code == "inside_accepted_intent":
        proposal["criteria"] = [c.id for c in node.intent.acceptance_criteria]
    return proposal


def _nodes_by_guid(intention: DAGManager) -> dict[str, Any]:
    return {str(UUID(node_id)): node for node_id, node in intention.nodes.items()}


def propose_dispositions(
    document: dict[str, Any],
    intention: DAGManager,
    *,
    ledger: EvidenceLedger | None = None,
) -> dict[str, Any]:
    """Propose a disposition for every finding; read-only."""

    validate_findings(document)
    nodes = _nodes_by_guid(intention)
    recorded = {d.source: d for d in (ledger.qa_dispositions if ledger else [])}
    findings = []
    for finding in document["findings"]:
        proposal = _propose(finding, nodes)
        disposition = recorded.get(finding["source"])
        proposal["recorded"] = (
            disposition.model_dump(mode="json", exclude_none=True)
            if disposition is not None
            else None
        )
        findings.append(proposal)
    return {
        "authority": "evidence",
        "contract": CONTRACT,
        "contract_version": document["contract_version"],
        "exported_at": document["exported_at"],
        "digest": document["digest"],
        "summary": {
            "findings": len(findings),
            "revert-node": sum(
                f["proposed_disposition"] == "revert-node" for f in findings
            ),
            "bug-handoff": sum(
                f["proposed_disposition"] == "bug-handoff" for f in findings
            ),
            "recorded": sum(f["recorded"] is not None for f in findings),
        },
        "findings": findings,
    }


def record_disposition(
    ledger_path: str | Path,
    document: dict[str, Any],
    intention: DAGManager,
    *,
    session_id: str,
    finding_id: str,
    disposition: str,
    reason: str,
    recorded_by: str,
    recorded_at: str | datetime,
    criterion_id: str | None = None,
    approved_by: str | None = None,
) -> QADisposition:
    """Record the chosen disposition of one finding, with its reason.

    The proposal is recomputed against the current Intention DAG. `revert-node`
    is refused unless the finding names an approved node. The record goes into
    the evidence ledger under its lock; the Intention DAG is never written.
    """

    validate_findings(document)
    source = finding_source(session_id, finding_id)
    finding = next((f for f in document["findings"] if f["source"] == source), None)
    if finding is None:
        raise FindingsError(f"The document has no finding {source}")
    proposal = _propose(finding, _nodes_by_guid(intention))
    if disposition == "revert-node" and proposal["intent_id"] is None:
        raise FindingsError(
            f"revert-node needs a finding that names an Intention node; "
            f"{source} is {proposal['reason_code']}"
        )
    if (
        disposition == "revert-node"
        and proposal["reason_code"] != "inside_accepted_intent"
    ):
        raise FindingsError(f"revert-node needs approved intent; {proposal['reason']}")
    record = QADisposition(
        source=source,
        session_id=session_id,
        finding_id=finding_id,
        findings_digest=document["digest"],
        title=finding["title"],
        disposition=disposition,
        proposed_disposition=proposal["proposed_disposition"],
        intent_id=(str(UUID(proposal["intent_id"])) if proposal["intent_id"] else None),
        criterion_id=criterion_id,
        reason=reason,
        recorded_by=recorded_by,
        recorded_at=recorded_at,
        approved_by=approved_by,
    )
    record_qa_disposition(ledger_path, intention, record)
    return record


def render_proposals(report: dict[str, Any]) -> str:
    """A short human brief of the proposals."""

    summary = report["summary"]
    lines = [
        f"QA findings ({report['contract']} v{report['contract_version']}, "
        f"{report['digest']})",
        f"{summary['findings']} finding(s): {summary['revert-node']} revert-node, "
        f"{summary['bug-handoff']} bug-handoff proposed; "
        f"{summary['recorded']} recorded.",
        "",
    ]
    for finding in report["findings"]:
        lines.append(f"- {finding['source']}: {finding['title']}")
        lines.append(
            f"  Proposed: {finding['proposed_disposition']} "
            f"({finding['reason_code']}). {finding['reason']}"
        )
        if finding.get("criteria"):
            lines.append(f"  Criteria of the node: {', '.join(finding['criteria'])}")
        recorded = finding["recorded"]
        if recorded:
            lines.append(
                f"  Recorded: {recorded['disposition']} by {recorded['recorded_by']}"
                + (
                    f", approved by {recorded['approved_by']}"
                    if recorded.get("approved_by")
                    else ""
                )
            )
        else:
            lines.append("  Recorded: nothing yet; `dag-tool qa record` records it.")
    lines.append("")
    lines.append(
        "Proposals are evidence. revert-node needs a named approver and never "
        "edits the Intention DAG."
    )
    return "\n".join(lines)


__all__ = [
    "CONTRACT",
    "SUPPORTED_CONTRACT_VERSIONS",
    "FindingsError",
    "finding_source",
    "findings_digest",
    "load_findings",
    "propose_dispositions",
    "record_disposition",
    "render_proposals",
    "validate_findings",
]
