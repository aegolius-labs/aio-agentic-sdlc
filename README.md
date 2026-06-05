# Agentic Backlog Manager

A deterministic, 3-Dimensional Impact/Effort/Dependency backlog manager designed for AI/Agentic workflows.

It replaces token-heavy LLM prioritization of Markdown files with a strict, deterministic JSON-based tracking system. It calculates recursive dependency scores, performs topological sorting to ensure prerequisites come first, and auto-generates human-readable Markdown exports.

## Licensing Note

This project is intended for **Personal / Non-Commercial Use Only**. When you publish this to GitHub, it is highly recommended to select a license like the **PolyForm Noncommercial License 1.0.0** or **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** from the GitHub license templates.

## Usage without Installation (`uvx`)

Because this project is properly packaged with `pyproject.toml`, you do not need to install it to use it! If you have `uv` installed, you can simply run it on-demand anywhere:

```bash
uvx agentic-backlog init
uvx agentic-backlog add "my-feature" --impact 5 --effort 3 --category "Security" --requires "prereq-feature"
uvx agentic-backlog prioritize
uvx agentic-backlog export
```

`uvx` will automatically download, cache, and execute the tool, doing its thing and leaving no mess behind.

## Integrations (OpenSpec & Spec-Kit)

Future development of this tool aims to integrate directly with `open-spec` and `spec-kit`. The vision is to allow `agentic-backlog init` to automatically detect an OpenSpec workspace, read existing `.openspec.yaml` changes, and intelligently seed the `backlog.json`.

*(See `TASKS_FOR_NEXT_AGENT.md` for integration implementation details.)*
