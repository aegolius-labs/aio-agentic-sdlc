# Two-Stage Pipeline Epic: Implementation Plan

## 1. Overview
The Two-Stage Pipeline aims to split the requirements gathering and architectural design phases into two distinct steps. The Intake Agent will solely be responsible for writing Product Requirement Documents (PRDs) into an `inbox/` directory. The Architect Agent will then process these PRDs during the `plan` phase, mapping them to the `intention-dag.yaml` and moving them to `specs/`.

## 2. Structural Implementation Steps

### Step 1: Intake Agent Refactor (Completed)
- **File to Update:** `.agents/agents/sdlc_intake/system_prompt.md`
- **Changes:**
  - Removed permissions to modify `intention-dag.yaml`.
  - Updated the objective to focus on acting as a Product Manager.
  - Specified that output should be written as Markdown PRDs into the `inbox/` directory.

### Step 2: Update `intention-dag.yaml` (Completed)
- **File to Update:** `intention-dag.yaml`
- **Changes:**
  - Updated `sdlc-intake-agent` description.
  - Added `sdlc-architect-agent` node as a core agent responsible for reading PRDs from `inbox/` and updating the DAG.
  - Added `inbox-directory` entity.
  - Added edges mapping the intake agent writing to the inbox and the architect agent reading from it.

### Step 3: Architect Subagent Setup
- **Action:** Create the `sdlc_architect` agent definition.
- **Files to Create/Update:**
  - `.agents/agents/sdlc_architect/system_prompt.md` (or equivalent location)
- **Prompt Details:**
  - Define the persona as a Technical Architect.
  - Objective: Read PRDs from `inbox/`, perform technical research, map requirements into architectural nodes in `intention-dag.yaml`, and move the processed PRDs to `specs/`.
  - Allowed tools: Reading PRDs, updating DAG files, and moving files.

### Step 4: CLI `plan` Refactor
- **File to Update:** `src/agentic_backlog/cli.py` (specifically `plan_cmd`)
- **Changes:**
  1. Add logic to check if `inbox/` directory exists and has any Markdown files.
  2. If files exist:
     - Programmatically invoke the `sdlc_architect` subagent.
     - Provide the subagent with the list of files in `inbox/`.
     - The subagent will process each file, update `intention-dag.yaml`, and move the files to `specs/`.
  3. Once the `inbox/` is completely processed (or if it was empty initially):
     - Instantiate the `DiffingEngine` (as currently done).
     - Compute the differences between `intention-dag.yaml` and `reality-dag.yaml`.
     - Print the Execution Backlog (diff) to the terminal.

### Step 5: Verify CLI `apply` command
- **File to Review:** `src/agentic_backlog/cli.py` and `src/agentic_backlog/orchestrator_loop.py`
- **Changes:** No functional changes required for `apply`. It will execute the calculated diff as usual.

## 3. Future Considerations
- Adding robust error handling when the architect subagent encounters conflicting PRDs.
- Emitting standard logging messages during the `plan` step to notify the user of architect activities.
