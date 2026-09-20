# Bridging the Intention and Reality altitudes

Status: research note. No implementation is proposed here, and nothing in this
document is accepted intent.

## Why this exists

`doc/VISION.md` requires that the Reality DAG "maps 1:1 with the ontology and schema of
the Intention DAG" so an accurate diff can be computed. Running the framework against
itself shows that requirement is not met, and measurement suggests the requirement
itself is the wrong target.

Reconciliation of this repository against its own source:

```
intention_nodes: 61      confirmed: 10
reality_nodes: 756       candidate: 0
                         unmapped: 51
                         unclassified_reality: 746
```

Zero candidates. Every Intention node that can be matched by the current rule already
carries an approved receipt, so the review queue is empty — not because the work is
done, but because nothing else is matchable.

## What the current rule does

`reconciliation.py:41` normalizes a name by NFKC-folding it and discarding every
non-alphanumeric character. A candidate requires **exact `(type, normalized_name)`
equality** and **uniqueness** (`reconciliation.py:173`).

Reality's types come from `parsers/visitors.py`:

| Type | Rule |
| --- | --- |
| `entity` | class whose base name is `BaseModel`, `Model` or `Entity` (line 118) |
| `endpoint` | function decorated `get`/`post`/`put`/`delete`/`patch`/`route`/`endpoint` (line 193) |
| `component` | every other class and function |
| `module` | one per source file |
| `agent` | markdown agent definitions |
| `container` | **never emitted** |

## The altitude mismatch

The two graphs describe the same system at different levels, and collide on shared
vocabulary:

| Type | Intention means | Reality means |
| --- | --- | --- |
| `agent` | `SDLC Architect Agent` | `sdlc_architect` |
| `entity` | `Inbox Directory`, `Unified Configuration File` | `Metadata`, `Node`, `MappingApproval` — Pydantic models |
| `endpoint` | `Health Check Endpoint`, `Telemetry Backend` | `test_plan_cmd_with_inbox_files` — pytest functions |

Intention is architectural: components, containers, directories, configuration, agent
roles. Reality is symbol-level: classes, functions, modules. Exact name matching bridges
them only where an architectural component happens to be implemented as one
identically-named class. That is 6 of 61 nodes, by coincidence.

A strict 1:1 ontology is therefore not merely unmet; it is the wrong requirement.
Mapping an architectural node onto a single symbol discards the fact that most
architectural concerns are implemented by *several* symbols, and some — directories,
configuration files, agent definitions — by no Python symbol at all.

## Measured strategies

All figures are against the 55 Intention nodes with no exact match, on this repository.

| Strategy | Matches | Notes |
| --- | --- | --- |
| Exact `(type, name)` — current | 6 | already all confirmed; yields 0 new candidates |
| Strip trailing noun (`agent`, `directory`, …) | 9 | +3 agents only |
| Module-name match | 1 | `MCP Server` → `mcp_server.py` |
| Name only, type ignored | 0 | every hit is contested, so uniqueness rejects it |
| Embedding, single symbol | 29 at ≥0.50 | ranks well; discriminates absence |
| Embedding, module bundle | 17 at ≥0.50 | reaches architectural altitude; dilutes |

### Syntactic strategies are exhausted

Normalization tuning buys three nodes. It adds `SDLC Intake/Architect/Researcher Agent`
and stops: `Implementer Agent` still misses `sdlc_implementer`, `Specialized QA Agents`
still misses `sdlc_qa`. This is worth doing for its own sake, but it is not the
bottleneck and should not be mistaken for one.

### Embedding over single symbols

Using the model already shipped for `check_duplicate_prd`, over the 172 Reality nodes
carrying real docstrings rather than generated stubs:

| Threshold | Matches |
| --- | --- |
| ≥ 0.70 | 2 |
| ≥ 0.60 | 10 |
| ≥ 0.50 | 29 |
| ≥ 0.40 | 43 |

Correct at the top: `SDLC Researcher Agent → sdlc_researcher` (0.838),
`SDLC Architect Agent → sdlc_architect` (0.747),
`DAG Visualization and Comparison → DAGVisualizationEngine` (0.640).

Wrong in the same band: `Agentic Orchestrator Loop [container] → sdlc_orchestrator
[agent]` (0.650), `AST Visitor → RealityDAGGenerator` (0.588, the real answer is
`visitors.py`).

The useful property is at the bottom. Unimplemented intent scores lowest —
`EULA & Privacy Prompt` 0.266, `Telemetry Backend` 0.296, `Health Check Endpoint` 0.321.
**Similarity discriminates "not built yet" from "built elsewhere",** which is exactly the
judgment the diff needs to make and currently cannot.

### Embedding over module bundles

Aggregating each module with its descendants' names and docstrings — 77 bundles
averaging 8.6 symbols — and matching Intention against those:

