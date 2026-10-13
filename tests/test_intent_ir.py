from datetime import datetime, timezone

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Edge, EdgeType, Metadata, Node, NodeType
from aio_agentic_sdlc.intent_ir import (
    AcceptanceCriterion,
    Ambiguity,
    AmbiguityStatus,
    Approval,
    ApprovalState,
    IntentIR,
    IntentRevision,
    Provenance,
    ProvenanceType,
)

NODE_ID = "00000000-0000-0000-0000-0000000000a1"


def _intent_ir() -> IntentIR:
    return IntentIR(
        provenance=[
            Provenance(
                source_type=ProvenanceType.HUMAN_STATEMENT,
                reference="chat:turn-42",
                statement="Password reset requests must be rate limited.",
            )
        ],
        assumptions=["A shared rate-limit store is available."],
        ambiguities=[
            Ambiguity(
                question="Should administrators bypass the limit?",
                status=AmbiguityStatus.OPEN,
            )
        ],
        confidence=0.8,
        acceptance_criteria=[
            AcceptanceCriterion(
                id="AC-1",
                statement="The sixth request in one minute returns HTTP 429.",
                required_evidence=["integration-test:password-reset-rate-limit"],
            )
        ],
        revision_history=[
            IntentRevision(
                revision=1,
                recorded_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
                actor="sdlc_intake",
                generator_version="aio-agentic-sdlc/0.23",
                summary="Initial interpretation of the user request.",
            )
        ],
        responsible_agent="sdlc_intake",
        generator_version="aio-agentic-sdlc/0.23",
        approval=Approval(state=ApprovalState.REVIEW_REQUIRED),
    )


def test_intent_ir_round_trips_through_dag_yaml(tmp_path):
    manager = DAGManager(
        Metadata(name="Intent", version="1.0"),
        [
            Node(
                id=NODE_ID,
                type=NodeType.COMPONENT,
                name="Rate limiter",
                intent=_intent_ir(),
            )
        ],
        [],
    )
    path = tmp_path / "intention-dag.yaml"

    manager.save(str(path))
    loaded = DAGManager.load(str(path))

    assert loaded.get_node(NODE_ID).intent == _intent_ir()
    loaded.validate_intent_ir(require_all=True)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("provenance", []),
        ("acceptance_criteria", []),
        ("revision_history", []),
        ("confidence", -0.1),
        ("confidence", 1.1),
    ],
)
def test_intent_ir_rejects_incomplete_or_invalid_core_fields(field, value):
    data = _intent_ir().model_dump()
    data[field] = value

    with pytest.raises(ValidationError):
        IntentIR.model_validate(data)


def test_intent_ir_rejects_non_increasing_revision_history():
    data = _intent_ir().model_dump()
    duplicate = data["revision_history"][0].copy()
    data["revision_history"].append(duplicate)

    with pytest.raises(ValidationError, match="strictly increasing"):
        IntentIR.model_validate(data)


def test_intent_revision_requires_timezone_aware_timestamp():
    with pytest.raises(ValidationError, match="timezone-aware"):
        IntentRevision(
            revision=1,
            recorded_at=datetime(2026, 7, 23),
            actor="sdlc_intake",
            generator_version="aio-agentic-sdlc/0.23",
            summary="Naive timestamps are not auditable across hosts.",
        )


def test_intent_ir_rejects_duplicate_acceptance_criterion_ids():
    data = _intent_ir().model_dump()
    duplicate = data["acceptance_criteria"][0].copy()
    duplicate["statement"] = "A separate condition with a reused identifier."
    data["acceptance_criteria"].append(duplicate)

    with pytest.raises(ValidationError, match="criterion IDs must be unique"):
        IntentIR.model_validate(data)


def test_acceptance_criterion_rejects_blank_evidence_reference():
    with pytest.raises(ValidationError):
        AcceptanceCriterion(
            id="AC-1",
            statement="The condition is observable.",
            required_evidence=["   "],
        )


def test_resolved_ambiguity_requires_resolution():
    with pytest.raises(ValidationError, match="resolution"):
        Ambiguity(question="Which store?", status=AmbiguityStatus.RESOLVED)


def test_approved_intent_requires_approval_audit_fields():
    with pytest.raises(ValidationError, match="approved_by"):
        Approval(state=ApprovalState.APPROVED)


def test_approved_intent_requires_timezone_aware_approval_timestamp():
    with pytest.raises(ValidationError, match="timezone-aware"):
        Approval(
            state=ApprovalState.APPROVED,
            approved_by="product-owner",
            approved_at=datetime(2026, 7, 23),
        )


def test_strict_intent_validation_reports_nodes_without_intent():
    manager = DAGManager(
        Metadata(name="Legacy", version="1.0"),
        [Node(id=NODE_ID, type=NodeType.COMPONENT, name="Legacy node")],
        [],
    )

    with pytest.raises(ValueError, match=NODE_ID):
        manager.validate_intent_ir(require_all=True)


def test_node_updates_revalidate_intent_ir():
    manager = DAGManager(
        Metadata(name="Intent", version="1.0"),
        [
            Node(
                id=NODE_ID,
                type=NodeType.COMPONENT,
                name="Rate limiter",
                intent=_intent_ir(),
            )
        ],
        [],
    )
    invalid_intent = _intent_ir().model_dump()
    invalid_intent["confidence"] = 2.0

    with pytest.raises(ValidationError):
        manager.update_node(NODE_ID, intent=invalid_intent)


