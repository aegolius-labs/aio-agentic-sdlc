"""ROADMAP M5, Seam A forward: authorized work projects into an ABK manifest.

`tests/fixtures/seam-a/work.json` is byte-identical to the copy in
agentic-backlog-kit, whose test validates its manifest with the kit's own
engine. If this test fails, the seam moved: update both fixtures together and
say so in the change.
"""

import copy
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aio_agentic_sdlc.abk_export import (
    CONTRACT,
    CONTRACT_VERSION,
    AbkExportError,
    export_abk_manifest,
    newly_finished,
)
from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.evidence import EvidenceEvaluator, EvidenceLedger
from aio_agentic_sdlc.intent_ir import ApprovalState
from tests.test_evidence import _manager, _node, _record

FIXTURE = Path(__file__).parent / "fixtures" / "seam-a" / "work.json"
GUID = "3f2b8c1e-6d4a-4b7e-9c2f-8a1d5e6f7a90"
UNAPPROVED = "9d0e1f2a-3b4c-4d5e-8f60-718293a4b5c6"


def _fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _scenario(*, recorded=False):
    approved = _node(GUID)
    unapproved = _node(UNAPPROVED)
    unapproved.intent.approval.state = ApprovalState.REVIEW_REQUIRED
    unapproved.intent.approval.approved_by = None
    unapproved.intent.approval.approved_at = None
    intention = _manager(approved, unapproved)
    reality = _manager(_node(GUID), _node(UNAPPROVED))
    ledger = EvidenceLedger(records=[_record(approved)] if recorded else [])
    return intention, reality, EvidenceEvaluator(ledger)


def test_fixture_pins_the_contract():
    fixture = _fixture()

    assert fixture["contract"] == CONTRACT
    assert fixture["contract_version"] == CONTRACT_VERSION


def test_authorized_work_exports_exactly_the_pinned_manifest():
    fixture = _fixture()
    intention, reality, evidence = _scenario()

    manifest = export_abk_manifest(
        intention, reality, fixture["base_manifest"], evidence=evidence
    )

    assert manifest == fixture["manifest"]
    guid_items = [item for item in manifest["items"] if item.get("guid")]
    assert [item["guid"] for item in guid_items] == [GUID]
    assert UNAPPROVED not in json.dumps(manifest)


def test_manual_items_and_team_execution_state_survive_a_reexport():
    fixture = _fixture()
    intention, reality, evidence = _scenario()
    base = copy.deepcopy(fixture["manifest"])
    exported = next(item for item in base["items"] if item.get("guid"))
    exported["status"] = "In Progress"
    exported["sprint"] = "Sprint 4"

    again = export_abk_manifest(intention, reality, base, evidence=evidence)

    assert again["items"][0] == fixture["base_manifest"]["items"][0]
    item = next(item for item in again["items"] if item.get("guid"))
    assert (item["id"], item["status"], item["sprint"]) == (
        exported["id"],
        "In Progress",
        "Sprint 4",
    )


def test_finished_work_stays_done_until_its_issue_is_observed_closed():
    fixture = _fixture()
    intention, reality, evidence = _scenario(recorded=True)

    kept = export_abk_manifest(
        intention, reality, fixture["manifest"], evidence=evidence
    )
    item = next(item for item in kept["items"] if item.get("guid"))
    assert item["status"] == "Done"
    assert newly_finished(fixture["manifest"], kept) == [item["id"]]
    assert newly_finished(kept, kept) == []

    observed = {"items": [{"guid": GUID, "state": "closed"}]}
    dropped = export_abk_manifest(
        intention,
        reality,
        fixture["manifest"],
        evidence=evidence,
        observed_state=observed,
    )
    assert [item for item in dropped["items"] if item.get("guid")] == []


def test_done_work_back_in_the_diff_reopens_as_ready():
    fixture = _fixture()
    intention, reality, evidence = _scenario()
    base = copy.deepcopy(fixture["manifest"])
    next(item for item in base["items"] if item.get("guid"))["status"] = "Done"

    again = export_abk_manifest(intention, reality, base, evidence=evidence)

    assert next(i for i in again["items"] if i.get("guid"))["status"] == "Ready"


def test_unusable_base_manifests_fail_clearly():
    fixture = _fixture()
    intention, reality, evidence = _scenario()

    no_ready = copy.deepcopy(fixture["base_manifest"])
    no_ready["workflow"]["statuses"].remove("Ready")
    with pytest.raises(AbkExportError, match="'Ready' status"):
        export_abk_manifest(intention, reality, no_ready, evidence=evidence)

    fresh = copy.deepcopy(fixture["base_manifest"])
    fresh["items"][0]["id"] = "SDLC-3f2b8c1e"
    widened = export_abk_manifest(intention, reality, fresh, evidence=evidence)
    assert widened["items"][1]["id"] == "SDLC-3f2b8c1e6d4a"

    clash = copy.deepcopy(fixture["manifest"])
    clash["items"][0]["id"] = clash["items"][1]["id"]
    with pytest.raises(AbkExportError, match="already used"):
        export_abk_manifest(intention, reality, clash, evidence=evidence)


def test_cli_writes_the_manifest_and_never_touches_the_dags(tmp_path):
    fixture = _fixture()
    intention, reality, _ = _scenario()
    workspace = tmp_path / ".aio-agentic-sdlc"
    workspace.mkdir()
    intention.save(str(workspace / "intention-dag.yaml"))
    reality.save(str(workspace / "reality-dag.yaml"))
    base = tmp_path / "manifest.json"
    base.write_text(json.dumps(fixture["base_manifest"]), encoding="utf-8")
    before = (workspace / "intention-dag.yaml").read_bytes()

    result = CliRunner().invoke(
        cli,
        [
            "export-abk",
            "--intention",
            str(workspace / "intention-dag.yaml"),
            "--reality",
            str(workspace / "reality-dag.yaml"),
            "--base-manifest",
            str(base),
            "--output",
            str(base),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Exported 1 GUID item(s)" in result.output
    assert json.loads(base.read_text(encoding="utf-8")) == fixture["manifest"]
    assert (workspace / "intention-dag.yaml").read_bytes() == before
