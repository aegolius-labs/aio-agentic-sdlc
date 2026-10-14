# Repository guidance

## Start here

This file is the entry point. Read the documents below for the question you have, in this
order when you are new to the repository.

| Read | When you need to know |
| --- | --- |
| `doc/VISION.md` | Why the framework exists: the backlog is the diff of the Intention and Reality DAGs. Read before any architectural change. |
| `doc/authority-model.md` | Which layer owns which kind of truth, and why evidence never becomes intent. Normative. |
| `doc/architecture.md` | Repository layout, data flow, and how framework detection and SDD reconciliation fit together. |
| `doc/adr/0001-versioned-local-state.md` | How backlog writes are locked, revisioned, journaled, and recovered. |
| `doc/adr/0002-intent-ir-v1.md` | The Intent IR contract: provenance, ambiguity, confidence, acceptance evidence, approval states. |
| `doc/mapping-review.md` | What approving an Intention-to-source mapping does and does not mean. |
| `doc/dag-visualization.md` | Read-only views for comparing the two DAGs without parsing raw YAML. |
| `doc/claude-code-plugin.md` | Using the MCP server and plugin from Claude Code or Claude Desktop. |
| `doc/codex-plugin.md` | Using the plugin from Codex, and validating plugin or skill changes. |
| `README.md` | Installation, the backlog CLI, and the `dag-tool` command reference. |
| `plugins/aio-agentic-sdlc/skills/manage-sdlc/` | The operational workflow and role references agents follow. |

`doc/research/` and `doc/research_agent_customization.md` are dated research notes. They
explain past decisions but are not normative; prefer the documents above when they disagree.

## Log before you implement

Do not implement work that is not in the backlog. In this framework the backlog is the
computed diff between the Intention DAG and the Reality DAG, so "logging" means making the
work visible in that diff, not appending to a list:

- A new want enters as Intention through the Intake role and the approval-gated Intent IR
  tools, never as code first. Code with no accepted intent is Intention drift.
- Reconciliation work proceeds only when `triage_reconciliation_drift` classifies it as
  `missing_implementation` with `implementation_authorized: true`.
- Record the work item with the backlog tools (`add_task` or `aio-sdlc add`) and claim it
  with `get_next_task` or `update_task_status` before changing product code.
- An observed defect, closed issue, or QA finding is evidence. It may inform Reality or the
  backlog; it must not be filed as new intent to justify unlogged work.

If a user explicitly asks for a change outside this flow, say that it bypasses the backlog
and confirm before proceeding.

## Environment

- Use UV for Python dependency management and command execution.
- Create the development environment with `uv sync --frozen --group dev`.
- Run tests with `uv run --no-sync pytest` after the environment is synchronized.

## Organization authority model

- `doc/authority-model.md` is the normative statement of which Aegolius Labs
  repository owns which kind of truth. Read it before changing anything that
  touches the backlog projection or QA handoff boundary.
- This repository owns intent, reality, and the derived work diff.
  `agentic-backlog-kit` owns the GitHub projection of that work;
  `agentic-qa-kit` owns QA evidence.
- Downstream state flows back as evidence, never as intent. An external tracker
  or QA result may inform the Reality DAG or the derived backlog; it may never
  edit the Intention DAG outside an approval-gated Intent IR transition.

## State integrity

- Never edit `.aio-agentic-sdlc/intention-dag.yaml`,
  `.aio-agentic-sdlc/reality-dag.yaml`, or backlog state manually.
- Use the `aio-agentic-sdlc` MCP tools, CLI, or Python API for every state transition.
- Preserve canonical GUID traceability across DAG nodes, specs, and source markers.
- Generate and promote framework documents through the provided tools; do not hand-edit
  generated frontmatter.

## Engineering workflow

- Work on a feature branch, use test-driven development, and minimize the blast radius.
- Use Conventional Commits when the user asks for a commit.
- Inspect status and diffs before staging; never use blind staging commands.
- Do not push, open pull requests, or mutate external trackers unless the user authorizes it.
- Lint changed Markdown with Markdownlint when it is available.

## Host plugins

- The distributable plugin lives under `plugins/aio-agentic-sdlc/` and serves both hosts
  from one shared `skills/` body. Never fork skill content per host, and keep
  host-specific wording in the manifests.
- Codex: `.codex-plugin/plugin.json`, marketplace `.agents/plugins/marketplace.json`.
- Claude Code: `.claude-plugin/plugin.json`, marketplace `.claude-plugin/marketplace.json`
  at the repository root. See `doc/claude-code-plugin.md`.
- `tests/test_host_manifest_parity.py` enforces that the two manifests agree.
- Project-scoped named agents live under `.codex/agents/` and adapt the legacy Antigravity roles.
- Validate plugin changes with the plugin and skill validators documented in
  `doc/codex-plugin.md`.
