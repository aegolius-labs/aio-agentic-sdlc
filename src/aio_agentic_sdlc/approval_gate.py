"""The Approval Gate: a person approves work before it completes.

When a diff task leaves the diff, the work it stood for is implemented and its
evidence recorded. In the default `gated` mode the task does not complete on
its own: it waits, blocked as awaiting approval, until a person runs
`aio-sdlc approve`, which records who approved it, when and why. In `bypass`
mode, for continuous delivery, the task completes as soon as it leaves the
diff. The mode is `approval_mode` in `.aio-agentic-sdlc/config.json`
(owner decision, 2026-11-09).

Triage already gates the start of the work; this gates its end.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from aio_agentic_sdlc import core
from aio_agentic_sdlc.config import load_config
from aio_agentic_sdlc.core import AWAITING_APPROVAL, BacklogOperationError
from aio_agentic_sdlc.state import mutate_backlog

GATED = "gated"
BYPASS = "bypass"
APPROVAL_MODES = (GATED, BYPASS)
DEFAULT_APPROVAL_MODE = GATED


def approval_mode(project_path: str = ".", *, config: dict | None = None) -> str:
    """Return the configured mode. An unknown value fails closed."""

    if config is None:
        config = load_config(project_path)
    mode = config.get("approval_mode", DEFAULT_APPROVAL_MODE)
    if mode not in APPROVAL_MODES:
        raise BacklogOperationError(
            f"config.json approval_mode must be one of {', '.join(APPROVAL_MODES)}; "
            f"found {mode!r}."
        )
    return mode


def hold_for_approval(item: dict[str, Any]) -> None:
    """Block one finished diff task until a person approves it."""

    blockers = [b for b in item.get("blockers", []) if b != AWAITING_APPROVAL]
    item["blockers"] = [*blockers, AWAITING_APPROVAL]
    item["status"] = "Blocked"
    item["resolution"] = "left the diff; awaiting approval"


def awaiting_approval(project_path: str = ".") -> list[str]:
    backlog = core.load_backlog(project_path) or {}
    return sorted(
        name
        for name, item in (backlog.get("nodes") or {}).items()
        if isinstance(item, dict) and AWAITING_APPROVAL in item.get("blockers", [])
    )


def approve_task(
    name: str,
    *,
    approved_by: str,
    approved_at: datetime,
    rationale: str,
    project_path: str = ".",
) -> dict[str, Any]:
    """Complete one task that awaits approval, recording the approval on it."""

    if not approved_by.strip() or not rationale.strip():
        raise BacklogOperationError("approval needs an approver and a rationale")
    if approved_at.tzinfo is None:
        raise BacklogOperationError("approved_at must include a time zone")

    def mutate(data):
        item = (data.get("nodes") or {}).get(name)
        if not isinstance(item, dict):
            raise BacklogOperationError(f"Item '{name}' not found.")
        if AWAITING_APPROVAL not in item.get("blockers", []):
            raise BacklogOperationError(
                f"'{name}' is not awaiting approval. Only work that has left "
                "the diff can be approved."
            )
        item["blockers"] = [b for b in item["blockers"] if b != AWAITING_APPROVAL]
        approval = {
            "approved_by": approved_by.strip(),
            "approved_at": approved_at.isoformat(),
            "rationale": rationale.strip(),
        }
        item["approval"] = approval
        item["status"] = "Completed" if not item["blockers"] else "Blocked"
        item["resolution"] = (
            f"left the diff; approved by {approval['approved_by']}"
            if item["status"] == "Completed"
            else "approved, but other blockers remain"
        )
        return dict(item), True

    return mutate_backlog(project_path, operation="backlog.approve", mutator=mutate)
