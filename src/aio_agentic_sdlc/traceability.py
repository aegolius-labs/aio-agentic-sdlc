"""Plain-language traceability for one Intention node (ROADMAP M4).

The report follows one requirement from the person who stated it, through
its approval, the work that was authorized, the source symbol that
implements it and the evidence for each acceptance criterion, to whether it
is done. It is written for a reader who does not know the framework.

It is read-only and derives everything from committed state: the Intention
DAG, the generated Reality DAG, the evidence ledger, mapping receipts in the
source, optional triage decisions and the local backlog. It never decides
anything. "Done" here means exactly what the diff means by it: the node is
confirmed in Reality and every acceptance criterion has its required
evidence (ADR 0003).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import UUID

from .dag_manager import DAGManager
from .drift_triage import DriftTriageEngine, TriageDecisionSet
from .evidence import EvidenceEvaluator, load_evidence_ledger
from .mapping import MappingEngine
from .reconciliation import ReconciliationEngine
from .workspace import (
    BACKLOG_FILE,
    INTENTION_DAG_FILE,
    REALITY_DAG_FILE,
    WORKSPACE_DIR,
)

TRACE_SCHEMA_VERSION = 1

LEVEL_WORDS = {
    "declared": "only declared in the intent",
    "mapped": "linked to source by an approved mapping",
    "structural": "the named artifact exists",
    "tested": "an automated test passed",
    "behaviorally_verified": "the behavior was verified end to end",
    "approved": "a person accepted it",
}

CLASSIFICATION_WORDS = {
    "confirmed": "implemented, and a person approved which code implements it",
    "unmapped": "no implementation has been linked to it yet",
    "ambiguous": "several pieces of code could implement it; a person must choose",
    "structural_candidate": (
        "one piece of code looks like the implementation, but no person has "
        "approved the link yet"
    ),
}

TRIAGE_WORDS = {
    "missing_implementation": "work is authorized: the implementation is missing",
    "acceptance_evidence_required": (
        "work is authorized: the implementation exists but some acceptance "
        "criteria still lack their evidence"
    ),
    "needs_classification": (
        "waiting for a person to decide whether the implementation is missing"
    ),
    "identity_review_required": "waiting for a person to review a source link",
    "framework_tooling_drift": (
        "it exists, but the framework's tooling cannot observe it yet"
    ),
    "obsolete_or_unapproved_intent": (
        "no work is authorized, because the intent is not approved"
    ),
}


class TraceError(ValueError):
    """The trace cannot be built from the project's state."""


