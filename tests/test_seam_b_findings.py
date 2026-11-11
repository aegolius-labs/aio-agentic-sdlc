"""Seam B: agentic-qa-kit findings are evidence; this framework chooses disposition.

`tests/fixtures/seam-b/findings.json` pins the `aqk-findings` contract,
version 1. The kit will hold a byte-identical copy and assert that its export
emits exactly this shape. The two repositories do not import each other, so the
fixture is the contract.

A finding has two dispositions. `revert-node` reopens the acceptance of an
approved Intention node, so the diff regenerates the work; it needs a named
approver and never edits the Intention DAG. `bug-handoff` is the only choice for
a finding with no GUID or an unknown one, which is reported and never guessed.

If the fixture test fails, the seam moved. Update both fixtures together and say
so in the change; do not quietly relax the assertion.
"""

import copy
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.diffing_engine import DiffingEngine
from aio_agentic_sdlc.drift_triage import DriftTriageEngine
from aio_agentic_sdlc.evidence import (
    EvidenceError,
    EvidenceEvaluator,
    EvidenceLedger,
    load_evidence_ledger,
    record_evidence,
)
from aio_agentic_sdlc.intent_ir import ApprovalState
from aio_agentic_sdlc.qa_findings import (
    FindingsError,
    findings_digest,
    load_findings,
    propose_dispositions,
    record_disposition,
    validate_findings,
)
from tests.test_evidence import _manager, _node, _record

FIXTURE = Path(__file__).parent / "fixtures" / "seam-b" / "findings.json"
MAPPED_GUID = "3b241101-e2bb-4255-8caf-4136c566a962"
BEFORE = "2026-11-05T19:00:00+00:00"
APPROVED = "2026-11-11T16:00:00+00:00"
AFTER = "2026-11-12T09:00:00+00:00"


def _document() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _resealed(document: dict) -> dict:
    document["digest"] = findings_digest(document)
    return document


def _revert(ledger, intention, **overrides):
    arguments = {
        "session_id": "qa-example",
        "finding_id": "finding-rounding",
        "disposition": "revert-node",
        "criterion_id": "AC1",
        "reason": "Rounding is inside the node's accepted intent.",
        "recorded_by": "sdlc_qa",
        "recorded_at": APPROVED,
        "approved_by": "Owner",
    }
    arguments.update(overrides)
    return record_disposition(ledger, _document(), intention, **arguments)


# The contract


def test_the_fixture_honours_contract_version_1():
    document = load_findings(FIXTURE)

    assert document["contract"] == "aqk-findings"
    assert document["contract_version"] == 1
    assert findings_digest(document) == document["digest"]
    for finding in document["findings"]:
        assert finding["status"] == "confirmed"
        assert finding["source"] == (
            f"agentic-qa-kit:session={finding['session_id']};"
            f"finding={finding['finding_id']}"
        )


def test_an_unknown_contract_version_is_rejected():
    document = _resealed({**_document(), "contract_version": 2})

    with pytest.raises(FindingsError, match="contract_version 2"):
        validate_findings(document)


def test_another_contract_is_rejected():
    document = _resealed({**_document(), "contract": "abk-observed-state"})

    with pytest.raises(FindingsError, match="Not an aqk-findings document"):
        validate_findings(document)


def test_an_additive_field_keeps_the_version():
    document = _document()
    document["findings"][0]["charter_id"] = "charter-calculation"
    document["findings"][0]["session"]["objective"] = "added later"
    document["ledger_root"] = ".agentic-qa/sessions"

    validate_findings(_resealed(document))


def test_a_removed_field_is_rejected():
    document = _document()
    del document["findings"][0]["oracle"]

    with pytest.raises(FindingsError, match="missing oracle"):
        validate_findings(_resealed(document))


def test_an_edited_document_fails_its_digest():
    document = _document()
    document["findings"][0]["severity"] = "low"

    with pytest.raises(FindingsError, match="digest"):
        validate_findings(document)


