"""Consume agentic-backlog-kit observed-state documents as evidence (Seam A return).

`abk observe` emits an `abk-observed-state` document: for each issue the kit
manages, its item id, canonical GUID, open/closed state and observed Project
`Status` and `Sprint`. This module validates such a document and maps its
items onto Intention DAG nodes by canonical GUID.

The result is evidence about layer 4, never intent. A closed issue or a `Done`
status says what GitHub currently shows; it does not approve Intent IR, close
an ambiguity, satisfy an acceptance criterion or edit the Intention DAG. Only
an approval-gated Intent IR transition changes layer 1. Nothing here writes.

Items without a GUID, or whose GUID names no Intention node, are reported as
unmapped. They are never matched by item id, title or issue number, because
that would be a guess and this seam exists so that no one has to guess.

The contract is pinned by `tests/fixtures/seam-a/observed-state.json`, a
byte-identical copy of the kit's fixture. Neither repository imports the other.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from uuid import UUID

from aio_agentic_sdlc.dag_manager import DAGManager

CONTRACT = "abk-observed-state"
# Additive fields keep the version; removals and renames bump it. An unknown
# version is rejected rather than read on a best-effort basis.
SUPPORTED_CONTRACT_VERSIONS = frozenset({1})

_TOP_LEVEL_FIELDS = (
    "contract",
    "contract_version",
    "observed_at",
    "source",
    "target",
    "items",
    "unmanaged_issue_count",
    "digest",
)
_ITEM_FIELDS = (
    "item_id",
    "guid",
    "issue_number",
    "state",
    "status",
    "sprint",
    "in_project",
    "in_manifest",
)
_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")


class ObservedStateError(ValueError):
    """Raised when an observed-state document violates the Seam A contract."""


def observed_state_digest(document: dict[str, Any]) -> str:
    """Return the kit's digest of a document: canonical JSON without `digest`."""

    body = {key: value for key, value in document.items() if key != "digest"}
    canonical = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_item(index: int, item: Any) -> None:
    where = f"items[{index}]"
    if not isinstance(item, dict):
        raise ObservedStateError(f"{where} must be an object")
    missing = [field for field in _ITEM_FIELDS if field not in item]
    if missing:
        raise ObservedStateError(f"{where} is missing {', '.join(missing)}")
    if not isinstance(item["item_id"], str) or not item["item_id"]:
        raise ObservedStateError(f"{where}.item_id must be a non-empty string")
    guid = item["guid"]
    if guid is not None and (not isinstance(guid, str) or not _GUID.match(guid)):
        raise ObservedStateError(
            f"{where}.guid must be a lowercase canonical GUID or null"
        )
    if not _is_int(item["issue_number"]) or item["issue_number"] < 1:
        raise ObservedStateError(f"{where}.issue_number must be a positive integer")
    if item["state"] not in {"open", "closed"}:
        raise ObservedStateError(f"{where}.state must be 'open' or 'closed'")
    for field in ("status", "sprint"):
        if item[field] is not None and not isinstance(item[field], str):
            raise ObservedStateError(f"{where}.{field} must be a string or null")
    for field in ("in_project", "in_manifest"):
        if not isinstance(item[field], bool):
            raise ObservedStateError(f"{where}.{field} must be a boolean")


def validate_observed_state(document: Any) -> dict[str, Any]:
    """Return the document unchanged if it honours contract v1, else raise."""

    if not isinstance(document, dict):
        raise ObservedStateError("Observed state must be a JSON object")
    if document.get("contract") != CONTRACT:
        raise ObservedStateError(
            f"Not an observed-state document: contract is {document.get('contract')!r}"
        )
    version = document.get("contract_version")
    if not _is_int(version) or version not in SUPPORTED_CONTRACT_VERSIONS:
        supported = ", ".join(
            str(value) for value in sorted(SUPPORTED_CONTRACT_VERSIONS)
        )
        raise ObservedStateError(
            f"Unknown {CONTRACT} contract_version {version!r}; "
            f"this framework reads version {supported}"
        )
    missing = [field for field in _TOP_LEVEL_FIELDS if field not in document]
    if missing:
        raise ObservedStateError(f"Observed state is missing {', '.join(missing)}")
    if not isinstance(document["items"], list):
        raise ObservedStateError("Observed state items must be an array")
    for index, item in enumerate(document["items"]):
        _validate_item(index, item)
    count = document["unmanaged_issue_count"]
    if not _is_int(count) or count < 0:
        raise ObservedStateError("unmanaged_issue_count must be a non-negative integer")
    digest = document["digest"]
    if not isinstance(digest, str) or not _DIGEST.match(digest):
        raise ObservedStateError("digest must be 'sha256:' followed by 64 hex digits")
    if observed_state_digest(document) != digest:
        raise ObservedStateError(
            "Observed state digest does not match its content; "
            "the document was edited after the kit produced it"
        )
    return document


def load_observed_state(path: str | Path) -> dict[str, Any]:
    """Read and validate one observed-state document from disk."""

    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ObservedStateError(
            f"Observed state is not valid JSON: {error}"
        ) from error
    return validate_observed_state(document)


def map_observed_state(
    document: dict[str, Any], intention: DAGManager
) -> dict[str, Any]:
    """Map observed items to Intention nodes by canonical GUID, as evidence only."""

    validate_observed_state(document)
    nodes_by_guid: dict[str, str] = {}
    for node_id in intention.nodes:
        nodes_by_guid[str(UUID(node_id))] = node_id

    observations: dict[str, dict[str, Any]] = {}
    unmapped: list[dict[str, Any]] = []
    for item in document["items"]:
        guid = item["guid"]
        node_id = nodes_by_guid.get(guid) if guid else None
        if node_id is None:
            unmapped.append(
                {
                    "item_id": item["item_id"],
                    "issue_number": item["issue_number"],
                    "guid": guid,
                    "reason": "no_guid" if guid is None else "guid_not_in_intention",
                }
            )
            continue
        if node_id in observations:
            raise ObservedStateError(
                f"Two observed items claim Intention node {node_id}: "
                f"{observations[node_id]['item_id']} and {item['item_id']}"
            )
        observation = {
            "kind": "github_observation",
            "item_id": item["item_id"],
            "issue_number": item["issue_number"],
            "state": item["state"],
            "status": item["status"],
            "sprint": item["sprint"],
            "in_project": item["in_project"],
            "in_manifest": item["in_manifest"],
            "observed_at": document["observed_at"],
            "digest": document["digest"],
        }
        if "url" in item:
            observation["url"] = item["url"]
        observations[node_id] = observation

    return {
        "authority": "evidence",
        "contract": CONTRACT,
        "contract_version": document["contract_version"],
        "observed_at": document["observed_at"],
        "digest": document["digest"],
        "target": document["target"],
        "summary": {
            "observed_items": len(document["items"]),
            "mapped": len(observations),
            "unmapped": len(unmapped),
            "unmanaged_issue_count": document["unmanaged_issue_count"],
        },
        "observations": observations,
        "unmapped": sorted(unmapped, key=lambda entry: entry["item_id"]),
    }


__all__ = [
    "CONTRACT",
    "SUPPORTED_CONTRACT_VERSIONS",
    "ObservedStateError",
    "load_observed_state",
    "map_observed_state",
    "observed_state_digest",
    "validate_observed_state",
]
