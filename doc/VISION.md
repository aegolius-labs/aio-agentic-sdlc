# Agentic-Backlog Vision & North Star

**The Semantic Roadmap Graph**

The ultimate "North Star" for `agentic-backlog` is to serve as the definitive **Semantic Roadmap Graph** for a project. It is not merely a flat task tracker or a simple GitHub Issues bridge.

## Core Philosophy

1. **The Roadmap as a DAG:** An evolving backlog is essentially a mindmap or a Directed Acyclic Graph (DAG) that tells the complete story of a project. It documents how the project is supposed to work, how structural decisions were made, why they were made, and what the dependencies are.
2. **Bridging Intention and Reality:** Tools like `graphify` create comprehensive graphs of how a codebase *actually* works based on the source code. `agentic-backlog` maintains the graph of what *should* exist (the intended architecture).
3. **Reconciliation Engine:** The long-term vision is to superimpose the intended Roadmap Graph (`agentic-backlog`) over the implemented codebase graph (`graphify`) to automatically detect gaps, architectural misalignments, orphaned code, and precisely calculate what to tackle next to reconcile the two graphs.

## Implications for Architecture

- **Local Persistence is Key:** The local `backlog.json` file is a first-class citizen and acts as the local graph database. It must never be discarded, archived, or purely superseded by remote trackers.
- **Hierarchy is Fundamental:** Hierarchical types (Epics, Features, Tasks) and relationships (Parents, Dependencies) are not just organizational conveniences—they are the structural edges of the semantic graph.
- **Remote as a Projection:** While GitHub Issues/Projects are supported as powerful remote projections and execution trackers, the structural and semantic truth of the intended roadmap remains anchored in the local DAG.
