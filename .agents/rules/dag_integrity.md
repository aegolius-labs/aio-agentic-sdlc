---
name: dag-integrity
description: Enforces that DAG state files cannot be manually edited by agents to prevent JSON corruption.
---

# DAG Integrity Rules

The Dual-DAG state files (Intention DAG and Reality DAG) are the most critical source of truth for the `aio-agentic-sdlc` engine. 

1. **NO MANUAL EDITS**: You MUST NOT manually edit the DAG JSON/YAML files directly via text-editing tools. Manual edits frequently lead to schema corruption, syntax errors, and broken edges.
2. **USE TOOLING ONLY**: All modifications, creations, or deletions to the DAGs MUST be executed exclusively through dedicated programmatic tooling (such as a CLI, Python SDK, or specific MCP tools built for DAG manipulation).
