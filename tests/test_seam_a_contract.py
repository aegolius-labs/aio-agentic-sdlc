"""Seam A contract: a canonical GUID survives from the Intention DAG to GitHub.

This framework owns canonical GUID traceability and projects accepted work into
`agentic-backlog-kit`. The two repositories are independently installable and
must not import each other, so the identity half of the contract is pinned by a
committed fixture on each side. `tests/fixtures/seam-a/projected-item.json` is
byte-identical to the kit's copy: one projected manifest item and the issue-body
marker the kit writes for it. The matching test in the kit asserts it accepts
this item and writes exactly this marker.

The kit accepts only the lowercase canonical form, while `Node.id` also admits
uppercase hex. A projection must therefore hand over `str(UUID(node.id))`, never
the stored spelling.

If this test fails, the seam moved. Fix the projection or update both fixtures
together and say so in the change; do not quietly relax the assertion.
"""

import json
from pathlib import Path
from uuid import UUID

from aio_agentic_sdlc.dag_models import Node, NodeType

FIXTURE = Path(__file__).parent / "fixtures" / "seam-a" / "projected-item.json"
MARKER_PREFIX = "<!-- agentic-backlog-kit:"
MARKER_SUFFIX = "-->"


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _marker_fields(marker: str) -> dict[str, str]:
    assert marker.startswith(MARKER_PREFIX) and marker.endswith(MARKER_SUFFIX)
    inner = marker[len(MARKER_PREFIX) : -len(MARKER_SUFFIX)].strip()
    return dict(part.split("=", 1) for part in inner.split(";"))


def test_fixture_guid_is_a_valid_canonical_node_id():
    guid = _fixture()["guid"]

    Node(id=guid, type=NodeType.COMPONENT, name="Projected")
    assert str(UUID(guid)) == guid


def test_every_spelling_of_a_node_id_projects_to_the_fixture_guid():
    guid = _fixture()["guid"]

    for stored in (guid, guid.upper()):
        node = Node(id=stored, type=NodeType.COMPONENT, name="Projected")
        assert str(UUID(node.id)) == guid


def test_the_projected_item_carries_the_guid_unchanged():
    fixture = _fixture()

    assert fixture["item"]["guid"] == fixture["guid"]


def test_the_marker_carries_the_item_id_and_guid():
    fixture = _fixture()
    fields = _marker_fields(fixture["marker"])

    assert fields == {
        "id": fixture["item"]["id"],
        "schema": "1",
        "guid": fixture["guid"],
    }
    # Every released kit reads the id only up to the first separator.
    assert (
        fixture["marker"].split("id=", 1)[1].split(";", 1)[0] == fixture["item"]["id"]
    )
