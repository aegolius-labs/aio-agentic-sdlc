"""Seam A return channel: agentic-backlog-kit observed state is evidence, never intent.

`tests/fixtures/seam-a/observed-state.json` is byte-identical to the kit's copy
of the same name, which pins what `abk observe` emits (contract version 1). The
two repositories do not import each other, so this fixture is the contract.

If the fixture test fails, the seam moved. Update both fixtures together and say
so in the change; do not quietly relax the assertion.
"""

import copy
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Metadata, Node, NodeType
from aio_agentic_sdlc.observed_state import (
    ObservedStateError,
    load_observed_state,
    map_observed_state,
    observed_state_digest,
    validate_observed_state,
)
from aio_agentic_sdlc.reconciliation import ReconciliationEngine

FIXTURES = Path(__file__).parent / "fixtures" / "seam-a"
OBSERVED = FIXTURES / "observed-state.json"
IDENTITY = FIXTURES / "projected-item.json"


def _document() -> dict:
    return json.loads(OBSERVED.read_text(encoding="utf-8"))


def _resealed(document: dict) -> dict:
    document["digest"] = observed_state_digest(document)
    return document


def _intention(*guids: str) -> DAGManager:
    nodes = [
        Node(id=guid, type=NodeType.COMPONENT, name=f"Node {index}")
        for index, guid in enumerate(guids)
    ]
    return DAGManager(Metadata(name="Intention", version="1.0"), nodes, [])


def _reality() -> DAGManager:
    return DAGManager(Metadata(name="Reality", version="1.0"), [], [])


def test_the_fixture_honours_contract_version_1():
    document = load_observed_state(OBSERVED)

    assert document["contract"] == "abk-observed-state"
    assert document["contract_version"] == 1
    assert observed_state_digest(document) == document["digest"]


def test_the_fixture_shares_its_identity_with_the_seam_a_identity_fixture():
    identity = json.loads(IDENTITY.read_text(encoding="utf-8"))
    (item,) = _document()["items"]

    assert item["item_id"] == identity["item"]["id"]
    assert item["guid"] == identity["guid"]


def test_an_unknown_contract_version_is_rejected():
    document = _resealed({**_document(), "contract_version": 2})

    with pytest.raises(ObservedStateError, match="contract_version 2"):
        validate_observed_state(document)


def test_an_additive_field_keeps_the_version():
    document = _document()
    document["items"][0]["closed_at"] = "2026-09-28T11:00:00Z"
    document["new_top_level_note"] = "added later"

    validate_observed_state(_resealed(document))


def test_a_removed_field_is_rejected():
    document = _document()
    del document["items"][0]["status"]

    with pytest.raises(ObservedStateError, match="missing status"):
        validate_observed_state(_resealed(document))


def test_an_edited_document_fails_its_digest():
    document = _document()
    document["items"][0]["state"] = "closed"

    with pytest.raises(ObservedStateError, match="digest"):
        validate_observed_state(document)


def test_items_map_to_intention_nodes_by_canonical_guid_only():
    document = _document()
    guid = document["items"][0]["guid"]

    for stored in (guid, guid.upper()):
        mapped = map_observed_state(document, _intention(stored))

        assert list(mapped["observations"]) == [stored]
        assert mapped["observations"][stored]["item_id"] == "F-SEAM-A"
        assert mapped["unmapped"] == []
        assert mapped["authority"] == "evidence"


def test_items_without_a_resolvable_guid_are_unmapped_not_guessed():
    document = _document()
    item = document["items"][0]
    without_guid = {**item, "item_id": "F-NO-GUID", "guid": None, "issue_number": 43}
    document["items"].append(without_guid)
    _resealed(document)

    mapped = map_observed_state(
        document, _intention("00000000-0000-0000-0000-000000000001")
    )

    assert mapped["observations"] == {}
    assert [(entry["item_id"], entry["reason"]) for entry in mapped["unmapped"]] == [
        ("F-NO-GUID", "no_guid"),
        ("F-SEAM-A", "guid_not_in_intention"),
    ]


def test_reconciliation_attaches_observations_without_changing_classification():
    document = _document()
    guid = document["items"][0]["guid"]
    closed = copy.deepcopy(document)
    closed["items"][0]["state"] = "closed"
    closed["items"][0]["status"] = "Done"
    _resealed(closed)
    intention = _intention(guid)

    baseline = ReconciliationEngine(intention, _reality()).analyze()
    observed = ReconciliationEngine(
        intention, _reality(), observed_state=closed
    ).analyze()

    (base_record,) = baseline["items"]
    (record,) = observed["items"]
    assert record["classification"] == base_record["classification"] == "unmapped"
    assert record["requires_approval"] is True
    assert record["evidence"][-1]["kind"] == "github_observation"
    assert record["evidence"][-1]["state"] == "closed"
    assert record["evidence"][-1]["status"] == "Done"
    assert baseline["summary"] == observed["summary"]
    assert observed["observed_state"]["summary"]["mapped"] == 1
    assert "observed_state" not in baseline


def test_reconcile_cli_reads_observed_state_and_leaves_the_intention_dag_unchanged(
    tmp_path,
):
    guid = _document()["items"][0]["guid"]
    intention_file = tmp_path / "intention-dag.yaml"
    reality_file = tmp_path / "reality-dag.yaml"
    _intention(guid).save(str(intention_file))
    _reality().save(str(reality_file))
    before = intention_file.read_bytes()

    result = CliRunner().invoke(
        cli,
        [
            "reconcile",
            "--intention",
            str(intention_file),
            "--reality",
            str(reality_file),
            "--observed-state",
            str(OBSERVED),
        ],
    )

    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["observed_state"]["summary"]["mapped"] == 1
    assert report["items"][0]["evidence"][-1]["item_id"] == "F-SEAM-A"
    assert intention_file.read_bytes() == before


def test_reconcile_cli_rejects_an_unknown_contract_version(tmp_path):
    intention_file = tmp_path / "intention-dag.yaml"
    reality_file = tmp_path / "reality-dag.yaml"
    observed_file = tmp_path / "observed.json"
    _intention().save(str(intention_file))
    _reality().save(str(reality_file))
    observed_file.write_text(
        json.dumps(_resealed({**_document(), "contract_version": 99})),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "reconcile",
            "--intention",
            str(intention_file),
            "--reality",
            str(reality_file),
            "--observed-state",
            str(observed_file),
        ],
    )

    assert result.exit_code == 1
    assert "contract_version 99" in result.output