@pytest.mark.parametrize("status", ["candidate", "not-reproduced", "dismissed"])
def test_only_confirmed_findings_are_eligible(status):
    document = _document()
    document["findings"][0]["status"] = status

    with pytest.raises(FindingsError, match="only confirmed findings"):
        validate_findings(_resealed(document))


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("reproduction", "steps"), [], "reproduction steps"),
        (("reproduction", "reproducibility"), "not-reproduced", "reproducibility"),
        (("evidence",), [], "evidence"),
        (("acceptance_criteria",), [], "acceptance_criteria"),
        (("oracle",), " ", "oracle"),
    ],
)
def test_a_confirmed_finding_carries_its_reproduction_and_evidence(
    path, value, message
):
    document = _document()
    target = document["findings"][0]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(FindingsError, match=message):
        validate_findings(_resealed(document))


def test_a_broken_session_chain_is_rejected():
    document = _document()
    document["findings"][0]["session"]["integrity"] = "broken"

    with pytest.raises(FindingsError, match="integrity"):
        validate_findings(_resealed(document))


def test_the_source_must_name_the_session_and_finding():
    document = _document()
    document["findings"][0]["source"] = "agentic-qa-kit:session=other;finding=x"

    with pytest.raises(FindingsError, match="source"):
        validate_findings(_resealed(document))


def test_a_finding_appears_once():
    document = _document()
    document["findings"].append(copy.deepcopy(document["findings"][0]))

    with pytest.raises(FindingsError, match="more than once"):
        validate_findings(_resealed(document))


@pytest.mark.parametrize("guid", [MAPPED_GUID.upper(), "not-a-guid", 7])
def test_the_intent_guid_is_lowercase_canonical_or_null(guid):
    document = _document()
    document["findings"][0]["intent_guid"] = guid

    with pytest.raises(FindingsError, match="intent_guid"):
        validate_findings(_resealed(document))


# Proposals


def test_a_finding_on_an_approved_node_proposes_revert_node():
    for stored in (MAPPED_GUID, MAPPED_GUID.upper()):
        node = _node(stored)
        report = propose_dispositions(_document(), _manager(node))

        rounding, encoding = report["findings"]
        assert rounding["finding_id"] == "finding-rounding"
        assert rounding["proposed_disposition"] == "revert-node"
        assert rounding["reason_code"] == "inside_accepted_intent"
        assert rounding["intent_id"] == stored
        assert rounding["criteria"] == ["AC1"]
        assert "Widget" in rounding["reason"]
        assert encoding["proposed_disposition"] == "bug-handoff"
        assert report["authority"] == "evidence"
        assert report["summary"] == {
            "findings": 2,
            "revert-node": 1,
            "bug-handoff": 1,
            "recorded": 0,
        }


def test_findings_without_a_resolvable_guid_are_handed_off_not_guessed():
    document = _document()
    # Same title and id as a node would not help: matching is by GUID only.
    document["findings"][0]["intent_guid"] = "00000000-0000-4000-8000-000000000000"
    node = _node(MAPPED_GUID)
    node.name = document["findings"][0]["title"]

    report = propose_dispositions(_resealed(document), _manager(node))

    unknown, missing = report["findings"]
    assert unknown["proposed_disposition"] == "bug-handoff"
    assert unknown["reason_code"] == "guid_not_in_intention"
    assert unknown["intent_id"] is None
    assert missing["proposed_disposition"] == "bug-handoff"
    assert missing["reason_code"] == "no_guid"


@pytest.mark.parametrize(
    "state",
    [ApprovalState.REVIEW_REQUIRED, ApprovalState.REJECTED, ApprovalState.DRAFT],
)
def test_a_node_without_approved_intent_is_outside_accepted_intent(state):
    node = _node(MAPPED_GUID)
    node.intent.approval.state = state
    node.intent.approval.approved_by = None
    node.intent.approval.approved_at = None

    rounding, _ = propose_dispositions(_document(), _manager(node))["findings"]

    assert rounding["proposed_disposition"] == "bug-handoff"
    assert rounding["reason_code"] == "intent_not_approved"
    assert rounding["intent_id"] == MAPPED_GUID


def test_proposing_is_read_only(tmp_path):
    node = _node(MAPPED_GUID)
    ledger = tmp_path / "evidence.json"

    propose_dispositions(
        _document(), _manager(node), ledger=load_evidence_ledger(ledger)
    )

    assert not ledger.exists()


# Recording


