import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from aio_agentic_sdlc import __version__
from aio_agentic_sdlc.abk_export import export_abk_manifest, newly_finished
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Edge, EdgeType, Metadata, Node, NodeType
from aio_agentic_sdlc.dag_store import (
    dag_file_lock,
    guarded_dag_path,
    guarded_file_path,
    mutate_dag_file,
)
from aio_agentic_sdlc.dag_visualization import DAGVisualizationEngine, render_dag
from aio_agentic_sdlc.diffing_engine import DiffingEngine, DiffPolicy
from aio_agentic_sdlc.drift_triage import (
    DriftClassification,
    DriftTriageEngine,
    TriageDecision,
    TriageDecisionSet,
    render_drift_triage,
)
from aio_agentic_sdlc.evidence import (
    EVIDENCE_LEDGER_FILE,
    EvidenceEvaluator,
    EvidenceLevel,
    EvidenceRecord,
    load_evidence_ledger,
    record_evidence,
)
from aio_agentic_sdlc.intent_consistency import (
    IntentConsistencyChecker,
    render_intent_consistency,
)
from aio_agentic_sdlc.intent_ir import ApprovalState, IntentIR
from aio_agentic_sdlc.intent_migration import LegacyIntentMigrator
from aio_agentic_sdlc.intent_store import (
    create_intent_node_file,
    decide_intent_file,
    update_intent_file,
)
from aio_agentic_sdlc.mapping import (
    MappingApproval,
    MappingEngine,
    render_mapping_review,
    render_receipt_refresh_review,
)
from aio_agentic_sdlc.observed_state import load_observed_state
from aio_agentic_sdlc.reality_dag_generator import RealityDAGGenerator
from aio_agentic_sdlc.reconciliation import (
    ReconciliationEngine,
    validate_reconciliation_report_output,
    write_reconciliation_report,
)
from aio_agentic_sdlc.traceability import build_trace, render_trace_markdown
from aio_agentic_sdlc.workspace import (
    BACKLOG_FILE,
    INTENTION_DAG_FILE,
    REALITY_DAG_FILE,
    WORKSPACE_DIR,
)


@click.group()
@click.version_option(__version__, prog_name="dag-tool")
def cli():
    """CLI tool for managing DAG state files safely."""
    pass


@cli.command()
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the DAG yaml file.",
)
def validate(file):
    """Validates the structure and constraints of the DAG file."""
    try:
        manager = DAGManager.load(file)
        manager.validate()
        click.echo("DAG is valid.")
    except Exception as e:
        click.secho(f"Error validating DAG: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.command("validate-intent")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Intention DAG yaml file.",
)
@click.option(
    "--require-all/--allow-partial",
    default=True,
    help="Require every node to contain Intent IR or allow legacy nodes.",
)
def validate_intent(file, require_all):
    """Validate the Intent IR payloads and coverage of an Intention DAG."""
    try:
        manager = DAGManager.load(file)
        manager.validate_intent_ir(require_all=require_all)
        click.echo("Intent IR is valid.")
    except Exception as e:
        click.secho(f"Error validating Intent IR: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.command("check-consistency")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Intention DAG yaml file.",
)
@click.option(
    "--max-items",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Maximum findings returned without hiding complete totals.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Render a human brief or the complete machine report.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit non-zero when any error-severity finding is reported.",
)
def check_consistency(file, max_items, output_format, strict):
    """Report internal contradictions in the Intention DAG without mutating it."""
    try:
        report = IntentConsistencyChecker(DAGManager.load(file)).analyze(
            max_items=max_items
        )
    except Exception as e:
        click.secho(
            f"Error checking Intention DAG consistency: {str(e)}", err=True, fg="red"
        )
        sys.exit(1)
    if output_format.casefold() == "json":
        click.echo(json.dumps(report, indent=2))
    else:
        click.echo(render_intent_consistency(report))
    if strict and report["summary"]["by_severity"]["error"]:
        sys.exit(1)


@cli.command("intent-summary")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Intention DAG yaml file.",
)
@click.option("--node-id", help="Limit the review to one node ID.")
def intent_summary(file, node_id):
    """Render a human-readable Intent IR review without raw YAML."""
    try:
        manager = DAGManager.load(file)
        click.echo(manager.render_intent_summary(node_id=node_id))
    except Exception as e:
        click.secho(f"Error rendering Intent IR: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.group("intent")
def intent():
    """Create or revise protected Intent IR payloads."""
    pass


@intent.command("create-node")
@click.option(
    "--file",
    required=True,
    type=click.Path(dir_okay=False),
    help="Path to the Intention DAG yaml file. Created when it does not exist yet.",
)
@click.option(
    "--dag-name",
    help=(
        "Name of a newly created Intention DAG. Defaults to the project "
        "directory's name. Ignored when the DAG exists."
    ),
)
@click.option("--node-id", required=True, help="Canonical node GUID.")
@click.option(
    "--type", "node_type", required=True, type=click.Choice([t.value for t in NodeType])
)
@click.option("--name", required=True, help="Node name.")
@click.option("--domain", help="Node domain.")
@click.option("--description", help="Node description.")
@click.option(
    "--payload-file",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="JSON file containing the initial Intent IR v1 payload.",
)
def intent_create_node(
    file, dag_name, node_id, node_type, name, domain, description, payload_file
):
    """Atomically create one canonical node with its initial Intent IR."""
    try:
        create_with = None
        if not os.path.lexists(file):
            dag_path = Path(os.path.abspath(file))
            if not dag_path.parent.is_dir():
                raise click.ClickException(
                    f"Directory does not exist: {dag_path.parent}. "
                    "Run `aio-sdlc init` first."
                )
            default_name = (
                dag_path.parent.parent.name
                if dag_path.parent.name == WORKSPACE_DIR
                else dag_path.stem
            )
            create_with = Metadata(name=dag_name or default_name, version="1.0.0")
        with open(payload_file, "r", encoding="utf-8") as payload:
            intent_ir = IntentIR.model_validate(json.load(payload))
        node = Node(
            id=node_id,
            type=NodeType(node_type),
            name=name,
            domain=domain,
            description=description,
            intent=intent_ir,
        )
        revision = create_intent_node_file(file, node, create_with=create_with)
        if create_with is not None:
            click.echo(f"Created Intention DAG '{create_with.name}' at {file}.")
        click.echo(f"Node '{node_id}' created with Intent IR revision {revision}.")
    except Exception as e:
        click.secho(f"Error creating intent node: {str(e)}", err=True, fg="red")
        sys.exit(1)


@intent.command("set")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Intention DAG yaml file.",
)
@click.option(
    "--node-id", required=True, help="Node ID receiving the Intent IR payload."
)
@click.option(
    "--payload-file",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="JSON file containing one complete Intent IR payload.",
)
@click.option(
    "--expected-revision",
    required=True,
    type=click.IntRange(min=0),
    help="Current revision, or zero when creating the first Intent IR payload.",
)
def intent_set(file, node_id, payload_file, expected_revision):
    """Create or revise Intent IR using optimistic revision protection."""
    try:
        with open(payload_file, "r", encoding="utf-8") as payload:
            intent_ir = IntentIR.model_validate(json.load(payload))
        revision = update_intent_file(
            file,
            node_id,
            intent_ir,
            expected_revision=expected_revision,
        )
        click.echo(f"Intent IR for node '{node_id}' saved at revision {revision}.")
    except Exception as e:
        click.secho(f"Error setting Intent IR: {str(e)}", err=True, fg="red")
        sys.exit(1)