def test_intent_summary_is_reviewable_without_raw_yaml():
    manager = DAGManager(
        Metadata(name="Intent", version="1.0"),
        [
            Node(
                id=NODE_ID,
                type=NodeType.COMPONENT,
                name="Rate limiter",
                intent=_intent_ir(),
            )
        ],
        [],
    )

    summary = manager.render_intent_summary()

    assert "Rate limiter" in summary
    assert "chat:turn-42" in summary
    assert "Password reset requests must be rate limited." in summary
    assert "AC-1" in summary
    assert "integration-test:password-reset-rate-limit" in summary
    assert "Should administrators bypass the limit?" in summary
    assert "review_required" in summary
    assert "0.80" in summary
    assert "nodes:" not in summary


def test_intent_cli_validates_and_summarizes(tmp_path):
    manager = DAGManager(
        Metadata(name="Intent", version="1.0"),
        [
            Node(
                id=NODE_ID,
                type=NodeType.COMPONENT,
                name="Rate limiter",
                intent=_intent_ir(),
            )
        ],
        [],
    )
    path = tmp_path / "intention-dag.yaml"
    manager.save(str(path))
    runner = CliRunner()

    validate_result = runner.invoke(cli, ["validate-intent", "--file", str(path)])
    summary_result = runner.invoke(cli, ["intent-summary", "--file", str(path)])

    assert validate_result.exit_code == 0
    assert "Intent IR is valid" in validate_result.output
    assert summary_result.exit_code == 0
    assert "Rate limiter" in summary_result.output


OTHER_ID = "00000000-0000-0000-0000-0000000000a2"


def _manager_with_intent(state: ApprovalState) -> DAGManager:
    approval = (
        Approval(
            state=state,
            approved_by="Felix",
            approved_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
        )
        if state == ApprovalState.APPROVED
        else Approval(state=state)
    )
    intent = _intent_ir().model_copy(update={"approval": approval})
    node = Node(id=NODE_ID, type=NodeType.COMPONENT, name="Limiter", intent=intent)
    other = Node(id=OTHER_ID, type=NodeType.COMPONENT, name="Store")
    edge = Edge(source=NODE_ID, target=OTHER_ID, type=EdgeType.DEPENDS_ON)
    return DAGManager(Metadata(name="Test", version="1.0"), [node, other], [edge])


@pytest.mark.parametrize("state", list(ApprovalState))
def test_no_node_carrying_intent_can_be_deleted(state):
    manager = _manager_with_intent(state)
    with pytest.raises(ValueError, match="cannot be deleted"):
        manager.remove_node(NODE_ID)
    assert NODE_ID in manager.nodes


def test_deleting_a_plain_node_cannot_cascade_into_an_approved_node():
    manager = _manager_with_intent(ApprovalState.APPROVED)
    with pytest.raises(ValueError, match="frozen"):
        manager.remove_node(OTHER_ID)
    assert OTHER_ID in manager.nodes
    assert len(manager.edges) == 1


def test_plain_nodes_are_still_removable():
    manager = _manager_with_intent(ApprovalState.REVIEW_REQUIRED)
    manager.remove_node(OTHER_ID)
    assert OTHER_ID not in manager.nodes
    assert manager.edges == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: m.update_node(NODE_ID, name="Renamed"),
        lambda m: m.update_node(NODE_ID, description="Rewritten"),
        lambda m: m.remove_edge(NODE_ID, OTHER_ID, EdgeType.DEPENDS_ON),
        lambda m: m.add_edge(
            Edge(source=OTHER_ID, target=NODE_ID, type=EdgeType.CALLS)
        ),
    ],
    ids=["rename", "describe", "remove-edge", "add-edge"],
)
def test_structure_of_an_approved_node_is_frozen(mutate):
    manager = _manager_with_intent(ApprovalState.APPROVED)
    before = (manager.nodes[NODE_ID], list(manager.edges))
    with pytest.raises(ValueError, match="frozen"):
        mutate(manager)
    assert (manager.nodes[NODE_ID], manager.edges) == before


def test_intent_only_updates_still_reach_an_approved_node():
    manager = _manager_with_intent(ApprovalState.APPROVED)
    reopened = manager.nodes[NODE_ID].intent.model_copy(
        update={"approval": Approval(state=ApprovalState.REVIEW_REQUIRED)}
    )
    manager.update_node(NODE_ID, intent=reopened)
    manager.update_node(NODE_ID, name="Renamed")
    assert manager.nodes[NODE_ID].name == "Renamed"


def test_cli_node_remove_leaves_intent_untouched(tmp_path):
    path = tmp_path / "intention-dag.yaml"
    _manager_with_intent(ApprovalState.REJECTED).save(str(path))
    before = path.read_bytes()

    result = CliRunner().invoke(
        cli, ["node", "remove", "--file", str(path), "--id", NODE_ID]
    )

    assert result.exit_code == 1
    assert "intent set" in result.output
    assert path.read_bytes() == before