def build_trace(
    project_root: str | Path,
    intent_id: str,
    *,
    decisions: TriageDecisionSet | None = None,
) -> dict[str, Any]:
    """Collect one node's trace from committed state. Read-only."""

    root = Path(project_root).resolve()
    try:
        canonical = str(UUID(intent_id))
    except ValueError as error:
        raise TraceError("intent_id must be a canonical UUID") from error
    intention_path = root / INTENTION_DAG_FILE
    reality_path = root / REALITY_DAG_FILE
    if not intention_path.is_file():
        raise TraceError(f"no Intention DAG at {INTENTION_DAG_FILE}")
    if not reality_path.is_file():
        raise TraceError(
            f"no Reality DAG at {REALITY_DAG_FILE}; run dag-tool generate-reality"
        )
    intention = DAGManager.load(str(intention_path))
    reality = DAGManager.load(str(reality_path))
    node = next(
        (n for n in intention.nodes.values() if str(UUID(n.id)) == canonical), None
    )
    if node is None or node.intent is None:
        raise TraceError(f"Intention node {canonical} with Intent IR does not exist")
    intent = node.intent

    record = next(
        (
            r
            for r in ReconciliationEngine(intention, reality).iter_intent_records()
            if str(UUID(r["intent"]["id"])) == canonical
        ),
        None,
    )
    classification = record["classification"] if record else "unmapped"

    evaluator = EvidenceEvaluator(
        load_evidence_ledger(root / WORKSPACE_DIR / "evidence.json"),
        project_root=root,
    )
    acceptance = evaluator.evaluate(node, mapped=classification == "confirmed")
    statements = {c.id: c.statement for c in intent.acceptance_criteria}

    receipts = [
        receipt
        for receipt in MappingEngine(root, intention_path).check_receipts()["receipts"]
        if receipt.get("intent_id") == canonical
    ]

    triage_item = None
    engine = DriftTriageEngine(intention, reality, evidence=evaluator)
    # A decision file binds to the plan it was made against. Once the work
    # moves on it is stale for authorizing anything, but it is still the
    # record of who authorized the work, so the trace shows it either way.
    current = (
        decisions is not None
        and decisions.plan_digest == engine.source_identity()["plan_digest"]
    )
    report = engine.analyze(
        decisions=decisions if current else None,
        max_items=max(1, len(intention.nodes) + len(intention.edges)),
    )
    for item in report["items"]:
        if item["audit"].get("subject_key") == f"intent:{canonical}":
            triage_item = item
            break
    decision = None
    if decisions is not None:
        decision = next(
            (d for d in decisions.decisions if d.subject_key == f"intent:{canonical}"),
            None,
        )

    tasks = []
    backlog_path = root / BACKLOG_FILE
    if backlog_path.is_file():
        try:
            backlog = json.loads(backlog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            backlog = {}
        for name, item in (backlog.get("nodes") or {}).items():
            if isinstance(item, dict) and item.get("canonical_intent_id") == canonical:
                tasks.append(
                    {
                        "name": name,
                        "status": item.get("status"),
                        "resolution": item.get("resolution"),
                        "blockers": item.get("blockers", []),
                    }
                )

    done = (
        classification == "confirmed"
        and acceptance is not None
        and acceptance["complete"]
        and triage_item is None
    )
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "intent_id": canonical,
        "name": node.name,
        "type": node.type.value,
        "description": node.description,
        "done": done,
        "wanted": [
            {
                "source_type": p.source_type.value,
                "reference": p.reference,
                "statement": p.statement,
            }
            for p in intent.provenance
        ],
        "approval": {
            "state": intent.approval.state.value,
            "by": intent.approval.approved_by,
            "at": (
                intent.approval.approved_at.isoformat()
                if intent.approval.approved_at
                else None
            ),
            "rationale": intent.approval.rationale,
            "revision": intent.revision_history[-1].revision,
        },
        "open_ambiguities": [
            a.question for a in intent.ambiguities if a.status.value == "open"
        ],
        "implementation": {
            "classification": classification,
            "receipts": [
                {
                    "source_path": r["source_path"],
                    "line": r.get("receipt_line"),
                    "symbol_kind": r.get("symbol_kind"),
                    "symbol_name": r.get("symbol_name"),
                    "status": r["status"],
                }
                for r in receipts
            ],
        },
        "acceptance": [
            {
                "id": criterion["id"],
                "statement": statements.get(criterion["id"], ""),
                "satisfied": criterion["satisfied"],
                "references": criterion["references"],
            }
            for criterion in (acceptance or {}).get("criteria", [])
        ],
        "triage": (
            {
                "classification": triage_item["classification"],
                "reason": triage_item["reason"],
                "implementation_authorized": triage_item["implementation_authorized"],
            }
            if triage_item
            else None
        ),
        "decision": (
            {
                "classification": decision.classification.value,
                "by": decision.decided_by,
                "at": decision.decided_at.isoformat(),
                "rationale": decision.rationale,
                "current": current,
            }
            if decision
            else None
        ),
        "tasks": tasks,
    }


def _missing(trace: dict[str, Any]) -> list[str]:
    reasons = []
    if trace["approval"]["state"] != "approved":
        reasons.append(
            f"The intent is {trace['approval']['state'].replace('_', ' ')}, "
            "not approved, so no work on it is authorized."
        )
    if trace["implementation"]["classification"] != "confirmed":
        reasons.append(
            "Implementation: "
            + CLASSIFICATION_WORDS.get(
                trace["implementation"]["classification"],
                trace["implementation"]["classification"],
            )
            + "."
        )
    for criterion in trace["acceptance"]:
        if not criterion["satisfied"]:
            reasons.append(
                f"Acceptance criterion {criterion['id']} lacks its evidence."
            )
    if trace["triage"] and not reasons:
        reasons.append(TRIAGE_WORDS.get(trace["triage"]["classification"], ""))
    return reasons


