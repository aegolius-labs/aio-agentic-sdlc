import json
import uuid

import pytest
from click.testing import CliRunner

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Edge, EdgeType, Metadata, Node, NodeType
from aio_agentic_sdlc.intent_consistency import (
    IntentConsistencyChecker,
    IntentConsistencyError,
    render_intent_consistency,
)
from aio_agentic_sdlc.intent_ir import IntentIR


def _intent(state="review_required", criterion="Observable outcome.", ambiguity=None):
    approval = {"state": state}
    if state == "approved":
        approval.update(
            {"approved_by": "Owner", "approved_at": "2026-10-15T10:00:00+00:00"}
        )
    return IntentIR.model_validate(
        {
            "provenance": [
                {
                    "source_type": "human_statement",
                    "reference": "test:consistency",
                    "statement": "Test intent.",
                }
            ],
            "ambiguities": [{"question": ambiguity}] if ambiguity else [],
            "confidence": 0.9,
            "acceptance_criteria": [
                {
                    "id": "AC1",
                    "statement": criterion,
                    "required_evidence": ["test:consistency"],
                }
            ],
            "revision_history": [
                {
                    "revision": 1,
                    "recorded_at": "2026-10-15T10:00:00+00:00",
                    "actor": "test",
                    "generator_version": "test/v1",
                    "summary": "Created.",
                }
            ],
            "responsible_agent": "test",
            "generator_version": "test/v1",
            "approval": approval,
        }
    )


def _node(name, node_type=NodeType.COMPONENT, description=None, **intent):
    return Node(
        id=str(uuid.uuid4()),
        type=node_type,
        name=name,
        description=description or f"{name} description.",
        intent=_intent(**intent),
    )


def _manager(nodes, edges=()):
    return DAGManager(Metadata(name="test", version="1"), list(nodes), list(edges))


def _checks(report):
    return [finding["check"] for finding in report["findings"]]


def test_consistent_dag_has_no_findings():
    system = _node("System", NodeType.SYSTEM)
    component = _node("Component")
    report = IntentConsistencyChecker(
        _manager(
            [system, component],
            [Edge(source=system.id, target=component.id, type=EdgeType.CONTAINS)],
        )
    ).analyze()

    assert report["findings"] == []
    assert report["summary"]["findings"] == 0
    assert report["limitations"]


def test_reports_duplicate_and_overlapping_intent():
    first = _node("Report Builder", description="Builds the report.")
    second = _node("report-builder", description="Different words.")
    third = _node("Other", description="Builds the report.")

    report = IntentConsistencyChecker(_manager([first, second, third])).analyze()

    assert sorted(_checks(report)) == ["duplicate_intent", "overlapping_intent"]
    duplicate = next(f for f in report["findings"] if f["check"] == "duplicate_intent")
    assert {node["id"] for node in duplicate["nodes"]} == {first.id, second.id}


def test_reports_inverted_and_ambiguous_hierarchy():
    component = _node("Parent Component")
    module = _node("Child Module", NodeType.MODULE)
    other = _node("Other Parent", NodeType.CONTAINER)

    report = IntentConsistencyChecker(
        _manager(
            [component, module, other],
            [
                Edge(source=component.id, target=module.id, type=EdgeType.CONTAINS),
                Edge(source=other.id, target=module.id, type=EdgeType.CONTAINS),
            ],
        )
    ).analyze()

    assert _checks(report) == ["multiple_parents", "hierarchy_inversion"]
    assert report["findings"][0]["severity"] == "error"


def test_reports_approval_contradictions():
    approved = _node("Approved", state="approved")
    rejected = _node("Rejected", state="rejected")
    rejected_parent = _node("Rejected Parent", NodeType.CONTAINER, state="rejected")
    approved_child = _node("Approved Child", state="approved")

    report = IntentConsistencyChecker(
        _manager(
            [approved, rejected, rejected_parent, approved_child],
            [
                Edge(source=approved.id, target=rejected.id, type=EdgeType.DEPENDS_ON),
                Edge(
                    source=rejected_parent.id,
                    target=approved_child.id,
                    type=EdgeType.CONTAINS,
                ),
            ],
        )
    ).analyze()

    assert _checks(report) == ["approval_contradiction", "approval_contradiction"]
    assert report["summary"]["by_severity"]["error"] == 2


def test_reports_open_ambiguity_and_restated_criteria():
    approved = _node("Approved", state="approved", ambiguity="Is this right?")
    restated = _node(
        "Restated",
        description="Does  the thing.",
        criterion="does the thing.",
    )

    report = IntentConsistencyChecker(_manager([approved, restated])).analyze()

    assert _checks(report) == [
        "approved_with_open_ambiguity",
        "criterion_restates_description",
    ]
    assert report["findings"][1]["evidence"] == {"criterion_ids": ["AC1"]}


def test_bounds_detail_but_keeps_totals():
    nodes = [_node(f"N{i}", description="Same.") for i in range(3)]
    nodes += [_node(f"Dup{i}", description=f"D{i}.") for i in range(2)]
    nodes += [_node("dup-0", description="X.")]

    report = IntentConsistencyChecker(_manager(nodes)).analyze(max_items=1)

    assert report["limit"] == {
        "max_items": 1,
        "total_items": 2,
        "returned_items": 1,
        "truncated": True,
    }
    assert "Showing 1 of 2 findings." in render_intent_consistency(report)
    with pytest.raises(IntentConsistencyError):
        IntentConsistencyChecker(_manager(nodes)).analyze(max_items=0)


def test_cli_is_read_only_and_strict_fails_only_on_errors(tmp_path):
    approved = _node("Approved", state="approved")
    rejected = _node("Rejected", state="rejected")
    path = tmp_path / "intention-dag.yaml"
    _manager([approved, rejected]).save(str(path))
    runner = CliRunner()

    clean = runner.invoke(cli, ["check-consistency", "--file", str(path), "--strict"])
    assert clean.exit_code == 0
    assert "Findings: 0" in clean.output

    _manager(
        [approved, rejected],
        [Edge(source=approved.id, target=rejected.id, type=EdgeType.CALLS)],
    ).save(str(path))
    before = path.read_bytes()

    advisory = runner.invoke(
        cli, ["check-consistency", "--file", str(path), "--format", "json"]
    )
    assert advisory.exit_code == 0
    assert json.loads(advisory.output)["summary"]["by_severity"]["error"] == 1

    strict = runner.invoke(cli, ["check-consistency", "--file", str(path), "--strict"])
    assert strict.exit_code == 1
    assert path.read_bytes() == before
