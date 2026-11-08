"""Serialized, optimistic updates for Intent IR in canonical DAG files."""

from datetime import datetime
from pathlib import Path

from .dag_models import Metadata, Node
from .dag_store import mutate_dag_file
from .intent_ir import Approval, ApprovalState, IntentIR, IntentRevision

# The only states a person records through ``decide_intent_file``. Moving
# intent back to draft or review is a revision of its content, made with
# ``update_intent_file``.
DECISION_STATES = (ApprovalState.APPROVED, ApprovalState.REJECTED)


class IntentStoreError(ValueError):
    """Raised for an expected optimistic Intent IR mutation rejection."""


def create_intent_node_file(
    filepath: str | Path,
    node: Node,
    *,
    create_with: Metadata | None = None,
) -> int:
    """Atomically create one canonical DAG node with validated Intent IR.

    With ``create_with``, a missing Intention DAG is created holding only
    this node, so a fresh project needs no hand-written DAG skeleton.
    """
    if node.intent is None:
        raise IntentStoreError("canonical intent node creation requires Intent IR")
    if (
        len(node.intent.revision_history) != 1
        or node.intent.revision_history[0].revision != 1
    ):
        raise IntentStoreError(
            "new canonical intent node must contain exactly revision 1"
        )

    def create(manager):
        manager.add_node(node)
        return node.intent.revision_history[-1].revision

    return mutate_dag_file(filepath, create, create_with=create_with)


def update_intent_file(
    filepath: str | Path,
    node_id: str,
    intent: IntentIR,
    *,
    expected_revision: int,
) -> int:
    """Create or revise one node's Intent IR without rewriting audit history."""
    if expected_revision < 0:
        raise IntentStoreError("expected_revision must be zero or greater")

    def update(manager):
        node = manager.get_node(node_id)
        current = node.intent
        current_revision = current.revision_history[-1].revision if current else 0
        if current_revision != expected_revision:
            raise IntentStoreError(
                f"stale Intent IR revision for node {node_id}: "
                f"expected {expected_revision}, found {current_revision}"
            )

        if current is None:
            if (
                len(intent.revision_history) != 1
                or intent.revision_history[0].revision != 1
            ):
                raise IntentStoreError("new Intent IR must contain exactly revision 1")
        else:
            existing_history = current.revision_history
            proposed_history = intent.revision_history
            if (
                len(proposed_history) != len(existing_history) + 1
                or proposed_history[:-1] != existing_history
            ):
                raise IntentStoreError(
                    "Intent IR revision must preserve existing revision history "
                    "and append one entry"
                )
            if proposed_history[-1].revision != current_revision + 1:
                raise IntentStoreError(
                    f"next Intent IR revision must be {current_revision + 1}"
                )

        manager.update_node(node_id, intent=intent)
        return intent.revision_history[-1].revision

    return mutate_dag_file(filepath, update)


def decide_intent_file(
    filepath: str | Path,
    node_id: str,
    *,
    state: ApprovalState,
    decided_by: str,
    decided_at: datetime,
    rationale: str,
    expected_revision: int,
    generator_version: str,
) -> int:
    """Record a person's approval or rejection as one appended revision.

    The intent content is unchanged. Only the approval and the revision
    history move, under the same optimistic revision check as any edit.
    """
    state = ApprovalState(state)
    if state not in DECISION_STATES:
        raise IntentStoreError("an intent decision is either approved or rejected")

    def decide(manager):
        node = manager.get_node(node_id)
        current = node.intent
        if current is None:
            raise IntentStoreError(f"node {node_id} has no Intent IR to decide on")
        current_revision = current.revision_history[-1].revision
        if current_revision != expected_revision:
            raise IntentStoreError(
                f"stale Intent IR revision for node {node_id}: "
                f"expected {expected_revision}, found {current_revision}"
            )
        if current.approval.state == state:
            raise IntentStoreError(
                f"intent for node {node_id} is already {state.value}"
            )
        revision = IntentRevision(
            revision=current_revision + 1,
            recorded_at=decided_at,
            actor=decided_by,
            generator_version=generator_version,
            summary=f"{state.value.capitalize()} by {decided_by}: {rationale}",
        )
        decided = current.model_copy(
            update={
                "revision_history": [*current.revision_history, revision],
                "generator_version": generator_version,
                "approval": Approval(
                    state=state,
                    approved_by=decided_by,
                    approved_at=decided_at,
                    rationale=rationale,
                ),
            }
        )
        manager.update_node(
            node_id, intent=IntentIR.model_validate(decided.model_dump())
        )
        return revision.revision

    return mutate_dag_file(filepath, decide)
