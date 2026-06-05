---
name: agentic-backlog
description: "Deterministic 3D Matrix Backlog Manager for Agentic Workflows. Use this skill to interact with the project backlog."
---

# Agentic Backlog Skill

This repository uses `agentic-backlog` to manage its tasks deterministically.

## Instructions

To interact with the project backlog, **ALWAYS** use the following command structure:

```bash
uvx agentic-backlog <command> [args]
```

This ensures the CLI is dynamically executed via `uvx` even if it is not installed in the local virtual environment.

### Common Commands

* **View next task:** `uvx agentic-backlog next` (Output is in JSON format by default).
* **Add a task:** `uvx agentic-backlog add "<task name>" --impact <1-5> --effort <1-5> --category "<category>"`
* **Update status:** `uvx agentic-backlog status "<task name>" "<New|In Progress|Completed|Blocked>"`
* **Prioritize:** `uvx agentic-backlog prioritize` (Re-sorts the backlog).

You MUST run `uvx agentic-backlog` whenever you need to check your tasks, modify priorities, or mark work as completed.

### Agent Behavior Rules

* **Logging vs Implementation:** When the user proposes a new feature, idea, or issue, you MUST log it to the backlog via `uvx agentic-backlog add` and STOP. Do NOT automatically begin implementing or planning implementation for the new idea unless the user explicitly instructs you to do so.