@intent.command("decide")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Path to the Intention DAG yaml file.",
)
@click.option("--node-id", required=True, help="Node whose intent is decided.")
@click.option(
    "--state",
    required=True,
    type=click.Choice([ApprovalState.APPROVED.value, ApprovalState.REJECTED.value]),
    help="The person's decision.",
)
@click.option("--decided-by", required=True, help="The person deciding.")
@click.option("--decided-at", required=True, help="Timezone-aware ISO-8601 timestamp.")
@click.option("--rationale", required=True, help="Why the person decided this.")
@click.option(
    "--expected-revision",
    required=True,
    type=click.IntRange(min=1),
    help="The intent's current revision, from `dag-tool intent-summary`.",
)
def intent_decide(
    file, node_id, state, decided_by, decided_at, rationale, expected_revision
):
    """Record a person's approval or rejection of one node's intent.

    Appends exactly one revision and leaves the intent's content unchanged.
    The decision is the person's: record it only after they made it.
    """
    try:
        revision = decide_intent_file(
            file,
            node_id,
            state=ApprovalState(state),
            decided_by=decided_by,
            decided_at=_parse_aware_timestamp(decided_at, "--decided-at"),
            rationale=rationale,
            expected_revision=expected_revision,
            generator_version=f"aio-agentic-sdlc/{__version__}",
        )
        click.echo(
            f"Intent for node '{node_id}' {state} by {decided_by} at revision "
            f"{revision}."
        )
    except Exception as e:
        click.secho(f"Error deciding intent: {str(e)}", err=True, fg="red")
        sys.exit(1)


