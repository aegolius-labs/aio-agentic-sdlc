# Agentic Backlog Architecture

This document describes the high-level architecture and data flow of the `aio-agentic-sdlc-cli` tool.

## System Overview

> **Note:** Please read [VISION.md](./VISION.md) to understand the foundational North-Star of this project—the Semantic Roadmap Graph—before making architectural changes.

The CLI acts as a deterministic backlog manager using a 3-Dimensional matrix (Impact, Effort, Dependency) to calculate priority scores and topologically sort tasks. All framework state is local. External trackers are not authoritative and synchronization support is intentionally absent.

```mermaid
graph TD
    User([User / Agent]) -->|CLI / MCP Commands| CLI[Entrypoint]
    
    subgraph Core Engine
        CLI --> Detect[detect.py]
        CLI --> Sort[Topological Sort & Scoring]
        CLI --> Export[Markdown Exporter]
        CLI --> SDDRecon[SDD Reconciliation Layer]
    end
    
    subgraph Local Persistence
        CLI --> Intent[(intention-dag.yaml)]
        CLI --> Reality[(reality-dag.yaml)]
        CLI --> ReadJSON[load_backlog]
        ReadJSON --> FileDB[(backlog.json)]
        CLI --> WriteJSON[atomic save_backlog]
        WriteJSON --> FileDB
        CLI --> BackupManager[_create_backup]
        BackupManager --> BackupFiles[(Timestamped backups)]
    end

    Detect -->|Reads local environment| Workspace[Local Project Files]
    SDDRecon -.->|Reconciles artifacts with| Workspace
    Sort -->|In-memory mutator| Items[Backlog Items Dict]
```

## Data Flow

### 1. Command Dispatch

User invokes a command (e.g., `add`, `update`, `prioritize`, `next`, `status`, `block`, `unblock`, `export`, `init`). The `argparse` router dispatches to the appropriate command handler.

### 2. Local State Contract

The local files have distinct responsibilities:

- `intention-dag.yaml` is the durable, version-controlled source of truth for intended behavior and canonical GUIDs.
- `reality-dag.yaml` is a regenerable observation of the repository. It is evidence, not intent.
- `backlog.json` is a local, gitignored execution queue derived from the difference between the two DAGs. CLI and MCP backlog mutations operate only on this file.
- `.agentic-backlog.json` is a legacy generated artifact. Runtime code does not read it, and it must not be treated as roadmap state.

Framework tools, rather than hand edits, perform state transitions. External issue trackers may be reintroduced later as one-way projections, but they cannot select or replace the authoritative state.

### 3. State Loading

The command handler reads the current state from `backlog.json` via `load_backlog()`. If the file does not exist, an empty dictionary is returned.

### 4. State Modification & Backup

For mutating commands, `_create_backup()` is called immediately to create a timestamped backup before any modifications occur. Backups older than 7 days are pruned automatically. Writes use a temporary file followed by an atomic replacement, preserving the previous backlog if serialization is interrupted.

### 5. Prioritization Engine (`_compute_sorted_items`)

When prioritizing or retrieving the next task, the system performs:

1. **Cycle Detection & Topological Sort**: A depth-first search (DFS) algorithm traces the dependency graph (`requires` fields). If a cycle is detected, execution aborts with an error. Otherwise, a valid topological order is generated.
2. **Base Scoring**: Items receive a base score of `Impact + (5 - Effort)`. Completed items are given a base score of 0.
3. **Dependency Boosting**: Iterating in reverse topological order, each item inherits 50% of the scores of its direct dependents.
4. **Tie-Breaking**: Items are inserted into a priority queue factoring in their final score and a category weight (Security > Reliability > Business > other).
5. **Auto-Status**: Any incomplete item with non-empty `blockers` automatically switches to the `Blocked` status.

### 6. State Persistence

The final sorted items are saved to the local `backlog.json`. The `.aio-agentic-sdlc.json` file configures hierarchy and validation behavior; `core.mode` is always `local`.

## Framework Detection and SDD Reconciliation

The `init` command leverages `detect.py` to inspect the working directory for well-known framework identifiers (e.g., `package.json`, `pyproject.toml`, `Cargo.toml`). If a framework is detected, `generate_seed_backlog()` is invoked to pre-populate boilerplate tasks.

Furthermore, when working alongside Spec-Driven Development (SDD) frameworks like Open-Spec or Spec-Kit, the **SDD Reconciliation Layer** aims to reconcile overlapping feature sets. Reconciliation imports useful local artifacts into the local model without promoting either those artifacts or an external tracker above the Intention DAG.
