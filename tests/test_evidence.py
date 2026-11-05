import json
import uuid

import pytest
from click.testing import CliRunner
from pydantic import ValidationError

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Metadata, Node, NodeType
from aio_agentic_sdlc.evidence import (
    EvidenceEvaluator,
    EvidenceLedger,
    EvidenceLevel,
    EvidenceRecord,
    load_evidence_ledger,
    record_evidence,
    required_level,
)
from aio_agentic_sdlc.intent_ir import IntentIR
from aio_agentic_sdlc.reconciliation import ReconciliationEngine

NOW = "2026-11-05T19:00:00+00:00"


def _node(node_id=None, references=("test:widget-renders",)):
    node_id = node_id or str(uuid.uuid4())
    intent = IntentIR.model_validate(
        {
            "provenance": [
                {
                    "source_type": "human_statement",
                    "reference": "test:evidence",
                    "statement": "Test intent.",
                }
            ],
            "confidence": 0.9,
            "acceptance_criteria": [
                {
                    "id": "AC1",
                    "statement": "The widget renders.",
                    "required_evidence": [
                        f"reconciliation:intent:{node_id}",
                        *references,
                    ],
                }
            ],
            "revision_history": [
                {
                    "revision": 1,
                    "recorded_at": NOW,
                    "actor": "test",
                    "generator_version": "test/v1",
                    "summary": "Created.",
                }
            ],
            "responsible_agent": "test",
            "generator_version": "test/v1",
            "approval": {
                "state": "approved",
                "approved_by": "Owner",
                "approved_at": NOW,
            },
        }
    )
    return Node(
        id=node_id,
        type=NodeType.COMPONENT,
        name="Widget",
        description="Widget.",
        intent=intent,
    )


def _record(node, reference="test:widget-renders", level="tested", **overrides):
    payload = {
        "intent_id": node.id,
        "criterion_id": "AC1",
        "reference": reference,
        "level": level,
        "locator": "tests/test_widget.py::test_renders",
        "summary": "The widget test passes.",
        "recorded_by": "test",
        "recorded_at": NOW,
    }
    payload.update(overrides)
    return EvidenceRecord.model_validate(payload)


def _manager(*nodes):
    return DAGManager(Metadata(name="test", version="1"), list(nodes), [])


def test_evidence_level_state_machine():
    assert [level.value for level in EvidenceLevel] == [
        "declared",
        "mapped",
        "structural",
        "tested",
        "behaviorally_verified",
        "approved",
    ]
    assert required_level("reconciliation:intent:x") == EvidenceLevel.MAPPED
    assert required_level("test:x") == EvidenceLevel.TESTED
    assert required_level("demo:x") == EvidenceLevel.BEHAVIORALLY_VERIFIED
    assert required_level("review:x") == EvidenceLevel.APPROVED
    assert required_level("schema:x") == EvidenceLevel.STRUCTURAL

    node = _node()
    no_records = EvidenceEvaluator(EvidenceLedger())
    declared = no_records.evaluate(node, mapped=False)
    assert declared["level"] == "declared"
    assert declared["complete"] is False

    mapped = no_records.evaluate(node, mapped=True)
    references = mapped["criteria"][0]["references"]
    assert [r["satisfied"] for r in references] == [True, False]
    assert mapped["unverified_criteria"] == ["AC1"]

    structural_only = EvidenceEvaluator(
        EvidenceLedger(records=[_record(node, level="structural")])
    ).evaluate(node, mapped=True)
    assert structural_only["complete"] is False

    tested = EvidenceEvaluator(EvidenceLedger(records=[_record(node)])).evaluate(
        node, mapped=True
    )
    assert tested["complete"] is True
    assert tested["level"] == "mapped"
    assert tested["criteria"][0]["references"][1]["supporting"][0]["level"] == (
        "tested"
    )

    unmapped = EvidenceEvaluator(EvidenceLedger(records=[_record(node)])).evaluate(
        node, mapped=False
    )
    assert unmapped["complete"] is False


def test_records_reject_derived_levels_and_unaudited_approval():
    node = _node()
    for level in ("declared", "mapped"):
        with pytest.raises(ValidationError, match="derived"):
            _record(node, level=level)
    with pytest.raises(ValidationError, match="approved_by"):
        _record(node, level="approved")
    with pytest.raises(ValidationError, match="only valid"):
        _record(node, approved_by="Owner")
    with pytest.raises(ValidationError, match="canonical"):
        _record(node, intent_id=node.id.upper())
    assert _record(node, level="approved", approved_by="Owner").approved_by == "Owner"