def _parse_aware_timestamp(value, option):
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise click.BadParameter(
            "must be an ISO-8601 timestamp", param_hint=option
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise click.BadParameter("must be timezone-aware", param_hint=option)
    return parsed


def _intent_migration_protected_paths(
    project_path: str | Path,
    *extra_paths: str | Path,
) -> tuple[Path, ...]:
    root = Path(project_path).resolve()
    return (
        root / INTENTION_DAG_FILE,
        root / REALITY_DAG_FILE,
        root / BACKLOG_FILE,
        *(Path(path).resolve() for path in extra_paths),
    )


def _write_intent_migration_artifact(
    payload: dict[str, Any],
    output: str | Path,
    project_path: str | Path,
    *,
    extra_protected_paths: tuple[str | Path, ...] = (),
) -> None:
    """Persist derived migration evidence without overwriting framework state."""

    write_reconciliation_report(
        payload,
        output,
        protected_paths=_intent_migration_protected_paths(
            project_path,
            *extra_protected_paths,
        ),
    )


@intent.command("inventory")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option(
    "--max-items",
    default=100,
    show_default=True,
    type=click.IntRange(min=0),
    help="Maximum legacy-node details to return while preserving complete totals.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    help="Optional JSON report path; otherwise print the report.",
)
def intent_inventory(project_path, max_items, output):
    """Inventory legacy nodes with bounded detail and complete coverage totals."""

    try:
        report = LegacyIntentMigrator(project_path).inventory(max_items=max_items)
        if output:
            _write_intent_migration_artifact(report, output, project_path)
            click.echo(f"Legacy Intent IR inventory saved to {output}.")
        else:
            click.echo(json.dumps(report, indent=2))
    except Exception as e:
        click.secho(f"Error inventorying legacy intent: {str(e)}", err=True, fg="red")
        sys.exit(1)


@intent.command("plan-migration")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option(
    "--recorded-at",
    required=True,
    help="Timezone-aware ISO-8601 timestamp used for deterministic revision history.",
)
@click.option("--actor", required=True, help="Identity compiling the migration plan.")
@click.option(
    "--generator-version",
    required=True,
    help="Versioned compiler identity stored in each Intent IR revision.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False),
    help="JSON migration-plan path.",
)
def intent_plan_migration(project_path, recorded_at, actor, generator_version, output):
    """Compile every legacy node into a deterministic review-required plan."""

    try:
        timestamp = datetime.fromisoformat(recorded_at)
        plan = LegacyIntentMigrator(project_path).plan(
            recorded_at=timestamp,
            actor=actor,
            generator_version=generator_version,
        )
        _write_intent_migration_artifact(plan, output, project_path)
        click.echo(
            f"Legacy Intent IR migration plan saved to {output} "
            f"for {plan['summary']['planned_migrations']} node(s)."
        )
    except Exception as e:
        click.secho(
            f"Error planning legacy intent migration: {str(e)}", err=True, fg="red"
        )
        sys.exit(1)


@intent.command("apply-migration")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option(
    "--plan-file",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Exact JSON migration plan produced by plan-migration.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    help="Optional JSON result path; otherwise print the result.",
)
def intent_apply_migration(project_path, plan_file, output):
    """Atomically apply one complete, non-stale review-required migration plan."""

    try:
        if output:
            validate_reconciliation_report_output(
                output,
                protected_paths=_intent_migration_protected_paths(
                    project_path,
                    plan_file,
                ),
            )
        with open(plan_file, "r", encoding="utf-8") as handle:
            plan = json.load(handle)
        result = LegacyIntentMigrator(project_path).apply(plan)
        if output:
            try:
                _write_intent_migration_artifact(
                    result,
                    output,
                    project_path,
                    extra_protected_paths=(plan_file,),
                )
            except Exception as error:
                click.secho(
                    "Legacy Intent IR migration committed successfully, but result "
                    f"evidence could not be saved to {output}: {error}",
                    err=True,
                    fg="yellow",
                )
                click.echo(json.dumps(result, indent=2))
                return
            click.echo(f"Legacy Intent IR migration result saved to {output}.")
        else:
            click.echo(json.dumps(result, indent=2))
    except Exception as e:
        click.secho(
            f"Error applying legacy intent migration: {str(e)}", err=True, fg="red"
        )
        sys.exit(1)


@cli.group("mapping")
def mapping():
    """Review and explicitly approve source-bound identity mappings."""


@mapping.command("review")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option("--intent-id", required=True, help="Canonical Intention node GUID.")
@click.option(
    "--candidate-reality-id",
    help="Explicit current observed Reality GUID; omit for automatic name matching.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Render a decision brief for people or the complete machine report.",
)
def mapping_review(project_path, intent_id, candidate_reality_id, output_format):
    """Render fresh source-bound evidence for one mapping decision."""

    try:
        engine = MappingEngine(project_path, Path(project_path) / INTENTION_DAG_FILE)
        report = engine.review(
            intent_id,
            candidate_reality_id=candidate_reality_id,
        )
        if output_format == "json":
            click.echo(json.dumps(report, indent=2))
        else:
            click.echo(render_mapping_review(report))
    except Exception as e:
        click.secho(f"Error reviewing mapping: {str(e)}", err=True, fg="red")
        sys.exit(1)


@mapping.command("approve")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option("--intent-id", required=True, help="Canonical Intention node GUID.")
@click.option(
    "--candidate-reality-id",
    required=True,
    help="Reality candidate GUID from the exact mapping review.",
)
@click.option(
    "--evidence-digest",
    required=True,
    help="Evidence digest from the exact mapping review.",
)
@click.option(
    "--selection-mode",
    type=click.Choice(
        ["automatic_name_match", "explicit_observed_guid"],
        case_sensitive=True,
    ),
    default="automatic_name_match",
    show_default=True,
    help="Candidate selection mode used by the exact mapping review.",
)
@click.option("--approved-by", required=True, help="Identity of the approver.")
@click.option(
    "--approved-at",
    required=True,
    help="Timezone-aware ISO-8601 approval timestamp.",
)
@click.option("--rationale", required=True, help="Reason for approving this mapping.")
def mapping_approve(
    project_path,
    intent_id,
    candidate_reality_id,
    evidence_digest,
    selection_mode,
    approved_by,
    approved_at,
    rationale,
):
    """Approve exactly one fresh candidate and persist verified source evidence."""

    try:
        engine = MappingEngine(project_path, Path(project_path) / INTENTION_DAG_FILE)
        approval = MappingApproval.model_validate(
            {
                "approved_by": approved_by,
                "approved_at": approved_at,
                "rationale": rationale,
            }
        )
        result = engine.approve(
            intent_id,
            candidate_reality_id,
            evidence_digest,
            approval,
            selection_mode=selection_mode,
        )
        click.echo(json.dumps(result, indent=2))
    except Exception as e:
        click.secho(f"Error approving mapping: {str(e)}", err=True, fg="red")
        sys.exit(1)


@mapping.group("receipt")
def mapping_receipt():
    """Review and refresh confirmed source mapping receipts."""


@mapping_receipt.command("review")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option("--intent-id", required=True, help="Confirmed Intention node GUID.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Render a decision brief for people or the complete machine report.",
)
def mapping_receipt_review(project_path, intent_id, output_format):
    """Render fresh maintenance evidence for one confirmed source receipt."""

    try:
        engine = MappingEngine(project_path, Path(project_path) / INTENTION_DAG_FILE)
        report = engine.review_receipt_refresh(intent_id)
        if output_format == "json":
            click.echo(json.dumps(report, indent=2))
        else:
            click.echo(render_receipt_refresh_review(report))
    except Exception as error:
        click.secho(
            f"Error reviewing mapping receipt: {str(error)}",
            err=True,
            fg="red",
        )
        sys.exit(1)


@mapping_receipt.command("check")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json", "github"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Render for people, as the machine report, or as GitHub annotations.",
)
@click.option(
    "--warn-only",
    is_flag=True,
    help="Report stale or invalid receipts without failing.",
)
def mapping_receipt_check(project_path, output_format, warn_only):
    """Report every mapping receipt whose source changed since approval.

    Read-only. Exits 1 when any receipt is stale or invalid, unless
    --warn-only. Refreshing a receipt still needs a named approver.
    """

    try:
        engine = MappingEngine(project_path, Path(project_path) / INTENTION_DAG_FILE)
        report = engine.check_receipts()
    except Exception as error:
        click.secho(
            f"Error checking mapping receipts: {str(error)}",
            err=True,
            fg="red",
        )
        sys.exit(1)
    problems = [r for r in report["receipts"] if r["status"] != "fresh"]
    if output_format == "json":
        click.echo(json.dumps(report, indent=2))
    elif output_format == "github":
        level = "warning" if warn_only else "error"
        for receipt in problems:
            click.echo(
                f"::{level} file={receipt['source_path']},"
                f"line={receipt.get('receipt_line', 1)},"
                f"title={receipt['status'].capitalize()} mapping receipt::"
                + _receipt_problem(receipt)
            )
        click.echo(_receipt_summary(report))
    else:
        click.echo(_receipt_summary(report))
        for receipt in problems:
            click.echo(
                f"  {receipt['status'].upper()}  {receipt['source_path']}:"
                f"{receipt.get('receipt_line', 1)}  {_receipt_problem(receipt)}"
            )
    if problems and not warn_only:
        sys.exit(1)


def _receipt_summary(report):
    summary = report["summary"]
    return (
        f"Mapping receipts: {summary['fresh']} fresh, {summary['stale']} stale, "
        f"{summary['invalid']} invalid."
    )


