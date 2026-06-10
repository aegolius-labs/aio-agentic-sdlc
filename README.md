# Agentic Backlog Manager

A deterministic, 3-Dimensional Impact/Effort/Dependency backlog manager designed for AI/Agentic workflows.

It replaces token-heavy LLM prioritization of Markdown files with a strict, deterministic JSON-based tracking system. It calculates recursive dependency scores, performs topological sorting to ensure prerequisites come first, and auto-generates human-readable Markdown exports.

## Licensing Note

This project is intended for **Personal / Non-Commercial Use Only**. When you publish this to GitHub, it is highly recommended to select a license like the **PolyForm Noncommercial License 1.0.0** or **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** from the GitHub license templates.

## Installation & Usage for Agents (Agy, etc.)

This tool is distributed globally via PyPI, making it extremely easy for autonomous coding agents (like Agy) to install and use without local source code dependency.

You can install it globally in milliseconds using `uv`:

```bash
uv tool install agentic-backlog
```

Or using `pipx`:

```bash
pipx install agentic-backlog
```

Once installed globally, you can invoke it from anywhere in your workspace:

```bash
agentic-backlog init
agentic-backlog add "my-feature" --impact 5 --effort 3 --category "Security" --requires "prereq-feature"
agentic-backlog prioritize
agentic-backlog next
agentic-backlog export
```

## Integrations (OpenSpec & Spec-Kit)

`agentic-backlog` natively integrates with **Open-Spec** and **Spec-Kit** frameworks. When you run `agentic-backlog init` inside a workspace utilizing these frameworks (e.g. detecting `tasks.md` or `specs/*.md` files), the CLI will automatically parse your Markdown checklists and seed them dynamically into the resulting JSON tracking structure.
