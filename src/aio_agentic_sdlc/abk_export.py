"""Seam A forward direction: project authorized work into an ABK manifest.

``doc/authority-model.md`` makes Agentic Backlog Kit layer 4, a one-way
projection of layer 3 onto GitHub. This module writes that projection as an
ABK manifest and nothing else: it never calls GitHub, and every write the kit
then makes still goes through the kit's own plan, digest and apply contract.

The contract (``seam-a-work`` v1, fixture ``tests/fixtures/seam-a/work.json``):

- Only diff tasks that drift triage authorizes are exported, one ABK ``Task``
  per Intention node, keyed by canonical GUID. Relationship tasks have no
  single node and are not exported.
- The base manifest supplies ``github``, ``workflow`` and ``scoring``. Items
  that carry a ``guid`` belong to this export and are rewritten on each run,
  except their ``status`` and ``sprint``, which are the team's execution
  state; items without a ``guid`` are kept exactly as they are.
- A GUID item whose work has left the diff stays, with the first done status,
  because the kit never closes an issue the manifest stops listing. It is
  dropped only once observed state (``abk observe``) reports its issue closed.
"""

from __future__ import annotations

import copy
from typing import Any
from uuid import UUID

from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.diffing_engine import DiffingEngine
from aio_agentic_sdlc.drift_triage import DriftTriageEngine, TriageDecisionSet
from aio_agentic_sdlc.evidence import EvidenceEvaluator

CONTRACT = "seam-a-work"
CONTRACT_VERSION = 1
ABK_SCHEMA_VERSION = 2
ITEM_TYPE = "Task"
READY_STATUS = "Ready"
DEFAULT_DONE_STATUS = "Done"
ENABLER_VALUE = 3
ID_PREFIX = "SDLC-"


class AbkExportError(ValueError):
    """Raised when the base manifest or the derived work cannot be exported."""


def _guid(value: Any) -> str | None:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _task_guid(task: dict[str, Any]) -> str | None:
    if task.get("action") == "connect_confirmed":
        return None
    evidence = task.get("evidence") or {}
    return _guid(task.get("canonical_intent_id") or evidence.get("canonical_guid"))


def _authorized_guids(
    intention: DAGManager,
    reality: DAGManager,
    evidence: EvidenceEvaluator | None,
    decisions: TriageDecisionSet | None,
) -> set[str]:
    total = max(1, len(intention.nodes) + len(intention.edges))
    report = DriftTriageEngine(intention, reality, evidence=evidence).analyze(
        decisions=decisions, max_items=total
    )
    guids = set()
    for item in report["items"]:
        key = item["audit"]["subject_key"]
        if item["implementation_authorized"] and key.startswith("intent:"):
            guids.add(key.removeprefix("intent:"))
    return guids


def _title(task_name: str, guid: str) -> str:
    suffix = f" [{guid}]"
    return task_name[: -len(suffix)] if task_name.endswith(suffix) else task_name


def _criteria(intention: DAGManager, guid: str) -> list[str]:
    node = intention.nodes.get(guid)
    if node is None or node.intent is None:
        return []
    return [
        criterion.statement.strip()
        for criterion in node.intent.acceptance_criteria
        if criterion.statement.strip()
    ]


def _workflow(base: dict[str, Any]) -> tuple[str, list[str]]:
    workflow = base.get("workflow") or {}
    statuses = workflow.get("statuses")
    if statuses is not None and READY_STATUS not in statuses:
        raise AbkExportError(
            f"the base manifest workflow has no '{READY_STATUS}' status for "
            "exported work"
        )
    return READY_STATUS, list(workflow.get("done_statuses") or [DEFAULT_DONE_STATUS])


def _item_id(guid: str, taken: set[str]) -> str:
    compact = guid.replace("-", "")
    for length in (8, 12, 32):
        candidate = f"{ID_PREFIX}{compact[:length]}"
        if candidate not in taken:
            return candidate
    raise AbkExportError(f"no free ABK item id for GUID {guid}")


def _closed_guids(observed_state: dict[str, Any] | None) -> set[str]:
    if not observed_state:
        return set()
    return {
        item["guid"]
        for item in observed_state.get("items", [])
        if item.get("guid") and item.get("state") == "closed"
    }


def export_abk_manifest(
    intention: DAGManager,
    reality: DAGManager,
    base_manifest: dict[str, Any],
    *,
    evidence: EvidenceEvaluator | None = None,
    decisions: TriageDecisionSet | None = None,
    observed_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``base_manifest`` with its GUID items replaced by authorized work."""

    if not isinstance(base_manifest, dict) or not isinstance(
        base_manifest.get("items"), list
    ):
        raise AbkExportError("the base manifest must be an object with an items list")
    if base_manifest.get("schema_version") not in (1, ABK_SCHEMA_VERSION):
        raise AbkExportError("the base manifest schema_version must be 1 or 2")
    ready, done_statuses = _workflow(base_manifest)

    manual = [item for item in base_manifest["items"] if not item.get("guid")]
    previous = {
        _guid(item["guid"]): item for item in base_manifest["items"] if item.get("guid")
    }
    if None in previous:
        raise AbkExportError("a base manifest item carries a non-canonical guid")

    authorized = _authorized_guids(intention, reality, evidence, decisions)
    diff = DiffingEngine(intention, reality, evidence=evidence).calculate_diff()
    work: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for name, task in sorted(diff.get("nodes", {}).items()):
        guid = _task_guid(task)
        if guid in authorized:
            work.setdefault(guid, []).append((name, task))

    taken = {item["id"] for item in manual}
    exported = []
    for guid in sorted(work):
        tasks = work[guid]
        prior = previous.get(guid)
        item_id = prior["id"] if prior else _item_id(guid, taken)
        if item_id in taken:
            raise AbkExportError(
                f"ABK item id {item_id} for GUID {guid} is already used by an "
                "item without a guid"
            )
        taken.add(item_id)
        # The team's execution state (status, sprint) survives a re-export;
        # work that is back in the diff after it was done reopens as Ready.
        status = prior.get("status") if prior else None
        if not status or status in done_statuses:
            status = ready
        exported.append(
            {
                "id": item_id,
                "title": "; ".join(_title(name, guid) for name, _ in tasks),
                "type": ITEM_TYPE,
                "description": "\n\n".join(task["description"] for _, task in tasks),
                "acceptance_criteria": _criteria(intention, guid),
                "parent": None,
                "depends_on": [],
                "impact": max(task["impact"] for _, task in tasks),
                "effort": max(task["effort"] for _, task in tasks),
                "business_value": max(task["impact"] for _, task in tasks),
                "enabler_value": ENABLER_VALUE,
                "status": status,
                "maturity": "ready",
                "sprint": prior.get("sprint") if prior else None,
                "guid": guid,
            }
        )

    closed = _closed_guids(observed_state)
    finished = []
    for guid, item in sorted(previous.items()):
        if guid in work or guid in closed:
            continue
        kept = copy.deepcopy(item)
        kept["guid"] = guid
        kept["status"] = done_statuses[0]
        if kept["id"] in taken:
            raise AbkExportError(f"ABK item id {kept['id']} is used twice")
        taken.add(kept["id"])
        finished.append(kept)

    manifest = copy.deepcopy(base_manifest)
    manifest["schema_version"] = ABK_SCHEMA_VERSION
    manifest["items"] = copy.deepcopy(manual) + exported + finished
    return manifest