def _receipt_problem(receipt):
    if receipt["status"] == "invalid":
        return f"The receipt cannot be validated: {receipt['error']}."
    if receipt.get("binding") == "file":
        changed = (
            f"{receipt['source_path']} changed since the mapping receipt for "
            f"{receipt['symbol_name']} was approved. This older receipt binds to "
            "the whole file; refreshing it binds it to the symbol."
        )
    elif receipt.get("error"):
        changed = f"{receipt['error'].capitalize()}."
    else:
        changed = (
            f"{receipt['symbol_name']} changed since its mapping receipt was approved."
        )
    return (
        f"{changed} Review it with `dag-tool mapping receipt review --intent-id "
        f"{receipt['intent_id']}`, then refresh it with a named approver."
    )


@mapping_receipt.command("refresh")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Absolute path to the project directory.",
)
@click.option("--intent-id", required=True, help="Confirmed Intention node GUID.")
@click.option(
    "--evidence-digest",
    required=True,
    help="Evidence digest from the exact receipt review.",
)
@click.option("--approved-by", required=True, help="Identity of the approver.")
@click.option(
    "--approved-at",
    required=True,
    help="Timezone-aware ISO-8601 approval timestamp.",
)
@click.option("--rationale", required=True, help="Reason for refreshing this receipt.")
def mapping_receipt_refresh(
    project_path,
    intent_id,
    evidence_digest,
    approved_by,
    approved_at,
    rationale,
):
    """Refresh exactly one confirmed receipt from approved fresh evidence."""

    try:
        engine = MappingEngine(project_path, Path(project_path) / INTENTION_DAG_FILE)
        approval = MappingApproval.model_validate(
            {
                "approved_by": approved_by,
                "approved_at": approved_at,
                "rationale": rationale,
            }
        )
        result = engine.refresh_receipt(intent_id, evidence_digest, approval)
        click.echo(json.dumps(result, indent=2))
    except Exception as error:
        click.secho(
            f"Error refreshing mapping receipt: {str(error)}",
            err=True,
            fg="red",
        )
        sys.exit(1)


