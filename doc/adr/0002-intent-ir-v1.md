# ADR 0002: Intent IR v1

- Status: Accepted
- Date: 2026-07-23

## Context

The Intention DAG identifies desired components and relationships, but its existing node fields do
not explain where an interpretation came from, which assumptions or ambiguities shaped it, what
observable evidence would satisfy it, or whether anyone approved it. Agents could therefore
produce structurally valid YAML that was difficult to audit and easy to overstate.

## Decision

Intention DAG nodes may carry an `intent` payload conforming to the strict, versioned Intent IR v1
schema. The payload records:

- one or more provenance statements with durable source references;
- explicit assumptions, unresolved or resolved ambiguities, and bounded confidence;
- uniquely identified acceptance criteria with at least one required evidence reference each;
- a monotonic revision history with the responsible actor and generator version;
- the currently responsible agent and generator version; and
- an explicit draft, review-required, approved, or rejected state with approval audit fields.

Unknown fields fail validation. Revision history starts at one and increases strictly. Approved
intent requires both an approver and approval timestamp. Existing DAG nodes remain loadable without
an Intent IR payload during migration, while `dag-tool validate-intent` defaults to strict coverage
and fails when any node is missing the payload.

`dag-tool intent-summary` renders the interpretation for review without requiring a person to read
or edit raw graph YAML. State mutation remains the responsibility of framework tools; these review
and validation commands do not mutate the DAG.

## Consequences

- Human statements and imported sources remain traceable through subsequent agent transformations.
- Acceptance criteria state their required evidence before implementation is judged complete.
- Low-confidence interpretations and open ambiguities are visible before downstream execution.
- Legacy DAGs can migrate incrementally, but they do not pass strict Intent IR validation.
- Intake and Cartographer still need deterministic creation and revision tools before the framework
  can fully dogfood its roadmap.

## Alternatives Considered

- Storing the fields in the existing free-form `attributes` dictionary was rejected because it
  cannot provide a stable, validated contract.
- Requiring every existing node to migrate immediately was rejected because it would make current
  projects unreadable before framework-managed migration tooling exists.
- Treating confidence or approval as prose was rejected because downstream policy needs bounded,
  machine-readable values.
