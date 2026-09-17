# Repository guidance

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

## Codex plugin

- The distributable Codex plugin lives under `plugins/aio-agentic-sdlc/`.
- The repo-scoped marketplace is `.agents/plugins/marketplace.json`.
- Project-scoped named agents live under `.codex/agents/` and adapt the legacy Antigravity roles.
- Validate plugin changes with the plugin and skill validators documented in
  `doc/codex-plugin.md`.
