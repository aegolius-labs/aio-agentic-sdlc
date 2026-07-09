# AIO Agentic SDLC - Task Queue

This is a temporary queue to keep us focused while we transition the architecture from a simple task backlog to the full Dual-DAG reconciliation engine.

## Active Phase: SDLC Foundation
- [x] **Define the SDLC Pipeline**: Formalize the exact workflow an agent must follow from idea intake to final PR, independent of the DAG logic. We must establish this behavior first before building the complex reconciliation engine.

## Next Phase: The Dual-DAG Architecture
- [x] **Research & Define Intention DAG Schema**: Explore architectural modeling standards (C4, DDD) and define a JSON/YAML schema for agents to map the *desired* software state (components, modules, endpoints, dependencies) rather than just tasks.
- [x] **Develop DAG Manipulation Tooling**: Build the programmatic tools (CLI/SDK) required to safely edit the DAG state files, ensuring no agent ever performs manual JSON edits.
- [x] **Design the Reality DAG Generator**: Determine how we will generate an accurate, real-time graph of the existing codebase that maps 1:1 with the ontology of our Intention DAG.
- [x] **Develop the Diffing Engine**: Build the core logic that superimposes the Intention DAG over the Reality DAG to calculate the "Diff"—which will serve as our dynamically generated Backlog.
- [ ] **Agentic Orchestrator Integration**: Bind the calculated Diff to the SDLC Pipeline, allowing agents to automatically execute the required changes to reconcile reality with intention.

## Upcoming Enhancements (Phase 3)
- [ ] **Operational Modes (Approval vs Bypass)**: Introduce user approval gates prior to merging, with a "Bypass Approval" mode for fully autonomous continuous delivery.
- [ ] **Parallel Task Execution**: Enable the Orchestrator to spawn concurrent subagents for unblocked items in the backlog, handling DAG concurrency and merge conflicts.
- [ ] **Subagent Output Templates**: Define structured reporting templates for each subagent so the Orchestrator can compile a clean, human-readable summary of the entire parallel session.
- [ ] **QA Swarm Orchestration**: Upgrade `sdlc_qa` into an orchestrator that manages a swarm of specialized QA subagents (A11Y UX, API Contracts, Backlog Synthesis, Discovery, Performance Reliability, Requirements Analysis, Runtime Functional, Security Privacy, Static Quality, Test Inventory) to ensure bulletproof code generation.
