# All-in-One Agentic SDLC (aio-agentic-sdlc) Vision & North Star

## The Dual-DAG Reconciliation Engine

The ultimate "North Star" for this project is to evolve beyond passive task tracking into a fully autonomous, **All-in-One Agentic Software Development Life Cycle (SDLC)** orchestrator. It acts as the definitive reconciliation engine between software design and reality.

## Core Philosophy

1. **The Intention DAG:** We maintain a living Directed Acyclic Graph (DAG) that represents the *desired* state of the software. It documents how the project is supposed to work, structural decisions, requirements, and dependencies.
2. **The Reality DAG:** We generate a real-time DAG representing the *actual* state of the implemented codebase. To ensure we can compute an accurate delta, we must build our own Reality DAG generator so that it maps 1:1 with the ontology and schema of the Intention DAG.
3. **The Backlog as a Diff:** The "Backlog" is no longer a static list of user-created tasks. The
   Backlog is mathematically defined as the **Diff** between the Intention DAG and the Reality DAG.
   This diff precisely highlights missing dependencies, orphaned code, incomplete features, and
   architectural misalignments. The leaves of the diff are the actionable items. The framework's own
   scoring engine orders them, within the order the dependency edges already impose.
4. **Agentic Orchestration:** By calculating this Diff, our agentic SDLC framework knows exactly where the software is and where it needs to go. It can autonomously break down the Diff, formulate implementation plans, and delegate work to specialized subagents (Architects, Implementers, QA) to continuously pull the Reality DAG into alignment with the Intention DAG.

## Implications for Architecture

- **In-House Graph Generation:** Relying on third-party tools (like `graphify`) is insufficient if their output cannot map cleanly to our semantic Intention DAG. Both sides of the equation must speak the same structural language.
- **Local Persistence is Key:** The version-controlled `.aio-agentic-sdlc/intention-dag.yaml` is the source of truth for project intent. The Reality DAG and execution backlog are local derivatives with explicitly narrower responsibilities.
- **Hierarchy & Relationships are Fundamental:** Hierarchical types and dependency relationships are not organizational conveniences—they are the critical structural edges required to compute an accurate diff between Intention and Reality.
- **Remote Projections Are One-Way:** External trackers are never authoritative. The work projects one way onto GitHub Issues and Projects through `agentic-backlog-kit`, and what GitHub shows comes back only as evidence. Its contents cannot override locally derived work. See [authority-model.md](authority-model.md).

## The Suite

This framework is the end product. It is the all-encompassing, multi-layered system: a person provides intent, the system and its agents create and update the two DAGs, and the scored leaves of their diff are the backlog. The other Aegolius Labs repositories serve that one goal, and [authority-model.md](authority-model.md) is the normative statement of how they compose:

- **`agentic-backlog-kit`** is the projection layer. It shows the work on GitHub for people and teams, and it can be used on its own.
- **`agentic-qa-kit`** closes the loop. It brings QA and testing into the lifecycle as evidence about reality, and it can be used on its own.
- **`agentic-product-playbook`** is guidance for the Intake side. It helps the agents that scaffold a project and create its DAGs decide what must be decided first. It is an experiment, and it may become part of this framework's Intake path instead of staying a separate repository.

The kits are separate repositories today so that each keeps a fast, dependency-free standalone install. That is the current decision, not a permanent one. The authority model states when to reconsider merging them into this repository.

## Undecided: A UI Layer

The owner wants a UI layer that ties the suite together (stated 2026-11-11). Its form is
deliberately not chosen yet. It could be integrations into third-party tools, a terminal UI, a web
app, or a mix. The choice waits until more of the loop is complete. Whatever form it takes, it is a
view over the layers above, like the GitHub projection: it may show and collect input, but what it
shows never becomes intent except through the approval-gated Intake path.