@cli.command()
@click.option(
    "--intention",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Intention DAG yaml file.",
)
@click.option(
    "--reality",
    required=True,
    type=click.Path(exists=True),
    help="Path to the Reality DAG yaml file.",
)
@click.option(
    "--mode",
    type=click.Choice(["safe", "legacy-structural"]),
    default="safe",
    show_default=True,
    help="Use evidence-gated planning or explicitly request legacy structural output.",
)
@click.option(
    "--max-tasks",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Maximum tasks returned by safe planning.",
)
@click.option(
    "--max-candidates",
    type=click.IntRange(min=1),
    default=20,
    show_default=True,
    help="Maximum candidate identities retained in each safe task.",
)
@click.option(
    "--acceptance/--no-acceptance",
    default=True,
    show_default=True,
    help=(
        "Grade acceptance against the evidence.json beside the Intention DAG, so "
        "a confirmed node lacking required evidence stays in the plan (ADR 0003)."
    ),
)
def diff(intention, reality, mode, max_tasks, max_candidates, acceptance):
    """Calculates the diff between Intention DAG and Reality DAG."""
    try:
        intent_manager = DAGManager.load(intention)
        reality_manager = DAGManager.load(reality)
        policy = (
            DiffPolicy.safe(
                max_tasks=max_tasks,
                max_candidates=max_candidates,
            )
            if mode == "safe"
            else DiffPolicy.legacy_structural()
        )
        engine = DiffingEngine(
            intent_manager,
            reality_manager,
            policy=policy,
            evidence=_acceptance_evaluator(intention) if acceptance else None,
        )
        diff_result = engine.calculate_diff()

        click.echo(json.dumps(diff_result, indent=2))
    except Exception as e:
        click.secho(f"Error computing diff: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.command("reconcile")
@click.option(
    "--intention",
    required=True,
    type=click.Path(exists=True),
    help="Path to the canonical Intention DAG yaml file.",
)
@click.option(
    "--reality",
    required=True,
    type=click.Path(exists=True),
    help="Path to the generated Reality DAG yaml file.",
)
@click.option(
    "--max-items",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Maximum evidence records returned without hiding complete totals.",
)
@click.option(
    "--max-candidates",
    type=click.IntRange(min=1),
    default=20,
    show_default=True,
    help="Maximum candidate identities retained in each evidence record.",
)
@click.option(
    "--observed-state",
    type=click.Path(exists=True, dir_okay=False),
    help=(
        "agentic-backlog-kit `abk observe` output to attach as GitHub evidence. "
        "Mapped by canonical GUID; never changes a classification or the "
        "Intention DAG."
    ),
)
@click.option(
    "--evidence",
    "evidence_ledger",
    type=click.Path(exists=True, dir_okay=False),
    help=(
        "Evidence ledger to grade each node's acceptance criteria against "
        "(ADR 0003). Never changes a classification."
    ),
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    help="Atomically write the JSON report instead of printing it.",
)
def reconcile(
    intention,
    reality,
    max_items,
    max_candidates,
    observed_state,
    evidence_ledger,
    output,
):
    """Render a bounded, read-only reconciliation evidence report."""

    try:
        intent_manager = DAGManager.load(intention)
        reality_manager = DAGManager.load(reality)
        observed = load_observed_state(observed_state) if observed_state else None
        evaluator = (
            EvidenceEvaluator(
                load_evidence_ledger(evidence_ledger),
                project_root=_workspace_root(intention),
            )
            if evidence_ledger
            else None
        )
        report = ReconciliationEngine(
            intent_manager,
            reality_manager,
            observed_state=observed,
            evidence=evaluator,
        ).analyze(
            max_items=max_items,
            max_candidates=max_candidates,
        )
        if output:
            write_reconciliation_report(
                report,
                output,
                protected_paths=(intention, reality)
                + ((observed_state,) if observed_state else ())
                + ((evidence_ledger,) if evidence_ledger else ()),
            )
            click.echo(f"Reconciliation report saved to {output}.")
        else:
            click.echo(json.dumps(report, indent=2))
    except Exception as e:
        click.secho(f"Error reconciling DAGs: {str(e)}", err=True, fg="red")
        sys.exit(1)


def _acceptance_ledger_path(intention_path):
    return Path(os.path.abspath(intention_path)).parent / "evidence.json"


def _acceptance_evaluator(intention_path):
    """Evaluate the ledger beside the Intention DAG; missing means empty."""

    return EvidenceEvaluator(
        load_evidence_ledger(_acceptance_ledger_path(intention_path)),
        project_root=_workspace_root(intention_path),
    )


def _workspace_root(intention_path):
    """The project root when the DAG sits in its framework workspace."""

    parent = Path(os.path.abspath(intention_path)).parent
    return parent.parent if parent.name == ".aio-agentic-sdlc" else None


@cli.group("evidence")
def evidence():
    """Record acceptance evidence in the committed ledger (ADR 0003)."""


@evidence.command("record")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to the project containing the canonical framework workspace.",
)
@click.option("--intent-id", required=True, help="Canonical Intention node GUID.")
@click.option("--criterion-id", required=True, help="Acceptance criterion ID.")
@click.option(
    "--reference", required=True, help="The criterion's required evidence reference."
)
@click.option(
    "--level",
    required=True,
    type=click.Choice(
        [
            level.value
            for level in EvidenceLevel
            if level not in (EvidenceLevel.DECLARED, EvidenceLevel.MAPPED)
        ]
    ),
    help="Evidence level this record demonstrates.",
)
@click.option(
    "--locator",
    required=True,
    help="Where the evidence lives: a path, test node ID or URL.",
)
@click.option("--summary", required=True, help="What the evidence shows.")
@click.option("--recorded-by", required=True, help="Identity recording the evidence.")
@click.option("--recorded-at", required=True, help="Timezone-aware ISO-8601 timestamp.")
@click.option("--approved-by", help="The approver; required for approved evidence.")
def evidence_record(
    project_path,
    intent_id,
    criterion_id,
    reference,
    level,
    locator,
    summary,
    recorded_by,
    recorded_at,
    approved_by,
):
    """Append one record bound to an existing acceptance criterion."""

    try:
        root = Path(os.path.abspath(project_path))
        record = EvidenceRecord(
            intent_id=intent_id,
            criterion_id=criterion_id,
            reference=reference,
            level=level,
            locator=locator,
            summary=summary,
            recorded_by=recorded_by,
            recorded_at=recorded_at,
            approved_by=approved_by,
        )
        intention = DAGManager.load(str(root / INTENTION_DAG_FILE))
        count = record_evidence(
            root / EVIDENCE_LEDGER_FILE, intention, record, project_root=root
        )
        click.echo(f"Recorded {level} evidence for {criterion_id} ({count} records).")
    except Exception as e:
        click.secho(f"Error recording evidence: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.command("visualize")
@click.option(
    "--project-path",
    required=True,
    type=click.Path(exists=True, file_okay=False),
    help="Path to the project containing the canonical framework workspace.",
)
@click.option(
    "--view",
    required=True,
    type=click.Choice(["intention", "reality", "comparison"], case_sensitive=False),
    help="DAG view to render.",
)
@click.option("--focus-node", "focus_node_id", help="Canonical node GUID to focus.")
@click.option(
    "--depth",
    type=click.IntRange(min=0),
    default=1,
    show_default=True,
    help="Incoming and outgoing neighborhood depth.",
)
@click.option(
    "--max-items",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Maximum records returned without hiding complete totals.",
)
@click.option(
    "--max-edges",
    type=click.IntRange(min=1),
    default=200,
    show_default=True,
    help="Maximum intended and observed relationships returned per collection.",
)
@click.option(
    "--max-candidates",
    type=click.IntRange(min=1),
    default=20,
    show_default=True,
    help="Maximum identity candidates and nested source locations per record.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "mermaid", "json"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Output rendering format.",
)
def visualize(
    project_path,
    view,
    focus_node_id,
    depth,
    max_items,
    max_edges,
    max_candidates,
    output_format,
):
    """Render canonical DAGs without mutating project or framework state."""

    try:
        engine = DAGVisualizationEngine.from_project(project_path)
        report = engine.build_report(
            view=view,
            focus_node_id=focus_node_id,
            depth=depth,
            max_items=max_items,
            max_edges=max_edges,
            max_candidates=max_candidates,
        )
        click.echo(render_dag(report, output_format))
    except Exception as e:
        click.secho(f"Error visualizing DAGs: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.command("triage")
@click.option(
    "--intention",
    required=True,
    type=click.Path(exists=True),
    help="Path to the canonical Intention DAG yaml file.",
)
@click.option(
    "--reality",
    required=True,
    type=click.Path(exists=True),
    help="Path to the generated Reality DAG yaml file.",
)
@click.option(
    "--decisions",
    type=click.Path(exists=True, dir_okay=False),
    help="Optional digest-bound JSON triage decisions.",
)
@click.option(
    "--max-items",
    type=click.IntRange(min=1),
    default=100,
    show_default=True,
    help="Maximum triage records returned without hiding complete totals.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
    help="Render a human brief or the complete machine report.",
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    help="Atomically write the JSON report instead of printing it.",
)
@click.option(
    "--acceptance/--no-acceptance",
    default=True,
    show_default=True,
    help=(
        "Grade acceptance against the evidence.json beside the Intention DAG, so "
        "a confirmed node lacking required evidence stays in the plan (ADR 0003)."
    ),
)
def triage(intention, reality, decisions, max_items, output_format, output, acceptance):
    """Classify safe reconciliation work before backlog execution."""

    try:
        intent_manager = DAGManager.load(intention)
        reality_manager = DAGManager.load(reality)
        decision_set = None
        if decisions:
            decision_path = guarded_file_path(decisions)
            decision_set = TriageDecisionSet.model_validate_json(
                decision_path.read_text(encoding="utf-8")
            )
        report = DriftTriageEngine(
            intent_manager,
            reality_manager,
            evidence=_acceptance_evaluator(intention) if acceptance else None,
        ).analyze(
            decisions=decision_set,
            max_items=max_items,
        )
        if output:
            protected_paths = [intention, reality]
            if decisions:
                protected_paths.append(decisions)
            if acceptance:
                protected_paths.append(str(_acceptance_ledger_path(intention)))
            write_reconciliation_report(
                report,
                output,
                protected_paths=tuple(protected_paths),
            )
            click.echo(f"Drift triage report saved to {output}.")
        elif output_format.casefold() == "json":
            click.echo(json.dumps(report, indent=2))
        else:
            click.echo(render_drift_triage(report))
    except Exception as e:
        click.secho(
            f"Error triaging reconciliation drift: {str(e)}", err=True, fg="red"
        )
        sys.exit(1)


@cli.command("triage-decide")
@click.option(
    "--intention",
    required=True,
    type=click.Path(exists=True),
    help="Path to the canonical Intention DAG yaml file.",
)
@click.option(
    "--reality",
    required=True,
    type=click.Path(exists=True),
    help="Path to the generated Reality DAG yaml file.",
)
@click.option(
    "--decisions",
    required=True,
    type=click.Path(dir_okay=False),
    help=(
        "Decision file to create, or to add to when it is bound to the current "
        "plan digest."
    ),
)
@click.option(
    "--subject-key",
    required=True,
    help="The triage item's subject key, for example intent:<GUID>.",
)
@click.option(
    "--classification",
    required=True,
    type=click.Choice([c.value for c in DriftClassification]),
)
@click.option("--rationale", required=True, help="Why the person decided this.")
@click.option(
    "--evidence",
    "evidence_refs",
    required=True,
    multiple=True,
    help="What the decision rests on: a path, test or URL. Repeatable.",
)
@click.option("--decided-by", required=True, help="The person deciding.")
@click.option("--decided-at", required=True, help="Timezone-aware ISO-8601 timestamp.")
@click.option(
    "--acceptance/--no-acceptance",
    default=True,
    show_default=True,
    help="Bind to the digest that includes the evidence ledger, as triage does.",
)
def triage_decide(
    intention,
    reality,
    decisions,
    subject_key,
    classification,
    rationale,
    evidence_refs,
    decided_by,
    decided_at,
    acceptance,
):
    """Record one person's triage decision, bound to the current plan digest.

    An existing decision file is added to only while its plan digest is
    current. A stale file is refused, never silently re-bound: its decisions
    were made against a different state and must be re-derived.
    """
    try:
        intent_manager = DAGManager.load(intention)
        reality_manager = DAGManager.load(reality)
        engine = DriftTriageEngine(
            intent_manager,
            reality_manager,
            evidence=_acceptance_evaluator(intention) if acceptance else None,
        )
        digest = engine.source_identity()["plan_digest"]
        decision_path = guarded_file_path(decisions, create_parent=True)
        existing = []
        if decision_path.exists():
            current = TriageDecisionSet.model_validate_json(
                decision_path.read_text(encoding="utf-8")
            )
            if current.plan_digest != digest:
                raise click.ClickException(
                    "the decision file is bound to an older plan digest; its "
                    "decisions must be re-derived against the current state, "
                    "so write this decision to a new file"
                )
            existing = [d for d in current.decisions if d.subject_key != subject_key]
        decision = TriageDecision(
            subject_key=subject_key,
            classification=DriftClassification(classification),
            rationale=rationale,
            evidence=list(evidence_refs),
            decided_by=decided_by,
            decided_at=_parse_aware_timestamp(decided_at, "--decided-at"),
        )
        decision_set = TriageDecisionSet(
            plan_digest=digest,
            decisions=sorted([*existing, decision], key=lambda d: d.subject_key),
        )
        report = engine.analyze(
            decisions=decision_set,
            max_items=max(1, len(intent_manager.nodes) + len(intent_manager.edges)),
        )
        item = next(
            i for i in report["items"] if i["audit"].get("subject_key") == subject_key
        )
        _write_json_atomically(decision_path, decision_set.model_dump(mode="json"))
        authorized = "yes" if item["implementation_authorized"] else "no"
        click.echo(
            f"Recorded {classification} for {subject_key} by {decided_by} in "
            f"{decisions}. Implementation authorized: {authorized}."
        )
    except click.ClickException as e:
        click.secho(f"Error recording triage decision: {e.message}", err=True, fg="red")
        sys.exit(1)
    except Exception as e:
        click.secho(f"Error recording triage decision: {str(e)}", err=True, fg="red")
        sys.exit(1)


def _write_json_atomically(path, payload):
    import tempfile

    target = Path(path)
    fd, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
        os.replace(temporary, target)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise


@cli.command("trace")
@click.option(
    "--project-path",
    default=".",
    show_default=True,
    type=click.Path(exists=True, file_okay=False),
    help="Project containing the framework workspace.",
)
@click.option("--intent-id", required=True, help="Canonical Intention node GUID.")
@click.option(
    "--decisions",
    type=click.Path(exists=True, dir_okay=False),
    help="Digest-bound triage decisions, to show who authorized the work.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"], case_sensitive=False),
    default="markdown",
    show_default=True,
)
@click.option(
    "--output",
    type=click.Path(dir_okay=False),
    help="Write the report to this file instead of printing it.",
)
def trace(project_path, intent_id, decisions, output_format, output):
    """Explain one requirement end to end in plain language. Read-only.

    From the stated want through approval, authorized work, the implementing
    symbol and the evidence for each acceptance criterion, to whether it is
    done.
    """
    try:
        decision_set = None
        if decisions:
            decision_set = TriageDecisionSet.model_validate_json(
                guarded_file_path(decisions).read_text(encoding="utf-8")
            )
        result = build_trace(project_path, intent_id, decisions=decision_set)
        text = (
            json.dumps(result, indent=2) + "\n"
            if output_format == "json"
            else render_trace_markdown(result)
        )
        if output:
            target = guarded_file_path(output, create_parent=True)
            target.write_text(text, encoding="utf-8")
            click.echo(f"Traceability report saved to {output}.")
        else:
            click.echo(text, nl=False)
    except Exception as e:
        click.secho(f"Error building the trace: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.command("demo")
@click.option(
    "--directory",
    required=True,
    type=click.Path(file_okay=False),
    help="An empty or new directory for the throwaway demo project.",
)
@click.option(
    "--approver",
    required=True,
    help="Your name. It is recorded on every approval you give at a gate.",
)
@click.option(
    "--yes",
    is_flag=True,
    help="Approve every gate without asking. Only for unattended runs such as CI.",
)
@click.option(
    "--agent-command",
    help=(
        "Run a real agent CLI instead of the scripted one, for example "
        '"claude -p". The work order arrives on its stdin.'
    ),
)
def demo(directory, approver, yes, agent_command):
    """Take one requirement through the whole loop in a throwaway project.

    Intent, approval, authorized work, implementation by an agent, source
    mapping, tests, evidence and completion, using only public commands. It
    stops at each approval gate and asks you, unless --yes.
    """
    import shlex

    from aio_agentic_sdlc.closed_loop_demo import ClosedLoopDemo, DemoError

    if not yes and not sys.stdin.isatty():
        click.secho(
            "The demo asks for approval at each gate. Run it in a terminal, or "
            "pass --yes for an unattended run.",
            err=True,
            fg="red",
        )
        sys.exit(2)

    def confirm(question):
        if yes:
            click.echo(f"  {question} yes (--yes)")
            return True
        return click.confirm(f"  {question}", default=False)

    try:
        ClosedLoopDemo(
            directory,
            approver=approver,
            confirm=confirm,
            agent_command=shlex.split(agent_command) if agent_command else None,
            echo=click.echo,
        ).run()
    except DemoError as e:
        click.secho(f"The loop did not close: {e}", err=True, fg="red")
        sys.exit(1)


@cli.group("benchmark-intent")
def benchmark_intent():
    """Measure intent translation against the golden corpus (ROADMAP M4)."""


@benchmark_intent.command("score")
@click.option(
    "--translations",
    "runs",
    required=True,
    multiple=True,
    type=click.Path(exists=True, file_okay=False),
    help=(
        "A directory of translations, one <case>.json per case and "
        "<case>.after.json after feedback. Repeat for repeated runs; stability "
        "needs at least two."
    ),
)
@click.option(
    "--corpus",
    type=click.Path(exists=True),
    help="Corpus directory or corpus.yaml. Defaults to the packaged corpus.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "json"], case_sensitive=False),
    default="human",
    show_default=True,
)
def benchmark_intent_score(runs, corpus, output_format):
    """Score translations; exit 1 when a threshold fails. Read-only."""
    from aio_agentic_sdlc.intent_benchmark import (
        BenchmarkError,
        load_corpus,
        render_report,
        score,
    )

    try:
        report = score(load_corpus(corpus), runs)
    except BenchmarkError as e:
        click.secho(f"Error scoring the benchmark: {e}", err=True, fg="red")
        sys.exit(2)
    if output_format == "json":
        click.echo(json.dumps(report, indent=2))
    else:
        click.echo(render_report(report), nl=False)
    if not report["passed"]:
        sys.exit(1)


@benchmark_intent.command("run")
@click.option(
    "--agent-command",
    required=True,
    help='The translator CLI, for example "claude -p". The prompt is on stdin.',
)
@click.option(
    "--output",
    required=True,
    type=click.Path(file_okay=False),
    help="Directory for this run's translations.",
)
@click.option(
    "--corpus",
    type=click.Path(exists=True),
    help="Corpus directory or corpus.yaml. Defaults to the packaged corpus.",
)
@click.option(
    "--timeout",
    type=click.IntRange(min=1),
    default=300,
    show_default=True,
    help="Seconds allowed for each translation.",
)
def benchmark_intent_run(agent_command, output, corpus, timeout):
    """Translate every case with an agent CLI, then score it with `score`."""
    import shlex

    from aio_agentic_sdlc.intent_benchmark import (
        BenchmarkError,
        load_corpus,
        run_translator,
    )

    try:
        failures = run_translator(
            load_corpus(corpus), shlex.split(agent_command), output, timeout=timeout
        )
    except BenchmarkError as e:
        click.secho(f"Error running the translator: {e}", err=True, fg="red")
        sys.exit(2)
    for failure in failures:
        click.secho(f"  {failure}", err=True, fg="yellow")
    click.echo(
        f"Wrote translations to {output}. Score them with: "
        f"dag-tool benchmark-intent score --translations {output}"
    )


@cli.command("export-abk")
@click.option(
    "--intention",
    required=True,
    type=click.Path(exists=True),
    help="Path to the canonical Intention DAG yaml file.",
)
@click.option(
    "--reality",
    required=True,
    type=click.Path(exists=True),
    help="Path to the generated Reality DAG yaml file.",
)
@click.option(
    "--base-manifest",
    required=True,
    type=click.Path(exists=True, dir_okay=False),
    help="Agentic Backlog Kit manifest supplying github, workflow and scoring.",
)
@click.option(
    "--output",
    required=True,
    type=click.Path(dir_okay=False),
    help="Where to write the manifest; may be the base manifest itself.",
)
@click.option(
    "--observed-state",
    type=click.Path(exists=True, dir_okay=False),
    help="`abk observe` document; exported items whose issue is closed are dropped.",
)
@click.option(
    "--decisions",
    type=click.Path(exists=True, dir_okay=False),
    help="Optional digest-bound JSON triage decisions.",
)
def export_abk(intention, reality, base_manifest, output, observed_state, decisions):
    """Project authorized work into an Agentic Backlog Kit manifest (Seam A).

    Writes one manifest file and never calls GitHub: apply it with the kit's
    own plan, confirm and apply flow.
    """

    try:
        decision_set = None
        if decisions:
            decision_set = TriageDecisionSet.model_validate_json(
                guarded_file_path(decisions).read_text(encoding="utf-8")
            )
        observed = load_observed_state(observed_state) if observed_state else None
        base = json.loads(guarded_file_path(base_manifest).read_text(encoding="utf-8"))
        manifest = export_abk_manifest(
            DAGManager.load(intention),
            DAGManager.load(reality),
            base,
            evidence=_acceptance_evaluator(intention),
            decisions=decision_set,
            observed_state=observed,
        )
        write_reconciliation_report(
            manifest,
            output,
            protected_paths=(
                intention,
                reality,
                str(_acceptance_ledger_path(intention)),
                *([decisions] if decisions else []),
                *([observed_state] if observed_state else []),
            ),
        )
        exported = [item for item in manifest["items"] if item.get("guid")]
        click.echo(
            f"Exported {len(exported)} GUID item(s) to {output}. Review and apply "
            "it with the backlog kit's plan and apply flow."
        )
        finished = newly_finished(base, manifest)
        if finished:
            transitions = " ".join(
                f"--transition {item_id}={next(i['status'] for i in manifest['items'] if i['id'] == item_id)}"
                for item_id in finished
            )
            click.echo(
                f"{len(finished)} item(s) left the diff. The kit keeps an existing "
                "card's Status, so move them with its reviewed transition: "
                f"sync-plan {transitions}"
            )
    except Exception as e:
        click.secho(f"Error exporting the ABK manifest: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.command("generate-reality")
@click.option(
    "--dir",
    required=True,
    type=click.Path(exists=True),
    help="Root directory to analyze.",
)
@click.option("--system", default="System", help="Name of the root system node.")
@click.option(
    "--output",
    required=True,
    type=click.Path(),
    help="Path to save the generated Reality DAG yaml file.",
)
def generate_reality(dir, system, output):
    """Generates a Reality DAG by statically analyzing source code in the given directory."""
    try:
        with dag_file_lock(output) as guarded_output:
            generator = RealityDAGGenerator(root_dir=dir, system_name=system)
            reality_dag = generator.generate()
            reality_dag.save(str(guarded_dag_path(guarded_output)))
        click.echo(f"Reality DAG generated and saved to {output}.")
    except Exception as e:
        click.secho(f"Error generating reality DAG: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.group()
def node():
    """Node manipulation commands."""
    pass


@node.command("add")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the DAG yaml file.",
)
@click.option("--id", required=True, help="Node ID")
@click.option(
    "--type",
    required=True,
    type=click.Choice([t.value for t in NodeType]),
    help="Node Type",
)
@click.option("--name", required=True, help="Node Name")
@click.option("--domain", help="Node Domain")
@click.option("--description", help="Node Description")
def node_add(file, id, type, name, domain, description):
    """Add a new node."""
    try:
        node_obj = Node(
            id=id,
            type=NodeType(type),
            name=name,
            domain=domain,
            description=description,
        )
        mutate_dag_file(file, lambda manager: manager.add_node(node_obj))
        click.echo(f"Node '{id}' added successfully.")
    except Exception as e:
        click.secho(f"Error adding node: {str(e)}", err=True, fg="red")
        sys.exit(1)


@node.command("update")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the DAG yaml file.",
)
@click.option("--id", required=True, help="Node ID")
@click.option("--name", help="Node Name")
@click.option("--domain", help="Node Domain")
@click.option("--description", help="Node Description")
def node_update(file, id, name, domain, description):
    """Update an existing node."""
    try:
        mutate_dag_file(
            file,
            lambda manager: manager.update_node(
                id,
                name=name,
                domain=domain,
                description=description,
            ),
        )
        click.echo(f"Node '{id}' updated successfully.")
    except Exception as e:
        click.secho(f"Error updating node: {str(e)}", err=True, fg="red")
        sys.exit(1)


@node.command("remove")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the DAG yaml file.",
)
@click.option("--id", required=True, help="Node ID")
def node_remove(file, id):
    """Remove a node."""
    try:
        mutate_dag_file(file, lambda manager: manager.remove_node(id))
        click.echo(f"Node '{id}' removed successfully.")
    except Exception as e:
        click.secho(f"Error removing node: {str(e)}", err=True, fg="red")
        sys.exit(1)


