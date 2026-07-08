# Specification: SDLC Orchestrator

## 1. Overview
The SDLC Orchestrator is the central hub for the `aio-agentic-sdlc` framework. It acts as the single user-facing entity. It manages the Software Development Life Cycle by ingesting user ideas, navigating the Dual-DAG reconciliation loop, and delegating execution to specialized subagents.

## 2. Core Principles
- **Single Pane of Glass:** The user communicates exclusively with the Orchestrator.
- **Strict Delegation:** The Orchestrator does not perform heavy computation, graph generation, or coding. It delegates to specialized subagents.
- **Token-Optimized Communication:** Inter-agent communication relies on highly compressed, token-optimized data structures (JSON, YAML, precise file paths, raw diffs). Human pleasantries are strictly omitted.
- **The Backlog is a Diff:** The project backlog is entirely dynamic. It is automatically generated and updated anytime there is a Diff calculated between the Intention DAG and the Reality DAG.

## 3. Specialized Subagent Roles
*   **Cartographer (State Manager):** Responsible for parsing the codebase to update the Reality DAG, parsing user requirements to update the Intention DAG, and calculating the Diff between the two to dynamically generate the Backlog.
*   **Architect:** Responsible for Research, Breakdown, and Planning based on the calculated Diff.
*   **Implementer:** Responsible for executing code changes based on strict constraints and TDD principles.
*   **QA / Tester:** Responsible for fuzzing, writing missing test cases, and attempting to break the implementer's code.

## 4. The Orchestrated SDLC Pipeline

### Phase 0: Bootstrap (One-Time Execution)
1.  **Trigger:** Orchestrator detects `aio-agentic-sdlc` is uninitialized in the workspace.
2.  **Delegation:** Orchestrator spawns the **Cartographer** subagent.
3.  **Execution:** Cartographer scans the codebase to generate the initial **Reality DAG** and creates a baseline **Intention DAG**.

### Phase 1: Intake & State Update
1.  **Trigger:** User provides an idea or requirement directly to the Orchestrator (external ticketing is ignored).
2.  **Delegation:** Orchestrator spawns the **Cartographer**.
3.  **Execution:** Cartographer updates the **Intention DAG** with the new requirements. It then calculates the Diff between the new Intention DAG and the existing Reality DAG.
4.  **Handoff:** Cartographer returns the updated, dynamic Backlog (the Diff) to the Orchestrator.

### Phase 2: Breakdown & Planning
1.  **Delegation:** Orchestrator spawns the **Architect** subagent, passing it the new Diff/Backlog.
2.  **Execution:** Architect analyzes the Diff, performs necessary technical research, and formulates a step-by-step structural implementation plan.
3.  **Handoff:** Architect returns a highly compressed data structure (the plan) to the Orchestrator.

### Phase 3: Implementation (TDD)
1.  **Delegation:** Orchestrator parses the plan and spawns **Implementer** subagents.
2.  **Execution:** Implementers follow Test-Driven Development (TDD) to write tests and implement the code required to resolve the Diff.
3.  **Handoff:** Implementers return a compressed summary of changed files and passing tests.

### Phase 4: Comprehensive Testing
1.  **Delegation:** Orchestrator spawns the **QA** subagent.
2.  **Execution:** QA inspects the implementations, runs integration suites, and performs adversarial testing.
3.  **Handoff:** QA returns a pass/fail matrix. 
    *   *If Fail:* Orchestrator loops back to **Phase 3 (Implementation)** with the failure context.
    *   *If Pass:* Proceed to Wrap-Up.

### Phase 5: Wrap-Up & State Reconciliation
1.  **Delegation:** Orchestrator spawns the **Cartographer** one final time.
2.  **Execution:** Cartographer rescans the modified codebase to update the **Reality DAG**. It calculates the Diff one last time to verify the backlog is now empty (Intention == Reality).
3.  **Completion:** Orchestrator finalizes documentation, commits the code, opens a PR, and reports success to the user.