def render_trace_markdown(trace: dict[str, Any]) -> str:
    """Render a trace for a reader who does not know the framework."""

    lines = [f"# Traceability: {trace['name']}", ""]
    if trace["done"]:
        lines.append(
            "**Status: done.** The requirement is implemented, a person approved "
            "which code implements it, and every acceptance criterion has the "
            "evidence it requires."
        )
    else:
        lines.append("**Status: not done yet.**")
        lines.append("")
        lines.extend(f"- {reason}" for reason in _missing(trace))
    lines.extend(["", "## What was wanted", ""])
    if trace["description"]:
        lines.extend([trace["description"], ""])
    for source in trace["wanted"]:
        lines.append(
            f"- \"{source['statement']}\" "
            f"({source['source_type'].replace('_', ' ')}: {source['reference']})"
        )

    approval = trace["approval"]
    lines.extend(["", "## Who approved it", ""])
    if approval["state"] in ("approved", "rejected"):
        lines.append(
            f"{approval['state'].capitalize()} by {approval['by']} on "
            f"{approval['at']} (revision {approval['revision']})."
        )
        if approval["rationale"]:
            lines.append(f"Reason given: {approval['rationale']}")
    else:
        lines.append(
            f"Not approved yet: the intent is "
            f"{approval['state'].replace('_', ' ')} (revision {approval['revision']})."
        )
    if trace["open_ambiguities"]:
        lines.append("")
        lines.append("Open questions:")
        lines.extend(f"- {question}" for question in trace["open_ambiguities"])

    lines.extend(["", "## Why work was authorized", ""])
    if trace["decision"]:
        decision = trace["decision"]
        lines.append(
            f"{decision['by']} decided on {decision['at']} that "
            f"{TRIAGE_WORDS.get(decision['classification'], decision['classification'])}."
        )
        lines.append(f"Reason given: {decision['rationale']}")
        if not decision["current"]:
            lines.append(
                "That decision was made against an earlier state of the project, "
                "so it no longer authorizes new work."
            )
    elif trace["triage"]:
        lines.append(
            TRIAGE_WORDS.get(
                trace["triage"]["classification"], trace["triage"]["classification"]
            ).capitalize()
            + "."
        )
    else:
        lines.append("No work is outstanding for this requirement.")
    for task in trace["tasks"]:
        detail = f"; {task['resolution']}" if task.get("resolution") else ""
        lines.append(f"- Task \"{task['name']}\": {task['status']}{detail}.")

    implementation = trace["implementation"]
    lines.extend(["", "## Where it is implemented", ""])
    lines.append(
        CLASSIFICATION_WORDS.get(
            implementation["classification"], implementation["classification"]
        ).capitalize()
        + "."
    )
    for receipt in implementation["receipts"]:
        freshness = (
            "the code is unchanged since that approval"
            if receipt["status"] == "fresh"
            else "the code changed since that approval, so it needs a new look"
        )
        lines.append(
            f"- `{receipt['symbol_name']}` ({receipt['symbol_kind']}) in "
            f"`{receipt['source_path']}` (approval receipt on line {receipt['line']}): {freshness}."
        )

    lines.extend(["", "## Acceptance criteria and their evidence", ""])
    for criterion in trace["acceptance"]:
        mark = "met" if criterion["satisfied"] else "not met"
        lines.append(f"### {criterion['id']}: {mark}")
        lines.append("")
        lines.append(criterion["statement"])
        lines.append("")
        for reference in criterion["references"]:
            needed = LEVEL_WORDS.get(reference["required_level"], "")
            achieved = LEVEL_WORDS.get(reference["achieved_level"], "")
            lines.append(
                f"- Needs `{reference['reference']}`: {needed}. So far: {achieved}."
            )
            for support in reference.get("supporting", []):
                lines.append(f"  - {support['summary']} (`{support['locator']}`)")
        lines.append("")
    lines.append(
        "This report is read-only. It is generated from the project's committed "
        "state and does not approve or change anything."
    )
    return "\n".join(lines).rstrip() + "\n"
