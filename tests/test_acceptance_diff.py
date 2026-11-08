"""ROADMAP M3: a confirmed node lacking required evidence stays in the diff."""

import json

import pytest
from click.testing import CliRunner

from aio_agentic_sdlc import orchestrator_loop
from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.diffing_engine import DiffingEngine
from aio_agentic_sdlc.drift_triage import (
    DriftTriageEngine,
    DriftTriageError,
    TriageDecisionSet,
)
from aio_agentic_sdlc.evidence import EvidenceEvaluator, EvidenceLedger
from aio_agentic_sdlc.intent_ir import ApprovalState
from tests.test_evidence import _manager, _node, _record


def _verify_tasks(plan):
    return {
        name: task
        for name, task in plan["nodes"].items()
        if task["action"] == "verify_acceptance"
    }


def test_confirmed_node_without_evidence_stays_in_the_diff():
    node = _node()
    intention, reality = _manager(node), _manager(_node(node.id))

    plain = DiffingEngine(intention, reality).calculate_diff()
    assert plain["nodes"] == {}
    assert "acceptance_incomplete" not in plain["meta"]["reconciliation"]

    plan = DiffingEngine(
        intention, reality, evidence=EvidenceEvaluator(EvidenceLedger())
    ).calculate_diff()

    tasks = _verify_tasks(plan)
    assert len(tasks) == 1
    ((name, task),) = tasks.items()
    assert name == f"Verify acceptance of Component 'Widget' [{node.id}]"
    assert task["category"] == "Verification"
    assert task["evidence"]["canonical_guid"] == node.id
    assert task["evidence"]["unverified_criteria"] == ["AC1"]
    assert "dag-tool evidence record" in task["description"]
    assert plan["meta"]["reconciliation"]["acceptance_incomplete"] == 1


def test_complete_evidence_leaves_the_diff():
    node = _node()
    ledger = EvidenceLedger(records=[_record(node)])

    plan = DiffingEngine(
        _manager(node),
        _manager(_node(node.id)),
        evidence=EvidenceEvaluator(ledger),
    ).calculate_diff()

    assert plan["nodes"] == {}
    assert plan["meta"]["reconciliation"]["acceptance_incomplete"] == 0


def test_unmapped_node_is_not_turned_into_verification_work():
    node = _node()
    plan = DiffingEngine(
        _manager(node), _manager(), evidence=EvidenceEvaluator(EvidenceLedger())
    ).calculate_diff()

    assert [task["action"] for task in plan["nodes"].values()] == ["investigate_intent"]
    assert plan["meta"]["reconciliation"]["acceptance_incomplete"] == 0


def test_triage_authorizes_evidence_work_for_approved_intent_only():
    approved = _node()
    unapproved = _node()
    unapproved.intent.approval.state = ApprovalState.REVIEW_REQUIRED
    unapproved.intent.approval.approved_by = None
    unapproved.intent.approval.approved_at = None
    intention = _manager(approved, unapproved)
    reality = _manager(_node(approved.id), _node(unapproved.id))
    evidence = EvidenceEvaluator(EvidenceLedger())

    report = DriftTriageEngine(intention, reality, evidence=evidence).analyze()

    by_id = {item["audit"]["canonical_intent_id"]: item for item in report["items"]}
    assert by_id[approved.id]["classification"] == "acceptance_evidence_required"
    assert by_id[approved.id]["decision_source"] == "evidence_gate"
    assert by_id[approved.id]["implementation_authorized"] is True
    assert "AC1" in by_id[approved.id]["reason"]
    assert by_id[unapproved.id]["classification"] == "obsolete_or_unapproved_intent"
    assert by_id[unapproved.id]["implementation_authorized"] is False
    assert report["summary"]["acceptance_evidence_required"] == 1
    assert report["summary"]["actionable_implementation"] == 1

    plain = DriftTriageEngine(intention, reality).analyze()
    assert plain["summary"]["plan_tasks"] == 0
    assert plain["summary"]["acceptance_evidence_required"] == 0


def test_evidence_binds_the_triage_digest():
    node = _node()
    intention, reality = _manager(node), _manager(_node(node.id))
    empty = DriftTriageEngine(
        intention, reality, evidence=EvidenceEvaluator(EvidenceLedger())
    ).source_identity()
    recorded = DriftTriageEngine(
        intention,
        reality,
        evidence=EvidenceEvaluator(EvidenceLedger(records=[_record(node)])),
    ).source_identity()
    plain = DriftTriageEngine(intention, reality).source_identity()

    assert "evidence_sha256" not in plain
    assert empty["plan_digest"] != recorded["plan_digest"]
    assert empty["plan_digest"] != plain["plan_digest"]

    stale = TriageDecisionSet.model_validate(
        {"schema_version": 1, "plan_digest": empty["plan_digest"], "decisions": []}
    )
    with pytest.raises(DriftTriageError, match="stale triage decisions"):
        DriftTriageEngine(
            intention,
            reality,
            evidence=EvidenceEvaluator(EvidenceLedger(records=[_record(node)])),
        ).analyze(decisions=stale)


def _workspace(tmp_path, node):
    workspace = tmp_path / ".aio-agentic-sdlc"
    workspace.mkdir()
    _manager(node).save(str(workspace / "intention-dag.yaml"))
    _manager(_node(node.id)).save(str(workspace / "reality-dag.yaml"))
    return workspace


def test_cli_diff_and_triage_grade_acceptance_by_default(tmp_path):
    node = _node()
    workspace = _workspace(tmp_path, node)
    paths = [
        "--intention",
        str(workspace / "intention-dag.yaml"),
        "--reality",
        str(workspace / "reality-dag.yaml"),
    ]
    runner = CliRunner()

    diff = runner.invoke(cli, ["diff", *paths])
    assert diff.exit_code == 0, diff.output
    assert len(_verify_tasks(json.loads(diff.output))) == 1

    skipped = runner.invoke(cli, ["diff", *paths, "--no-acceptance"])
    assert skipped.exit_code == 0, skipped.output
    assert json.loads(skipped.output)["nodes"] == {}

    triage = runner.invoke(cli, ["triage", *paths, "--format", "json"])
    assert triage.exit_code == 0, triage.output
    report = json.loads(triage.output)
    assert report["summary"]["acceptance_evidence_required"] == 1
    assert "evidence_sha256" in report["source"]

    human = runner.invoke(cli, ["triage", *paths])
    assert "Acceptance evidence required: 1" in human.output


def test_ingest_diff_marks_evidence_work_authorized(tmp_path, monkeypatch):
    node = _node()
    _workspace(tmp_path, node)
    monkeypatch.chdir(tmp_path)

    orchestrator_loop.ingest_diff()

    from aio_agentic_sdlc import core

    backlog = core.load_backlog()
    verify = [
        task
        for task in backlog["nodes"].values()
        if task.get("action") == "verify_acceptance"
    ]
    assert len(verify) == 1
    assert verify[0]["implementation_authorized"] is True
