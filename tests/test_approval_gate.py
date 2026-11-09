"""The Approval Gate (owner decision 2026-11-09): completion is gated by default."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from aio_agentic_sdlc import approval_gate, core, orchestrator_loop
from aio_agentic_sdlc.config import save_config
from aio_agentic_sdlc.core import AWAITING_APPROVAL, BacklogOperationError

INTENT_ID = "11111111-1111-4111-8111-111111111111"
WHEN = datetime(2026, 11, 9, 13, 0, tzinfo=timezone.utc)


def _diff_task():
    return {
        "item_type": "Task",
        "impact": 3,
        "effort": 2,
        "category": "Reconciliation",
        "description": "implement the requirement",
        "status": "New",
        "blockers": [],
        "scores": {},
        "action": "investigate_intent",
        "canonical_intent_id": INTENT_ID,
        "evidence": {},
    }


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    core.add_item("seed", 1, 1, "Feature", "creates the workspace")
    core.remove_item("seed")
    with (
        patch("aio_agentic_sdlc.orchestrator_loop.DAGManager"),
        patch("aio_agentic_sdlc.orchestrator_loop.DiffingEngine") as engine,
        patch(
            "aio_agentic_sdlc.orchestrator_loop.authorized_subjects",
            return_value={f"intent:{INTENT_ID}"},
        ),
    ):
        diff = engine.return_value.calculate_diff

        def ingest(*tasks):
            diff.return_value = {
                "nodes": {f"task-{i}": t for i, t in enumerate(tasks)},
                "edges": [],
            }
            orchestrator_loop.ingest_diff()
            return core.load_backlog()["nodes"]

        yield ingest


def _approve(name="task-0", **overrides):
    arguments = {
        "approved_by": "Felix",
        "approved_at": WHEN,
        "rationale": "The evidence is recorded.",
        **overrides,
    }
    return approval_gate.approve_task(name, **arguments)


def test_gated_is_the_default_and_work_that_left_the_diff_waits(project):
    project(_diff_task())
    core.add_blocker("task-0", orchestrator_loop.AWAITING_EVIDENCE)

    nodes = project()

    item = nodes["task-0"]
    assert approval_gate.approval_mode() == "gated"
    assert item["status"] == "Blocked"
    assert item["blockers"] == [AWAITING_APPROVAL]
    assert item["resolution"] == "left the diff; awaiting approval"
    assert approval_gate.awaiting_approval() == ["task-0"]
    assert core.get_next_item(where=orchestrator_loop._is_authorized)[0] is None


def test_approval_completes_the_work_and_records_who(project):
    project(_diff_task())
    project()

    item = _approve()

    assert item["status"] == "Completed"
    assert item["approval"] == {
        "approved_by": "Felix",
        "approved_at": WHEN.isoformat(),
        "rationale": "The evidence is recorded.",
    }
    assert item["resolution"] == "left the diff; approved by Felix"
    # A later ingest keeps the approved completion.
    assert project()["task-0"]["status"] == "Completed"


def test_the_gate_cannot_be_bypassed_through_status_or_blockers(project):
    project(_diff_task())
    project()

    for attempt in (
        lambda: core.set_status("task-0", "Completed"),
        lambda: core.remove_blocker("task-0", AWAITING_APPROVAL),
        lambda: core.update_item("task-0", status="Completed"),
        lambda: core.update_item("task-0", blockers=""),
    ):
        with pytest.raises(BacklogOperationError, match="awaiting approval"):
            attempt()
    assert core.load_backlog()["nodes"]["task-0"]["status"] == "Blocked"


def test_only_waiting_work_can_be_approved_and_approval_needs_a_person(project):
    project(_diff_task())

    with pytest.raises(BacklogOperationError, match="not awaiting approval"):
        _approve()
    project()
    with pytest.raises(BacklogOperationError, match="approver and a rationale"):
        _approve(approved_by=" ")
    with pytest.raises(BacklogOperationError, match="time zone"):
        _approve(approved_at=datetime(2026, 11, 9, 13, 0))


def test_work_back_in_the_diff_before_approval_is_work_again(project):
    project(_diff_task())
    project()

    item = project(_diff_task())["task-0"]

    assert item["status"] == "New"
    assert AWAITING_APPROVAL not in item["blockers"]
    assert item["resolution"].startswith("reopened")


def test_bypass_completes_work_as_soon_as_it_leaves_the_diff(project):
    save_config({"approval_mode": "bypass"})
    project(_diff_task())

    item = project()["task-0"]

    assert item["status"] == "Completed"
    assert item["resolution"] == "left the diff"
    assert approval_gate.awaiting_approval() == []


def test_an_unknown_mode_fails_closed(project):
    save_config({"approval_mode": "sometimes"})

    with pytest.raises(BacklogOperationError, match="approval_mode"):
        project(_diff_task())