@node.command("list")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the DAG yaml file.",
)
@click.option("--domain", help="Filter by Domain")
@click.option(
    "--type", type=click.Choice([t.value for t in NodeType]), help="Filter by Type"
)
@click.option(
    "--output",
    type=click.Choice(["json", "text"]),
    default="text",
    help="Output format",
)
def node_list(file, domain, type, output):
    """List nodes."""
    try:
        manager = DAGManager.load(file)
        node_type = NodeType(type) if type else None
        nodes = manager.find_nodes(domain=domain, type=node_type)

        if output == "json":
            click.echo(
                json.dumps(
                    [n.model_dump(mode="json", exclude_none=True) for n in nodes],
                    indent=2,
                )
            )
        else:
            for n in nodes:
                click.echo(f"{n.id} ({n.type.value}) - {n.name}")
    except Exception as e:
        click.secho(f"Error listing nodes: {str(e)}", err=True, fg="red")
        sys.exit(1)


@cli.group()
def edge():
    """Edge manipulation commands."""
    pass


@edge.command("add")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the DAG yaml file.",
)
@click.option("--source", required=True, help="Source Node ID")
@click.option("--target", required=True, help="Target Node ID")
@click.option(
    "--type",
    required=True,
    type=click.Choice([t.value for t in EdgeType]),
    help="Edge Type",
)
@click.option("--description", help="Edge Description")
def edge_add(file, source, target, type, description):
    """Add an edge."""
    try:
        edge_obj = Edge(
            source=source, target=target, type=EdgeType(type), description=description
        )
        mutate_dag_file(file, lambda manager: manager.add_edge(edge_obj))
        click.echo(f"Edge {source} -> {target} ({type}) added successfully.")
    except Exception as e:
        click.secho(f"Error adding edge: {str(e)}", err=True, fg="red")
        sys.exit(1)


