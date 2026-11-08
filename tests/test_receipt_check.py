"""ROADMAP M2: stale mapping receipts are visible instead of accumulating."""

import json

from click.testing import CliRunner

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.source_markers import mapping_receipt_freshness
from tests.test_source_identity_maintenance import (
    INTENT_ID,
    _confirmed_source,
    _project,
    _schema_one_receipt,
)


def _check(tmp_path, *args):
    return CliRunner().invoke(
        cli,
        ["mapping", "receipt", "check", "--project-path", str(tmp_path), *args],
    )


def test_unchanged_source_is_fresh():
    _, annotated = _confirmed_source()

    result = mapping_receipt_freshness(annotated, "src/runtime.py")

    assert result["status"] == "fresh"
    assert result["intent_id"] == INTENT_ID
    assert result["symbol_name"] == "RuntimeBoundary"
    assert result["receipt_line"] == 1


def test_edited_source_is_stale():
    _, annotated = _confirmed_source()

    result = mapping_receipt_freshness(
        annotated + b"\ndef added():\n    return 1\n", "src/runtime.py"
    )

    assert result["status"] == "stale"
    assert result["current_source_sha256"] != result["receipt_source_sha256"]


def test_files_without_receipts_and_string_literals_are_ignored():
    assert mapping_receipt_freshness(b"x = 1\n", "a.py") is None
    literal = b'PREFIX = "# aio-sdlc-mapping-approval: {}"\n'
    assert mapping_receipt_freshness(literal, "a.py") is None


def test_moved_or_malformed_receipts_are_invalid():
    _, annotated = _confirmed_source()
    moved = mapping_receipt_freshness(annotated, "src/elsewhere.py")
    assert moved["status"] == "invalid"
    assert "source_path" in moved["error"]

    neutral = b"class RuntimeBoundary:\n    pass\n"
    _, unknown = _confirmed_source(
        receipt=_schema_one_receipt(neutral, schema_version=9)
    )
    assert mapping_receipt_freshness(unknown, "src/runtime.py")["status"] == "invalid"


def test_cli_check_fails_on_stale_and_warn_only_reports_annotations(tmp_path):
    _, annotated = _confirmed_source()
    _, source_path, _ = _project(tmp_path, annotated)

    fresh = _check(tmp_path)
    assert fresh.exit_code == 0, fresh.output
    assert "1 fresh, 0 stale, 0 invalid" in fresh.output

    source_path.write_bytes(annotated + b"\nVALUE = 1\n")
    before = source_path.read_bytes()

    stale = _check(tmp_path)
    assert stale.exit_code == 1
    assert "STALE  src/runtime.py:1" in stale.output
    assert INTENT_ID in stale.output

    github = _check(tmp_path, "--format", "github", "--warn-only")
    assert github.exit_code == 0, github.output
    assert github.output.startswith(
        "::warning file=src/runtime.py,line=1,title=Stale mapping receipt::"
    )

    report = json.loads(_check(tmp_path, "--format", "json", "--warn-only").output)
    assert report["summary"] == {"fresh": 0, "stale": 1, "invalid": 0}
    assert source_path.read_bytes() == before