Reaches altitudes single symbols cannot. `Agentic Orchestrator Loop`, a `container`,
matched `orchestrator_loop.py` at 0.673 — and `container` is a type Reality never emits,
so no symbol-level rule could ever have matched it. Also correct:
`Legacy Intent IR Migration → intent_ir.py` (0.686),
`Evidence-Gated Reconciliation Base → reconciliation.py` (0.610),
`Approval-Gated Source Mapping → mapping.py` (0.528).

Three failure modes appeared:

1. **Large modules act as attractors.** `dag_cli.py`, at 29 symbols, was top match for
   five unrelated Intention nodes. Averaging many symbols produces a vague centroid
   close to everything.
2. **Absence detection is lost.** `Parallel Task Runner`, which does not exist, matched
   `orchestrator_loop.py` at 0.560 — comfortably inside the plausible band. The property
   that made single-symbol embedding valuable disappears under aggregation.
3. **Tests win.** `Markdown Parser` matched `test_markdown_parser_adversarial` (0.615)
   rather than the parser itself.

## Test pollution

**432 of 756 Reality nodes — 57 percent — are test code.**

| | Nodes |
| --- | --- |
| Test | 432 (382 component, 47 module, 3 endpoint) |
| Non-test | 324 (272 component, 34 module, 10 agent, 7 entity, 1 system) |

The Reality DAG is defined as what the software *is*. Tests are evidence *about* the
software, which the authority model places at layer 5. Their presence more than doubles
the candidate pool, degrades every matching strategy measured above, and produces all
three false `endpoint` classifications.

Separately, those three false endpoints are a defect: `@patch(...)` from `unittest.mock`
matches the HTTP `patch` decorator name at `visitors.py:193`.

## Structural matching is not currently possible

Reality edges: **755 `contains`, 3 `depends_on`.** Intention edges: 28 `contains`,
30 `calls`, 19 `reads`, 17 `depends_on`, 9 `writes`.

Reality is a containment tree with essentially no relational structure, so matching by
graph shape has nothing to match against. This could change — the parser already walks
call and import syntax — but as generated today, structural matching is unavailable.

## Options

### A. Relax 1:1 to one-to-many

An Intention node maps to a *set* of Reality symbols rather than one. A receipt becomes
"these symbols constitute this node's implementation" instead of "this symbol is its
canonical identity".

Fits the evidence: most architectural concerns span several symbols. Costs a schema
change to the receipt model and a harder review question — completeness of a set is
more work to judge than identity of a symbol.

### B. Emit architectural nodes in Reality

The generator aggregates symbols into module- and package-level nodes, so Reality
carries both altitudes and `container` becomes expressible.

Measured to work where it matters, and the only approach that reached `container`.
Requires deciding aggregation boundaries, and the attractor problem needs a mitigation —
weighting by specificity, or splitting large modules.

### C. Deepen the Intention DAG

Generate intent down to symbol level so both sides sit at the same altitude.

Rejected on the evidence. Reality has 756 nodes against Intention's 61. An agent
authoring intent at that granularity approaches writing the implementation, which is the
token cost the framework exists to avoid, and it would make Intention a description of
code rather than a statement of purpose.

### D. Semantic candidate generation with human arbitration

Use embeddings to *rank* candidates and let the existing approval gate decide. The
framework already requires human approval with an evidence digest, so automatic
precision was never the requirement — *candidates worth reviewing* is.

This is the cheapest path from a zero-length queue to a working one: 29 candidates at
≥0.50 today, against 0 now. Precision at the top of the ranking is imperfect, which is
acceptable when the next step is a human decision brief and `defer` is the default.

### E. Explicit markers as the escape hatch

`# aio-sdlc-node:` GUID markers already exist, 12 of them, and bind a symbol to an
Intention node with no inference at all. Always correct, never discovers anything,
scales by hand. Useful as the fallback for nodes no strategy can reach.

## What the measurements suggest

No single strategy is sufficient, and the two embedding approaches fail in complementary
ways: single-symbol is precise and detects absence but cannot reach architectural nodes;
bundling reaches them but dilutes and loses absence detection. Running both and
presenting both to the reviewer preserves each one's strength.

Two findings are independent of which direction is chosen and would improve any of them:

- Excluding tests removes 57 percent of the candidate pool and all three false endpoints.
- Fixing the `patch` decorator collision is a bounded defect fix inside existing intent.

## Reproducing

Scripts used for these measurements were scratch, not committed. Each reads
`.aio-agentic-sdlc/intention-dag.yaml` and `.aio-agentic-sdlc/reality-dag.yaml`, uses
`reconciliation.normalize_node_name` for syntactic strategies and
`semantic_dedup.get_model` for embedding strategies, and reports match counts at fixed
thresholds. Figures are specific to this repository at Reality DAG generation time and
should be re-measured before being relied on.
