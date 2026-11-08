import asyncio
import os
from uuid import UUID

from google.antigravity import Agent

from aio_agentic_sdlc import core
from aio_agentic_sdlc.antigravity_compat import local_agent_config
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.diffing_engine import DiffingEngine
from aio_agentic_sdlc.drift_triage import DriftTriageEngine
from aio_agentic_sdlc.evidence import (
    EVIDENCE_LEDGER_FILE,
    EvidenceEvaluator,
    EvidenceLedger,
    load_evidence_ledger,
)
from aio_agentic_sdlc.workspace import INTENTION_DAG_FILE, REALITY_DAG_FILE

# Backlog-entry fields that belong to execution, not to the diff. Re-ingesting
# the diff must not reset them, or in-flight work would lose its state.
EXECUTION_FIELDS = ("status", "blockers")

# Actions the safe diff emits. A backlog item carrying one was cut from the
# diff, so the diff alone decides whether it is still work (ROADMAP M4).
DIFF_ACTIONS = frozenset(
    {
        "update_confirmed",
        "verify_acceptance",
        "review_mapping",
        "resolve_ambiguous_mapping",
        "investigate_intent",
        "connect_confirmed",
    }
)

# Set once an agent returns. Returning is not evidence: the task completes only
# when a later ingest no longer finds it in the diff (ROADMAP M3).
AWAITING_EVIDENCE = (
    "Awaiting evidence: an agent finished this task, so it completes only once "
    "it leaves the diff."
)


def is_diff_task(item):
    """Return whether a backlog item was cut from the safe diff."""

    return isinstance(item, dict) and item.get("action") in DIFF_ACTIONS


def triage_subject_key(task):
    """Return the drift-triage subject key for a safe diff task, or None."""

    if not isinstance(task, dict):
        return None
    evidence = task.get("evidence") or {}
    if task.get("action") == "connect_confirmed":
        relationship = evidence.get("relationship") or {}
        try:
            source = str(UUID(relationship["source_id"]))
            target = str(UUID(relationship["target_id"]))
            relation = relationship["type"]
        except (KeyError, TypeError, ValueError):
            return None
        return f"relationship:{source}:{relation}:{target}"
    canonical_id = task.get("canonical_intent_id") or evidence.get("canonical_guid")
    if not canonical_id:
        return None
    try:
        return f"intent:{UUID(str(canonical_id))}"
    except ValueError:
        return None


def workspace_evidence():
    """Grade acceptance against the workspace ledger; missing means empty."""

    ledger = (
        load_evidence_ledger(EVIDENCE_LEDGER_FILE)
        if os.path.isdir(os.path.dirname(EVIDENCE_LEDGER_FILE))
        else EvidenceLedger()
    )
    return EvidenceEvaluator(ledger, project_root=".")


def authorized_subjects(intention_dag, reality_dag, decisions=None, evidence=None):
    """Return the triage subject keys whose implementation is authorized.

    Only approved intent that triage classifies as ``missing_implementation``
    or ``acceptance_evidence_required`` is authorized, so unapproved intent
    never reaches an implementing agent.
    """

    engine = DriftTriageEngine(intention_dag, reality_dag, evidence=evidence)
    total = max(1, len(intention_dag.nodes) + len(intention_dag.edges))
    report = engine.analyze(decisions=decisions, max_items=total)
    return {
        item["audit"]["subject_key"]
        for item in report["items"]
        if item["implementation_authorized"]
    }