@edge.command("remove")
@click.option(
    "--file",
    required=True,
    type=click.Path(exists=True),
    help="Path to the DAG yaml file.",
)
@click.option("--source", required=True, help="Source Node ID")
@click.option("--target", required=True, help="Target Node ID")
@click.option(
    "--type",
    required=True,
    type=click.Choice([t.value for t in EdgeType]),
    help="Edge Type",
)
def edge_remove(file, source, target, type):
    """Remove an edge."""
    try:
        mutate_dag_file(
            file,
            lambda manager: manager.remove_edge(source, target, EdgeType(type)),
        )
        click.echo(f"Edge {source} -> {target} ({type}) removed successfully.")
    except Exception as e:
        click.secho(f"Error removing edge: {str(e)}", err=True, fg="red")
        sys.exit(1)


if __name__ == "__main__":
    cli()


@cli.command("doctor")
@click.option(
    "--project",
    "project_path",
    default=".",
    type=click.Path(file_okay=False),
    help="Project to check. Defaults to the current directory.",
)
@click.option(
    "--no-mcp",
    is_flag=True,
    help="Skip the MCP handshake (it starts the server once).",
)
@click.option("--timeout", default=60.0, show_default=True, help="Seconds for MCP.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def doctor(project_path, no_mcp, timeout, output_format):
    """Check the installation and project state; exit 1 on a failure. Read-only."""
    from aio_agentic_sdlc.install_check import render_doctor, run_doctor

    report = run_doctor(project_path, mcp=not no_mcp, timeout=timeout)
    if output_format == "json":
        click.echo(json.dumps(report, indent=2))
    else:
        click.echo(render_doctor(report))
    sys.exit(0 if report["passed"] else 1)
