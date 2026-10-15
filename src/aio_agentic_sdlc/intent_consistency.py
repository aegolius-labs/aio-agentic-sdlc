"""Read-only self-consistency checks over the Intention DAG (layer 1).

Reconciliation compares intent with Reality, and Intent IR validation checks
each node against its schema. Neither notices an Intention DAG that disagrees
with itself, and a self-contradictory Intention DAG makes every computed diff
wrong. These checks are deterministic and advisory: they never mutate state,
and they do not judge whether two prose statements contradict each other.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import EdgeType, Node, NodeType
from aio_agentic_sdlc.intent_ir import AmbiguityStatus, ApprovalState
from aio_agentic_sdlc.reconciliation import normalize_node_name

CONSISTENCY_SCHEMA_VERSION = 1
DEFAULT_MAX_ITEMS = 100

SEVERITY_ORDER = ("error", "warning", "info")

# Breadth of each node type in the containment hierarchy. A node may contain
# nodes of equal or narrower breadth; containing a broader node is inverted.
HIERARCHY_BREADTH = {
    NodeType.SYSTEM: 0,
    NodeType.CONTAINER: 1,
    NodeType.AGENT: 1,
    NodeType.MODULE: 2,
    NodeType.COMPONENT: 3,
    NodeType.ENDPOINT: 3,
    NodeType.ENTITY: 3,
}

# Relationships where the source relies on the target existing as intended.
RELIANCE_EDGES = {
    EdgeType.DEPENDS_ON,
    EdgeType.CALLS,
    EdgeType.READS,
    EdgeType.WRITES,
    EdgeType.SUBSCRIBES,
    EdgeType.IMPLEMENTS,
}

LIMITATIONS = (
    "Whether two acceptance criteria or descriptions contradict in meaning is "
    "not judged; prose contradiction needs human review.",
    "Overlap is detected only from identical normalized names or descriptions, "
    "not from semantic similarity.",
)


class IntentConsistencyError(ValueError):
    """The Intention DAG cannot be checked."""


def _approval_state(node: Node) -> str | None:
    if node.intent is None:
        return None
    return node.intent.approval.state.value


def _label(node: Node) -> dict[str, str]:
    return {"id": node.id, "type": node.type.value, "name": node.name}


def _normalized_text(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _finding(
    check: str,
    severity: str,
    message: str,
    nodes: list[Node],
    **evidence: Any,
) -> dict[str, Any]:
    finding = {
        "check": check,
        "severity": severity,
        "message": message,
        "nodes": [_label(node) for node in nodes],
    }
    if evidence:
        finding["evidence"] = evidence
    return finding


class IntentConsistencyChecker:
    """Report internal contradictions in one Intention DAG without mutating it."""

    def __init__(self, intention: DAGManager):
        intention.validate()
        self.intention = intention

    def _source_digest(self) -> str:
        payload = {
            "nodes": [
                self.intention.nodes[node_id].model_dump(mode="json")
                for node_id in sorted(self.intention.nodes)
            ],
            "edges": sorted(
                (edge.source, edge.target, edge.type.value)
                for edge in self.intention.edges
            ),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def _ordered_nodes(self) -> list[Node]:
        return [
            self.intention.nodes[node_id] for node_id in sorted(self.intention.nodes)
        ]

    def _duplicate_names(self) -> list[dict[str, Any]]:
        groups: dict[tuple[NodeType, str], list[Node]] = defaultdict(list)
        for node in self._ordered_nodes():
            normalized = normalize_node_name(node.name)
            if normalized:
                groups[(node.type, normalized)].append(node)
        return [
            _finding(
                "duplicate_intent",
                "warning",
                f"{len(nodes)} {node_type.value} nodes share the normalized name "
                f"'{normalized}'; reconciliation cannot tell them apart.",
                nodes,
                normalized_name=normalized,
            )
            for (node_type, normalized), nodes in sorted(
                groups.items(), key=lambda item: (item[0][0].value, item[0][1])
            )
            if len(nodes) > 1
        ]

    def _duplicate_descriptions(self) -> list[dict[str, Any]]:
        groups: dict[str, list[Node]] = defaultdict(list)
        for node in self._ordered_nodes():
            normalized = _normalized_text(node.description)
            if normalized:
                groups[normalized].append(node)
        return [
            _finding(
                "overlapping_intent",
                "warning",
                f"{len(nodes)} nodes carry the same description and may state "
                "the same intent twice.",
                nodes,
            )
            for _, nodes in sorted(groups.items())
            if len(nodes) > 1
        ]

    def _hierarchy(self) -> list[dict[str, Any]]:
        findings = []
        parents: dict[str, list[Node]] = defaultdict(list)
        for edge in self.intention.edges:
            if edge.type != EdgeType.CONTAINS:
                continue
            parent = self.intention.nodes[edge.source]
            child = self.intention.nodes[edge.target]
            parents[child.id].append(parent)
            if HIERARCHY_BREADTH[child.type] < HIERARCHY_BREADTH[parent.type]:
                findings.append(
                    _finding(
                        "hierarchy_inversion",
                        "warning",
                        f"{parent.type.value.capitalize()} '{parent.name}' contains "
                        f"the broader {child.type.value} '{child.name}'.",
                        [parent, child],
                    )
                )
        for child_id in sorted(parents):
            if len(parents[child_id]) > 1:
                child = self.intention.nodes[child_id]
                findings.append(
                    _finding(
                        "multiple_parents",
                        "error",
                        f"{child.type.value.capitalize()} '{child.name}' is "
                        f"contained by {len(parents[child_id])} parents, so its "
                        "place in the hierarchy is ambiguous.",
                        [child, *sorted(parents[child_id], key=lambda n: n.id)],
                    )
                )
        return findings

    def _approval_contradictions(self) -> list[dict[str, Any]]:
        findings = []
        approved = ApprovalState.APPROVED.value
        rejected = ApprovalState.REJECTED.value
        for edge in sorted(
            self.intention.edges,
            key=lambda e: (e.source, e.target, e.type.value),
        ):
            source = self.intention.nodes[edge.source]
            target = self.intention.nodes[edge.target]
            source_state = _approval_state(source)
            target_state = _approval_state(target)
            if (
                edge.type in RELIANCE_EDGES
                and source_state == approved
                and target_state == rejected
            ):
                findings.append(
                    _finding(
                        "approval_contradiction",
                        "error",
                        f"Approved '{source.name}' {edge.type.value} rejected "
                        f"'{target.name}'.",
                        [source, target],
                        relation=edge.type.value,
                    )
                )
            if (
                edge.type == EdgeType.CONTAINS
                and source_state == rejected
                and target_state == approved
            ):
                findings.append(
                    _finding(
                        "approval_contradiction",
                        "error",
                        f"Approved '{target.name}' is contained by rejected "
                        f"'{source.name}'.",
                        [source, target],
                        relation=edge.type.value,
                    )
                )
        return findings

    def _intent_payloads(self) -> list[dict[str, Any]]:
        findings = []
        for node in self._ordered_nodes():
            intent = node.intent
            if intent is None:
                continue
            open_questions = [
                ambiguity.question
                for ambiguity in intent.ambiguities
                if ambiguity.status == AmbiguityStatus.OPEN
            ]
            if intent.approval.state == ApprovalState.APPROVED and open_questions:
                findings.append(
                    _finding(
                        "approved_with_open_ambiguity",
                        "warning",
                        f"Approved '{node.name}' still has {len(open_questions)} "
                        "open ambiguity; approval and the open question disagree.",
                        [node],
                        open_ambiguities=open_questions,
                    )
                )
            description = _normalized_text(node.description)
            restated = [
                criterion.id
                for criterion in intent.acceptance_criteria
                if description and _normalized_text(criterion.statement) == description
            ]
            if restated:
                findings.append(
                    _finding(
                        "criterion_restates_description",
                        "info",
                        f"'{node.name}' has an acceptance criterion that only "
                        "restates its description, so it names no observable "
                        "outcome beyond the description.",
                        [node],
                        criterion_ids=restated,
                    )
                )
        return findings

    def analyze(self, *, max_items: int = DEFAULT_MAX_ITEMS) -> dict[str, Any]:
        """Return a bounded report with complete totals."""

        if isinstance(max_items, bool) or not isinstance(max_items, int):
            raise TypeError("max_items must be an integer")
        if max_items < 1:
            raise IntentConsistencyError("max_items must be at least 1")

        findings = [
            *self._approval_contradictions(),
            *self._hierarchy(),
            *self._duplicate_names(),
            *self._duplicate_descriptions(),
            *self._intent_payloads(),
        ]
        findings.sort(key=lambda f: SEVERITY_ORDER.index(f["severity"]))

        by_severity = {severity: 0 for severity in SEVERITY_ORDER}
        by_check: dict[str, int] = defaultdict(int)
        for finding in findings:
            by_severity[finding["severity"]] += 1
            by_check[finding["check"]] += 1

        returned = findings[:max_items]
        return {
            "schema_version": CONSISTENCY_SCHEMA_VERSION,
            "source": {
                "intention_sha256": self._source_digest(),
                "intention_nodes": len(self.intention.nodes),
                "intention_edges": len(self.intention.edges),
            },
            "summary": {
                "findings": len(findings),
                "by_severity": by_severity,
                "by_check": dict(sorted(by_check.items())),
            },
            "limit": {
                "max_items": max_items,
                "total_items": len(findings),
                "returned_items": len(returned),
                "truncated": len(returned) < len(findings),
            },
            "findings": returned,
            "limitations": list(LIMITATIONS),
        }


def render_intent_consistency(report: dict[str, Any]) -> str:
    """Render a short human brief of a consistency report."""

    summary = report["summary"]
    severity = summary["by_severity"]
    lines = [
        "Intention DAG consistency",
        "",
        f"{report['source']['intention_nodes']} nodes, "
        f"{report['source']['intention_edges']} edges checked.",
        f"Findings: {summary['findings']} "
        f"({severity['error']} error, {severity['warning']} warning, "
        f"{severity['info']} info)",
    ]
    limit = report["limit"]
    if limit["truncated"]:
        lines.append(
            f"Showing {limit['returned_items']} of {limit['total_items']} findings."
        )
    for finding in report["findings"]:
        names = ", ".join(f"'{node['name']}'" for node in finding["nodes"])
        lines.extend(
            [
                "",
                f"- [{finding['severity']}] {finding['check']}: {names}",
                f"  {finding['message']}",
            ]
        )
    lines.extend(["", "Not checked:"])
    lines.extend(f"- {limitation}" for limitation in report["limitations"])
    return "\n".join(lines)