def ingest_diff(decisions=None):
    """
    Loads intention/reality DAGs via DAGManager, uses DiffingEngine to calculate the diff,
    and merges the resulting tasks and edges into the local framework backlog
    using core.load_backlog and core.save_backlog, followed by core.prioritize_items.

    Each ingested task records whether drift triage authorizes its
    implementation. The backlog equals the diff: a diff task that is no longer
    in the diff completes, and a completed one that is back in the diff
    reopens. Other execution state of tasks already in the backlog is kept,
    and items not cut from the diff are never touched.
    """
    intention_dag = DAGManager.load(INTENTION_DAG_FILE)
    reality_dag = DAGManager.load(REALITY_DAG_FILE)

    evidence = workspace_evidence()

    diffing_engine = DiffingEngine(intention_dag, reality_dag, evidence=evidence)
    diff = diffing_engine.calculate_diff()
    tasks = diff.get("nodes", {})
    edges = diff.get("edges", [])
    authorized = authorized_subjects(intention_dag, reality_dag, decisions, evidence)

    backlog = core.load_backlog() or {}

    existing_items = backlog.get("nodes", {})
    current = set()
    for task_name, task in tasks.items() if isinstance(tasks, dict) else tasks:
        if isinstance(task, dict):
            task["id"] = task.get("id", task_name)
            task["name"] = task.get("name", task_name)
            task["implementation_authorized"] = triage_subject_key(task) in authorized
            prior = existing_items.get(task["name"])
            if isinstance(prior, dict):
                for field in EXECUTION_FIELDS:
                    if field in prior:
                        task[field] = prior[field]
            if task.get("status") == "Completed" and is_diff_task(task):
                task["status"] = "New"
                task["resolution"] = "reopened: the task is in the diff again"
            existing_items[task["name"]] = task
            current.add(task["name"])
        elif hasattr(task, "id"):
            existing_items[getattr(task, "name", task.id)] = task.__dict__

    for name, item in existing_items.items():
        if name in current or not is_diff_task(item):
            continue
        if item.get("status") != "Completed":
            item["status"] = "Completed"
            item["resolution"] = "left the diff"
        item["blockers"] = [
            b for b in item.get("blockers", []) if b != AWAITING_EVIDENCE
        ]
        item["implementation_authorized"] = False

    backlog["nodes"] = existing_items

    existing_edges = {
        (e.get("source", e.get("from")), e.get("target", e.get("to"))): e
        for e in backlog.get("edges", [])
    }
    for edge in edges:
        if isinstance(edge, dict) and ("source" in edge or "from" in edge):
            src = edge.get("source", edge.get("from"))
            tgt = edge.get("target", edge.get("to"))
            existing_edges[(src, tgt)] = edge
        elif hasattr(edge, "source") and hasattr(edge, "target"):
            existing_edges[(edge.source, edge.target)] = edge.__dict__

    backlog["edges"] = list(existing_edges.values())

    core.save_backlog(backlog, operation="backlog.ingest-diff")
    core.prioritize_items()


async def execute_task_with_agent(task):
    """
    Instantiates the Agent using LocalAgentConfig. Configures system_instructions
    for the 'sdlc_orchestrator' role, applies CapabilitiesConfig, and streams
    the chat response for the task provided.
    """
    config = local_agent_config(
        "You are the sdlc_orchestrator. Please execute the following task."
    )

    task_desc = (
        task.get("description", "")
        if isinstance(task, dict)
        else getattr(task, "description", str(task))
    )
    prompt = f"Execute this task: {task_desc}"

    async with Agent(config) as agent:
        await agent.chat(prompt)


def _is_authorized(item):
    return item.get("implementation_authorized") is True


async def main_loop(decisions=None):
    """
    1. Invokes ingest_diff().
    2. Fetches the highest-priority unblocked task that triage authorizes
       for implementation via core.get_next_item().
    3. Sets task status to 'In Progress' via core.set_status().
    4. Awaits execute_task_with_agent(task).
    5. Blocks the task as awaiting evidence (or 'Blocked' on failure). An
       agent returning is not evidence; the next ingest completes the task
       only if it has left the diff.

    Returns the executed task's name, or None when nothing is authorized.
    """
    ingest_diff(decisions)

    task, _warning = core.get_next_item(where=_is_authorized)
    if not task:
        return None

    task_name = task.get("name") if isinstance(task, dict) else None
    if not task_name:
        # Malformed task without a name, we cannot process or mark it blocked
        return None

    core.set_status(task_name, "In Progress")

    try:
        await execute_task_with_agent(task)
        core.add_blocker(task_name, AWAITING_EVIDENCE)
    except Exception as e:
        core.set_status(task_name, "Blocked")
        raise e
    return task_name


if __name__ == "__main__":
    asyncio.run(main_loop())