def test_revert_node_is_recorded_with_its_reason_and_approver(tmp_path):
    node = _node(MAPPED_GUID)
    intention = _manager(node)
    ledger = tmp_path / "evidence.json"
    before = intention.nodes[node.id].model_dump_json()

    recorded = _revert(ledger, intention)

    stored = load_evidence_ledger(ledger).qa_dispositions
    assert stored == [recorded]
    assert recorded.disposition == "revert-node"
    assert recorded.proposed_disposition == "revert-node"
    assert recorded.intent_id == MAPPED_GUID
    assert recorded.criterion_id == "AC1"
    assert recorded.approved_by == "Owner"
    assert recorded.reason.startswith("Rounding")
    assert recorded.findings_digest == _document()["digest"]
    assert (
        recorded.source == "agentic-qa-kit:session=qa-example;finding=finding-rounding"
    )
    # Evidence never edits intent.
    assert intention.nodes[node.id].model_dump_json() == before
    assert intention.nodes[node.id].intent.approval.state == ApprovalState.APPROVED

    report = propose_dispositions(
        _document(), intention, ledger=load_evidence_ledger(ledger)
    )
    assert report["findings"][0]["recorded"]["disposition"] == "revert-node"
    assert report["summary"]["recorded"] == 1


def test_revert_node_needs_a_named_approver(tmp_path):
    intention = _manager(_node(MAPPED_GUID))

    with pytest.raises(ValueError, match="approved_by"):
        _revert(tmp_path / "evidence.json", intention, approved_by=None)
    assert not (tmp_path / "evidence.json").exists()


def test_revert_node_needs_an_existing_criterion(tmp_path):
    intention = _manager(_node(MAPPED_GUID))

    with pytest.raises(ValueError, match="criterion"):
        _revert(tmp_path / "evidence.json", intention, criterion_id=None)
    with pytest.raises(EvidenceError, match="no acceptance criterion AC9"):
        _revert(tmp_path / "evidence.json", intention, criterion_id="AC9")


def test_revert_node_is_refused_outside_accepted_intent(tmp_path):
    unapproved = _node(MAPPED_GUID)
    unapproved.intent.approval.state = ApprovalState.REVIEW_REQUIRED
    unapproved.intent.approval.approved_by = None
    unapproved.intent.approval.approved_at = None

    with pytest.raises(FindingsError, match="revert-node"):
        _revert(tmp_path / "evidence.json", _manager(unapproved))
    with pytest.raises(FindingsError, match="revert-node"):
        _revert(
            tmp_path / "evidence.json",
            _manager(_node(MAPPED_GUID)),
            finding_id="finding-export-encoding",
        )


def test_bug_handoff_is_recorded_for_an_unmapped_finding(tmp_path):
    ledger = tmp_path / "evidence.json"

    recorded = record_disposition(
        ledger,
        _document(),
        _manager(_node(MAPPED_GUID)),
        session_id="qa-example",
        finding_id="finding-export-encoding",
        disposition="bug-handoff",
        reason="No Intention node models CSV export.",
        recorded_by="sdlc_qa",
        recorded_at=APPROVED,
    )

    assert recorded.disposition == "bug-handoff"
    assert recorded.intent_id is None
    assert recorded.approved_by is None


def test_overriding_the_proposal_needs_a_named_approver(tmp_path):
    ledger = tmp_path / "evidence.json"
    intention = _manager(_node(MAPPED_GUID))
    arguments = {
        "session_id": "qa-example",
        "finding_id": "finding-rounding",
        "disposition": "bug-handoff",
        "reason": "The session named this node, but the defect is in a caller.",
        "recorded_by": "sdlc_qa",
        "recorded_at": APPROVED,
    }

    with pytest.raises(ValueError, match="approved_by"):
        record_disposition(ledger, _document(), intention, **arguments)

    recorded = record_disposition(
        ledger, _document(), intention, approved_by="Owner", **arguments
    )
    assert recorded.proposed_disposition == "revert-node"
    assert recorded.disposition == "bug-handoff"


def test_a_finding_takes_exactly_one_disposition(tmp_path):
    ledger = tmp_path / "evidence.json"
    intention = _manager(_node(MAPPED_GUID))
    _revert(ledger, intention)

    with pytest.raises(EvidenceError, match="already has disposition"):
        _revert(ledger, intention, reason="Again.")
    assert len(load_evidence_ledger(ledger).qa_dispositions) == 1


