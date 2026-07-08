# AIO Agentic SDLC - Task Queue

This is a temporary queue to keep us focused while we transition the architecture from a simple task backlog to the full Dual-DAG reconciliation engine.

## Active Phase: SDLC Foundation
- [x] **Define the SDLC Pipeline**: Formalize the exact workflow an agent must follow from idea intake to final PR, independent of the DAG logic. We must establish this behavior first before building the complex reconciliation engine.

## Next Phase: The Dual-DAG Architecture
- [x] **Research & Define Intention DAG Schema**: Explore architectural modeling standards (C4, DDD) and define a JSON/YAML schema for agents to map the *desired* software state (components, modules, endpoints, dependencies) rather than just tasks.
- [ ] **Develop DAG Manipulation Tooling**: Build the programmatic tools (CLI/SDK) required to safely edit the DAG state files, ensuring no agent ever performs manual JSON edits.
- [x] **Design the Reality DAG Generator**: Determine how we will generate an accurate, real-time graph of the existing codebase that maps 1:1 with the ontology of our Intention DAG.
- [ ] **Develop the Diffing Engine**: Build the core logic that superimposes the Intention DAG over the Reality DAG to calculate the "Diff"—which will serve as our dynamically generated Backlog.
- [ ] **Agentic Orchestrator Integration**: Bind the calculated Diff to the SDLC Pipeline, allowing agents to automatically execute the required changes to reconcile reality with intention.
