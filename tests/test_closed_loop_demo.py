"""The closed-loop reference demo and the commands it needs (ROADMAP M4).

The integration test runs the demo end to end from an empty directory with
the framework's public commands. The unit tests cover what the demo exposed
as missing: creating the first Intention node, recording a person's intent
decision and triage decision through commands instead of hand-written JSON,
the agent work order, and the plain-language trace.
"""

import json
from datetime import datetime, timezone

import pytest
import yaml
from click.testing import CliRunner

from aio_agentic_sdlc import orchestrator_loop
from aio_agentic_sdlc.closed_loop_demo import (
    DEMO_INTENT_ID,
    REPORT_FILE,
    ClosedLoopDemo,
    DemoError,
    intake_payload,
    scripted_agent,
)
from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.intent_ir import ApprovalState
from aio_agentic_sdlc.intent_store import IntentStoreError, decide_intent_file
from aio_agentic_sdlc.traceability import build_trace, render_trace_markdown

NOW = "2026-11-08T20:00:00+00:00"


def _project_with_node(tmp_path, *, approve=False):
    """A workspace holding the demo's node, optionally approved."""

    workspace = tmp_path / ".aio-agentic-sdlc"
    workspace.mkdir()
    (tmp_path / "src").mkdir()
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps(intake_payload()), encoding="utf-8")
    runner = CliRunner()
    created = runner.invoke(
        cli,
        [
            "intent",
            "create-node",
            "--file",
            str(workspace / "intention-dag.yaml"),
            "--node-id",
            DEMO_INTENT_ID,
            "--type",
            "component",
            "--name",
            "Token Verifier",
            "--payload-file",
            str(payload),
        ],
    )
    assert created.exit_code == 0, created.output
    if approve:
        decide_intent_file(
            workspace / "intention-dag.yaml",
            DEMO_INTENT_ID,
            state=ApprovalState.APPROVED,
            decided_by="Reviewer",
            decided_at=datetime(2026, 11, 8, tzinfo=timezone.utc),
            rationale="Clear.",
            expected_revision=1,
            generator_version="test",
        )
    generated = runner.invoke(
        cli,
        [
            "generate-reality",
            "--dir",
            str(tmp_path),
            "--system",
            tmp_path.name,
            "--output",
            str(workspace / "reality-dag.yaml"),
        ],
    )
    assert generated.exit_code == 0, generated.output
    return workspace


def test_closed_loop_demo_reproduces_one_requirement_from_an_empty_directory(
    tmp_path,
):
    project = tmp_path / "demo"
    questions = []

    def approve(question):
        questions.append(question)
        return True

    output = []
    report = ClosedLoopDemo(
        project, approver="Test Reviewer", confirm=approve, echo=output.append
    ).run()

    # Five human gates: intent, triage decision, mapping, acceptance and the
    # Approval Gate on the finished work.
    assert questions == ["Approve as Test Reviewer?"] * 5
    text = report.read_text(encoding="utf-8")
    assert report.name == REPORT_FILE
    assert "**Status: done.**" in text
    assert "Approved by Test Reviewer" in text
    assert "Test Reviewer decided" in text
    assert "`verify_token` (function) in `src/demo_app/tokens.py`" in text
    assert "### TOKEN-AC1: met" in text and "### TOKEN-AC2: met" in text

    intent = (
        DAGManager.load(str(project / ".aio-agentic-sdlc" / "intention-dag.yaml"))
        .get_node(DEMO_INTENT_ID)
        .intent
    )
    assert intent.approval.state == ApprovalState.APPROVED
    assert intent.approval.approved_by == "Test Reviewer"
    backlog = json.loads(
        (project / ".aio-agentic-sdlc" / "backlog.json").read_text(encoding="utf-8")
    )
    (task,) = backlog["nodes"].values()
    assert task["status"] == "Completed"
    assert task["resolution"] == "left the diff; approved by Test Reviewer"
    assert task["approval"]["approved_by"] == "Test Reviewer"
    assert "# aio-sdlc-node: " + DEMO_INTENT_ID in (
        project / "src" / "demo_app" / "tokens.py"
    ).read_text(encoding="utf-8")


def test_closed_loop_demo_stops_at_a_refused_gate_without_approving(tmp_path):
    project = tmp_path / "demo"

    with pytest.raises(DemoError, match="stopped at the gate: approve the intent"):
        ClosedLoopDemo(
            project, approver="Reviewer", confirm=lambda _q: False, echo=lambda _l: None
        ).run()

    intent = (
        DAGManager.load(str(project / ".aio-agentic-sdlc" / "intention-dag.yaml"))
        .get_node(DEMO_INTENT_ID)
        .intent
    )
    assert intent.approval.state == ApprovalState.REVIEW_REQUIRED
    assert not (project / "src" / "demo_app" / "tokens.py").exists()


def test_closed_loop_demo_refuses_a_non_empty_directory(tmp_path):
    (tmp_path / "keep.txt").write_text("mine", encoding="utf-8")

    with pytest.raises(DemoError, match="empty directory"):
        ClosedLoopDemo(tmp_path, approver="Reviewer", confirm=lambda _q: True).run()