def test_a_ledger_without_dispositions_keeps_its_bytes_and_digest(tmp_path):
    node = _node(MAPPED_GUID)
    ledger_path = tmp_path / "evidence.json"
    record_evidence(ledger_path, _manager(node), _record(node))

    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert set(payload) == {"schema_version", "records"}
    assert "qa_dispositions" not in load_evidence_ledger(ledger_path).digest_payload()


# Reopening the work


def _plan(node, ledger):
    return DiffingEngine(
        _manager(node), _manager(_node(node.id)), evidence=EvidenceEvaluator(ledger)
    ).calculate_diff()


def test_revert_node_puts_a_complete_node_back_in_the_diff(tmp_path):
    node = _node(MAPPED_GUID)
    ledger_path = tmp_path / "evidence.json"
    record_evidence(ledger_path, _manager(node), _record(node, recorded_at=BEFORE))
    assert _plan(node, load_evidence_ledger(ledger_path))["nodes"] == {}

    _revert(ledger_path, _manager(node))
    ledger = load_evidence_ledger(ledger_path)

    acceptance = EvidenceEvaluator(ledger).evaluate(node, mapped=True)
    assert acceptance["complete"] is False
    assert acceptance["unverified_criteria"] == ["AC1"]
    assert acceptance["criteria"][0]["reopened_by"] == [
        "agentic-qa-kit:session=qa-example;finding=finding-rounding"
    ]
    plan = _plan(node, ledger)
    ((name, task),) = plan["nodes"].items()
    assert task["action"] == "verify_acceptance"
    assert task["evidence"]["unverified_criteria"] == ["AC1"]
    assert node.id in name

    triage = DriftTriageEngine(
        _manager(node), _manager(_node(node.id)), evidence=EvidenceEvaluator(ledger)
    ).analyze()
    (item,) = triage["items"]
    assert item["classification"] == "acceptance_evidence_required"
    assert item["implementation_authorized"] is True


def test_the_reopening_ends_only_with_evidence_recorded_after_it(tmp_path):
    node = _node(MAPPED_GUID)
    ledger_path = tmp_path / "evidence.json"
    intention = _manager(node)
    _revert(ledger_path, intention)

    # Evidence from before the finding no longer counts for the criterion.
    record_evidence(ledger_path, intention, _record(node, recorded_at=BEFORE))
    assert _plan(node, load_evidence_ledger(ledger_path))["nodes"] != {}

    # A self-reconciliation reference needs fresh evidence too: the mapping
    # existed when the defect was found.
    record_evidence(ledger_path, intention, _record(node, recorded_at=AFTER))
    still_open = EvidenceEvaluator(load_evidence_ledger(ledger_path)).evaluate(
        node, mapped=True
    )
    assert still_open["complete"] is False
    record_evidence(
        ledger_path,
        intention,
        _record(
            node,
            reference=f"reconciliation:intent:{node.id}",
            level="structural",
            recorded_at=AFTER,
            summary="The fix is mapped again.",
        ),
    )

    assert _plan(node, load_evidence_ledger(ledger_path))["nodes"] == {}


def test_bug_handoff_does_not_reopen_any_node(tmp_path):
    node = _node(MAPPED_GUID)
    ledger_path = tmp_path / "evidence.json"
    intention = _manager(node)
    record_evidence(ledger_path, intention, _record(node, recorded_at=BEFORE))
    record_disposition(
        ledger_path,
        _document(),
        intention,
        session_id="qa-example",
        finding_id="finding-rounding",
        disposition="bug-handoff",
        reason="The defect is in a caller outside this node.",
        recorded_by="sdlc_qa",
        recorded_at=APPROVED,
        approved_by="Owner",
    )

    assert _plan(node, load_evidence_ledger(ledger_path))["nodes"] == {}


def test_dispositions_change_the_triage_digest(tmp_path):
    node = _node(MAPPED_GUID)
    ledger_path = tmp_path / "evidence.json"
    intention, reality = _manager(node), _manager(_node(node.id))

    def digest():
        return DriftTriageEngine(
            intention,
            reality,
            evidence=EvidenceEvaluator(load_evidence_ledger(ledger_path)),
        ).source_identity()["plan_digest"]

    empty = DriftTriageEngine(
        intention, reality, evidence=EvidenceEvaluator(EvidenceLedger())
    ).source_identity()["plan_digest"]
    assert digest() == empty
    _revert(ledger_path, intention)
    assert digest() != empty


