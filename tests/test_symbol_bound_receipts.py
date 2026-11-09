"""Mapping receipts bind to the mapped symbol, not the whole file (2026-11-09).

The owner chose symbol binding so that editing a receipted file elsewhere no
longer needs a new identity review, while any change to the mapped symbol
itself still does.
"""

import hashlib

from aio_agentic_sdlc.source_markers import (
    SourceMarkerError,
    mapping_receipt_freshness,
    symbol_source_sha256,
)
from tests.test_receipt_check import _check
from tests.test_source_identity_maintenance import (
    INTENT_ID,
    _approval,
    _confirmed_source,
    _project,
    _reality_id,
    _schema_one_receipt,
)

SOURCE = (
    b"import os\n"
    b"\n"
    b"\n"
    b"@decorated\n"
    b"class RuntimeBoundary:\n"
    b"    def run(self):\n"
    b"        return 1\n"
    b"\n"
    b"\n"
    b"def helper():\n"
    b"    return 2\n"
)


def _approved(tmp_path):
    engine, source_path, _ = _project(tmp_path, SOURCE)
    observed_id = _reality_id(tmp_path, "RuntimeBoundary")
    review = engine.review(INTENT_ID, candidate_reality_id=observed_id)
    result = engine.approve(
        INTENT_ID,
        observed_id,
        review["evidence_digest"],
        _approval(),
        selection_mode="explicit_observed_guid",
    )
    return engine, source_path, result["receipt"]


def _freshness(source_path):
    return mapping_receipt_freshness(source_path.read_bytes(), "src/runtime.py")


def test_symbol_digest_covers_decorators_and_body_only():
    digest = symbol_source_sha256(
        SOURCE, symbol_kind="class", symbol_name="RuntimeBoundary", start_line=4
    )

    expected = b"@decorated\nclass RuntimeBoundary:\n    def run(self):\n"
    expected += b"        return 1\n"
    assert digest == hashlib.sha256(expected).hexdigest()


def test_a_symbol_not_on_its_start_line_is_refused():
    for kind, name, line in (
        ("class", "RuntimeBoundary", 5),
        ("function", "RuntimeBoundary", 4),
        ("class", "Missing", 4),
    ):
        try:
            symbol_source_sha256(
                SOURCE, symbol_kind=kind, symbol_name=name, start_line=line
            )
        except SourceMarkerError as error:
            assert "follows its mapping marker" in str(error)
        else:
            raise AssertionError((kind, name, line))


def test_new_receipts_bind_to_the_symbol(tmp_path):
    _, source_path, receipt = _approved(tmp_path)

    assert receipt["symbol_sha256"] == symbol_source_sha256(
        SOURCE, symbol_kind="class", symbol_name="RuntimeBoundary", start_line=4
    )
    result = _freshness(source_path)
    assert result["status"] == "fresh"
    assert result["binding"] == "symbol"


def test_edits_outside_the_symbol_leave_the_receipt_fresh(tmp_path):
    _, source_path, _ = _approved(tmp_path)
    content = source_path.read_bytes()
    edited = content.replace(b"import os\n", b"import os\nimport sys\n\nVALUE = 3\n")
    edited = edited.replace(b"return 2", b"return 22")
    source_path.write_bytes(edited)

    assert _freshness(source_path)["status"] == "fresh"
    assert _check(tmp_path).exit_code == 0


def test_edits_inside_the_symbol_make_the_receipt_stale(tmp_path):
    _, source_path, _ = _approved(tmp_path)
    source_path.write_bytes(source_path.read_bytes().replace(b"return 1", b"return 10"))

    result = _freshness(source_path)
    assert result["status"] == "stale"
    assert result["current_symbol_sha256"] != result["receipt_symbol_sha256"]
    stale = _check(tmp_path)
    assert stale.exit_code == 1
    assert "RuntimeBoundary changed since its mapping receipt" in stale.output


def test_a_renamed_symbol_is_stale_with_the_reason(tmp_path):
    _, source_path, _ = _approved(tmp_path)
    source_path.write_bytes(
        source_path.read_bytes().replace(b"class RuntimeBoundary", b"class Renamed")
    )

    result = _freshness(source_path)
    assert result["status"] == "stale"
    assert "follows its mapping marker" in result["error"]


def test_legacy_receipts_stay_file_bound_until_refreshed(tmp_path):
    _, annotated = _confirmed_source()
    engine, source_path, _ = _project(tmp_path, annotated)
    source_path.write_bytes(annotated + b"\nVALUE = 1\n")

    stale = _freshness(source_path)
    assert stale["status"] == "stale"
    assert stale["binding"] == "file"
    assert "binds to the whole file" in _check(tmp_path).output

    review = engine.review_receipt_refresh(INTENT_ID)
    result = engine.refresh_receipt(
        INTENT_ID, review["evidence_digest"], _approval("Batch refresh.")
    )

    assert "symbol_sha256" in result["receipt"]
    assert result["receipt"]["identity_approval"]["schema_version"] == 1
    source_path.write_bytes(source_path.read_bytes() + b"OTHER = 2\n")
    fresh = _freshness(source_path)
    assert fresh["status"] == "fresh"
    assert fresh["binding"] == "symbol"


def test_a_malformed_symbol_digest_is_invalid():
    neutral = b"class RuntimeBoundary:\n    pass\n"
    _, annotated = _confirmed_source(
        receipt=_schema_one_receipt(neutral, symbol_sha256="not-a-digest")
    )

    assert mapping_receipt_freshness(annotated, "src/runtime.py")["status"] == (
        "invalid"
    )