def test_demo_command_needs_a_terminal_or_yes(tmp_path):
    result = CliRunner().invoke(
        cli, ["demo", "--directory", str(tmp_path / "d"), "--approver", "Me"]
    )

    assert result.exit_code == 2
    assert "pass --yes" in result.output


def test_scripted_agent_refuses_a_work_order_without_the_requirement(tmp_path):
    with pytest.raises(DemoError, match="does not carry the requirement"):
        scripted_agent(
            "Execute this task: Canonical intent 9a3c has no match.", tmp_path
        )
    assert not (tmp_path / "src").exists()


def test_create_node_creates_a_missing_intention_dag(tmp_path):
    workspace = _project_with_node(tmp_path)

    dag = DAGManager.load(str(workspace / "intention-dag.yaml"))
    assert dag.metadata.name == tmp_path.name
    assert list(dag.nodes) == [DEMO_INTENT_ID]


def test_create_node_still_needs_the_workspace_directory(tmp_path):
    payload = tmp_path / "payload.json"
    payload.write_text(json.dumps(intake_payload()), encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        [
            "intent",
            "create-node",
            "--file",
            str(tmp_path / "missing" / "intention-dag.yaml"),
            "--node-id",
            DEMO_INTENT_ID,
            "--type",
            "component",
            "--name",
            "Token Verifier",
            "--payload-file",
            str(payload),
        ],
    )

    assert result.exit_code == 1
    assert "aio-sdlc init" in result.output


def test_intent_decide_appends_one_revision_and_keeps_content(tmp_path):
    workspace = _project_with_node(tmp_path)
    dag_file = workspace / "intention-dag.yaml"
    before = DAGManager.load(str(dag_file)).get_node(DEMO_INTENT_ID).intent

    result = CliRunner().invoke(
        cli,
        [
            "intent",
            "decide",
            "--file",
            str(dag_file),
            "--node-id",
            DEMO_INTENT_ID,
            "--state",
            "approved",
            "--decided-by",
            "Reviewer",
            "--decided-at",
            NOW,
            "--rationale",
            "Says what is wanted.",
            "--expected-revision",
            "1",
        ],
    )

    assert result.exit_code == 0, result.output
    after = DAGManager.load(str(dag_file)).get_node(DEMO_INTENT_ID).intent
    assert after.approval.state == ApprovalState.APPROVED
    assert after.approval.approved_by == "Reviewer"
    assert [r.revision for r in after.revision_history] == [1, 2]
    assert after.revision_history[0] == before.revision_history[0]
    assert after.acceptance_criteria == before.acceptance_criteria
    assert after.provenance == before.provenance


def test_intent_decide_rejects_stale_revisions_repeats_and_naive_times(tmp_path):
    workspace = _project_with_node(tmp_path)
    dag_file = workspace / "intention-dag.yaml"
    runner = CliRunner()

    def decide(*extra, revision="1", at=NOW, state="rejected"):
        return runner.invoke(
            cli,
            [
                "intent",
                "decide",
                "--file",
                str(dag_file),
                "--node-id",
                DEMO_INTENT_ID,
                "--state",
                state,
                "--decided-by",
                "Reviewer",
                "--decided-at",
                at,
                "--rationale",
                "No.",
                "--expected-revision",
                revision,
                *extra,
            ],
        )

    assert decide(revision="2").exit_code == 1
    assert decide(at="2026-11-08T20:00:00").exit_code != 0
    assert decide().exit_code == 0
    repeated = decide(revision="2")
    assert repeated.exit_code == 1
    assert "already rejected" in repeated.output
    assert decide(state="review_required", revision="2").exit_code == 2


def test_decide_intent_file_refuses_non_decision_states(tmp_path):
    workspace = _project_with_node(tmp_path)

    with pytest.raises(IntentStoreError, match="approved or rejected"):
        decide_intent_file(
            workspace / "intention-dag.yaml",
            DEMO_INTENT_ID,
            state=ApprovalState.DRAFT,
            decided_by="Reviewer",
            decided_at=datetime(2026, 11, 8, tzinfo=timezone.utc),
            rationale="Back to draft.",
            expected_revision=1,
            generator_version="test",
        )


def _triage_decide(workspace, decisions, *, subject=None, classification=None):
    return CliRunner().invoke(
        cli,
        [
            "triage-decide",
            "--intention",
            str(workspace / "intention-dag.yaml"),
            "--reality",
            str(workspace / "reality-dag.yaml"),
            "--decisions",
            str(decisions),
            "--subject-key",
            subject or f"intent:{DEMO_INTENT_ID}",
            "--classification",
            classification or "missing_implementation",
            "--rationale",
            "Nothing implements it.",
            "--evidence",
            "src",
            "--decided-by",
            "Reviewer",
            "--decided-at",
            NOW,
        ],
    )