# The dag-tool surface


def _workspace(tmp_path, node):
    workspace = tmp_path / ".aio-agentic-sdlc"
    workspace.mkdir()
    _manager(node).save(str(workspace / "intention-dag.yaml"))
    _manager(_node(node.id)).save(str(workspace / "reality-dag.yaml"))
    return workspace


def test_cli_proposes_then_records_a_disposition(tmp_path):
    node = _node(MAPPED_GUID)
    workspace = _workspace(tmp_path, node)
    intention_before = (workspace / "intention-dag.yaml").read_bytes()
    runner = CliRunner()

    proposed = runner.invoke(
        cli,
        [
            "qa",
            "propose",
            "--project-path",
            str(tmp_path),
            "--findings",
            str(FIXTURE),
            "--format",
            "json",
        ],
    )
    assert proposed.exit_code == 0, proposed.output
    report = json.loads(proposed.output)
    assert [f["proposed_disposition"] for f in report["findings"]] == [
        "revert-node",
        "bug-handoff",
    ]
    assert not (workspace / "evidence.json").exists()

    human = runner.invoke(
        cli,
        ["qa", "propose", "--project-path", str(tmp_path), "--findings", str(FIXTURE)],
    )
    assert human.exit_code == 0, human.output
    assert "revert-node" in human.output and "bug-handoff" in human.output

    recorded = runner.invoke(
        cli,
        [
            "qa",
            "record",
            "--project-path",
            str(tmp_path),
            "--findings",
            str(FIXTURE),
            "--session-id",
            "qa-example",
            "--finding-id",
            "finding-rounding",
            "--disposition",
            "revert-node",
            "--criterion-id",
            "AC1",
            "--reason",
            "Rounding is inside the node's accepted intent.",
            "--recorded-by",
            "sdlc_qa",
            "--recorded-at",
            APPROVED,
            "--approved-by",
            "Owner",
        ],
    )
    assert recorded.exit_code == 0, recorded.output
    assert "revert-node" in recorded.output
    ledger = load_evidence_ledger(workspace / "evidence.json")
    assert [d.disposition for d in ledger.qa_dispositions] == ["revert-node"]
    assert (workspace / "intention-dag.yaml").read_bytes() == intention_before

    handoff = runner.invoke(
        cli,
        [
            "qa",
            "record",
            "--project-path",
            str(tmp_path),
            "--findings",
            str(FIXTURE),
            "--session-id",
            "qa-example",
            "--finding-id",
            "finding-export-encoding",
            "--disposition",
            "bug-handoff",
            "--reason",
            "No Intention node models CSV export.",
            "--recorded-by",
            "sdlc_qa",
            "--recorded-at",
            APPROVED,
        ],
    )
    assert handoff.exit_code == 0, handoff.output
    assert "backlog-export qa-example finding-export-encoding" in handoff.output


def test_cli_refuses_revert_node_without_an_approver(tmp_path):
    workspace = _workspace(tmp_path, _node(MAPPED_GUID))

    result = CliRunner().invoke(
        cli,
        [
            "qa",
            "record",
            "--project-path",
            str(tmp_path),
            "--findings",
            str(FIXTURE),
            "--session-id",
            "qa-example",
            "--finding-id",
            "finding-rounding",
            "--disposition",
            "revert-node",
            "--criterion-id",
            "AC1",
            "--reason",
            "Inside intent.",
            "--recorded-by",
            "sdlc_qa",
            "--recorded-at",
            APPROVED,
        ],
    )

    assert result.exit_code == 1
    assert "approved_by" in result.output
    assert not (workspace / "evidence.json").exists()


def test_cli_rejects_a_tampered_document(tmp_path):
    _workspace(tmp_path, _node(MAPPED_GUID))
    tampered = tmp_path / "findings.json"
    document = _document()
    document["findings"][0]["severity"] = "low"
    tampered.write_text(json.dumps(document), encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["qa", "propose", "--project-path", str(tmp_path), "--findings", str(tampered)],
    )

    assert result.exit_code == 1
    assert "digest" in result.output