def test_missing_locator_does_not_count(tmp_path):
    node = _node()
    evaluator = EvidenceEvaluator(
        EvidenceLedger(records=[_record(node)]), project_root=tmp_path
    )
    result = evaluator.evaluate(node, mapped=True)
    assert result["complete"] is False
    assert result["records_with_missing_locator"] == 1

    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_widget.py").write_text("")
    assert evaluator.evaluate(node, mapped=True)["complete"] is True


def test_record_evidence_binds_to_existing_criteria(tmp_path):
    node = _node()
    intention = _manager(node)
    ledger = tmp_path / "evidence.json"

    assert record_evidence(ledger, intention, _record(node)) == 1
    assert load_evidence_ledger(ledger).records[0].level == EvidenceLevel.TESTED
    with pytest.raises(ValueError, match="already has"):
        record_evidence(ledger, intention, _record(node))
    with pytest.raises(ValueError, match="does not require"):
        record_evidence(ledger, intention, _record(node, reference="test:other"))
    with pytest.raises(ValueError, match="no acceptance criterion"):
        record_evidence(ledger, intention, _record(node, criterion_id="AC9"))
    with pytest.raises(ValueError, match="locator does not exist"):
        record_evidence(
            ledger,
            intention,
            _record(node, level="behaviorally_verified"),
            project_root=tmp_path,
        )
    assert len(load_evidence_ledger(ledger).records) == 1


def test_reconciliation_evidence_report():
    node = _node()
    unbuilt = _node(references=("demo:widget",))
    reality = _manager(_node(node.id))
    ledger = EvidenceLedger(
        records=[
            _record(node, level="structural"),
            _record(node, criterion_id="AC2"),
        ]
    )

    report = ReconciliationEngine(
        _manager(node, unbuilt), reality, evidence=EvidenceEvaluator(ledger)
    ).analyze()

    by_id = {item["intent"]["id"]: item for item in report["items"][:2]}
    confirmed = by_id[node.id]
    assert confirmed["classification"] == "confirmed"
    assert confirmed["acceptance"]["complete"] is False
    assert confirmed["acceptance"]["unverified_criteria"] == ["AC1"]
    cited = confirmed["acceptance"]["criteria"][0]["references"][1]
    assert cited["supporting"][0]["level"] == "structural"
    assert by_id[unbuilt.id]["acceptance"]["level"] == "declared"
    assert report["acceptance"]["complete"] == 0
    assert report["acceptance"]["incomplete"] == 2
    assert report["acceptance"]["orphaned_records"] == 1
    assert "AC2" in report["acceptance"]["orphaned"][0]["reason"]

    plain = ReconciliationEngine(_manager(node, unbuilt), reality).analyze()
    assert "acceptance" not in plain
    assert [i["classification"] for i in plain["items"][:2]] == [
        i["classification"] for i in report["items"][:2]
    ]


def test_cli_records_and_reports_evidence(tmp_path):
    node = _node()
    workspace = tmp_path / ".aio-agentic-sdlc"
    workspace.mkdir()
    _manager(node).save(str(workspace / "intention-dag.yaml"))
    _manager(_node(node.id)).save(str(workspace / "reality-dag.yaml"))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_widget.py").write_text("")
    runner = CliRunner()

    recorded = runner.invoke(
        cli,
        [
            "evidence",
            "record",
            "--project-path",
            str(tmp_path),
            "--intent-id",
            node.id,
            "--criterion-id",
            "AC1",
            "--reference",
            "test:widget-renders",
            "--level",
            "tested",
            "--locator",
            "tests/test_widget.py::test_renders",
            "--summary",
            "The widget test passes.",
            "--recorded-by",
            "test",
            "--recorded-at",
            NOW,
        ],
    )
    assert recorded.exit_code == 0, recorded.output
    intention_before = (workspace / "intention-dag.yaml").read_bytes()

    result = runner.invoke(
        cli,
        [
            "reconcile",
            "--intention",
            str(workspace / "intention-dag.yaml"),
            "--reality",
            str(workspace / "reality-dag.yaml"),
            "--evidence",
            str(workspace / "evidence.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["items"][0]["acceptance"]["complete"] is True
    assert report["acceptance"]["complete"] == 1
    assert (workspace / "intention-dag.yaml").read_bytes() == intention_before