def test_triage_decide_records_a_digest_bound_decision_that_authorizes(tmp_path):
    workspace = _project_with_node(tmp_path, approve=True)
    decisions = workspace / "changes" / "decisions.json"

    result = _triage_decide(workspace, decisions)

    assert result.exit_code == 0, result.output
    assert "Implementation authorized: yes" in result.output
    recorded = json.loads(decisions.read_text(encoding="utf-8"))
    assert recorded["decisions"][0]["decided_by"] == "Reviewer"
    triage = CliRunner().invoke(
        cli,
        [
            "triage",
            "--intention",
            str(workspace / "intention-dag.yaml"),
            "--reality",
            str(workspace / "reality-dag.yaml"),
            "--decisions",
            str(decisions),
            "--format",
            "json",
        ],
    )
    assert triage.exit_code == 0, triage.output
    report = json.loads(triage.output)
    assert report["source"]["plan_digest"] == recorded["plan_digest"]
    assert report["summary"]["actionable_implementation"] == 1

    # Deciding the same subject again replaces its decision, not duplicates it.
    again = _triage_decide(
        workspace, decisions, classification="framework_tooling_drift"
    )
    assert again.exit_code == 0, again.output
    assert "Implementation authorized: no" in again.output
    assert len(json.loads(decisions.read_text(encoding="utf-8"))["decisions"]) == 1


def test_triage_decide_refuses_to_rebind_a_stale_file(tmp_path):
    workspace = _project_with_node(tmp_path, approve=True)
    decisions = workspace / "decisions.json"
    decisions.write_text(
        json.dumps({"schema_version": 1, "plan_digest": "0" * 64, "decisions": []}),
        encoding="utf-8",
    )

    result = _triage_decide(workspace, decisions)

    assert result.exit_code == 1
    assert "older plan digest" in result.output
    assert json.loads(decisions.read_text(encoding="utf-8"))["plan_digest"] == "0" * 64


def test_triage_decide_refuses_an_unknown_subject_and_writes_nothing(tmp_path):
    workspace = _project_with_node(tmp_path, approve=True)
    decisions = workspace / "decisions.json"

    result = _triage_decide(
        workspace, decisions, subject="intent:00000000-0000-4000-8000-000000000000"
    )

    assert result.exit_code == 1
    assert "unknown or inapplicable" in result.output
    assert not decisions.exists()


def test_work_order_carries_the_intent_and_keeps_approval_with_people(tmp_path):
    workspace = _project_with_node(tmp_path, approve=True)
    dag = DAGManager.load(str(workspace / "intention-dag.yaml"))
    task = {
        "description": "Canonical intent has no deterministic structural match.",
        "canonical_intent_id": DEMO_INTENT_ID,
    }

    order = orchestrator_loop.work_order(task, dag)

    assert order.startswith("Execute this task: Canonical intent")
    assert "Requirement: Token Verifier (component)" in order
    assert "TOKEN-AC1:" in order and "required evidence: test:token-verifier" in order
    assert "Stated as: API tokens must be compared in constant time" in order
    assert "Do not approve intent" in order


def test_work_order_without_an_intent_still_states_the_rules():
    order = orchestrator_loop.work_order({"description": "tidy up"})

    assert order.startswith("Execute this task: tidy up")
    assert "Requirement:" not in order
    assert "Never edit files under .aio-agentic-sdlc/" in order


def test_trace_explains_what_is_missing_in_plain_language(tmp_path):
    _project_with_node(tmp_path)

    trace = build_trace(tmp_path, DEMO_INTENT_ID)
    text = render_trace_markdown(trace)

    assert trace["done"] is False
    assert "**Status: not done yet.**" in text
    assert "review required, not approved" in text
    assert "no implementation has been linked to it yet" in text
    assert "### TOKEN-AC1: not met" in text
    assert "GUID" not in text.split("## What was wanted")[0]


def test_trace_command_writes_json_and_rejects_unknown_nodes(tmp_path):
    _project_with_node(tmp_path)
    runner = CliRunner()

    as_json = runner.invoke(
        cli,
        [
            "trace",
            "--project-path",
            str(tmp_path),
            "--intent-id",
            DEMO_INTENT_ID,
            "--format",
            "json",
        ],
    )
    assert as_json.exit_code == 0, as_json.output
    assert json.loads(as_json.output)["approval"]["state"] == "review_required"

    unknown = runner.invoke(
        cli,
        [
            "trace",
            "--project-path",
            str(tmp_path),
            "--intent-id",
            "00000000-0000-4000-8000-000000000000",
        ],
    )
    assert unknown.exit_code == 1
    assert "does not exist" in unknown.output


def test_trace_is_read_only(tmp_path):
    workspace = _project_with_node(tmp_path)
    before = {
        path.name: path.read_bytes()
        for path in workspace.iterdir()
        if path.is_file() and path.suffix in {".yaml", ".json"}
    }

    build_trace(tmp_path, DEMO_INTENT_ID)

    after = {
        path.name: path.read_bytes()
        for path in workspace.iterdir()
        if path.is_file() and path.suffix in {".yaml", ".json"}
    }
    assert after == before
    assert yaml.safe_load(before["intention-dag.yaml"])["nodes"]
