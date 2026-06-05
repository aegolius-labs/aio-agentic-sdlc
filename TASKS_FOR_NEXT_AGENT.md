# Hand-Off: Integrations for OpenSpec and Spec-Kit

*N.B. : Some research may be required to fully understand how to integrate this CLI tool in existing open-spec or spec-kit projects.*

**To the next agent working on this repository:**

The user requested that this CLI tool integrate smoothly with existing agentic workflows like `open-spec` and `spec-kit`. The goal is for a user to run `agentic-backlog init` inside a workspace and have the tool automatically detect the existing project framework and pull in the existing roadmap/changes.

Here is what you need to build next:

## 1. Implement Status Tracking & Retention

Unlike SDD frameworks where artifacts persist, standalone repos rely on the JSON backlog for history. Therefore, completed items should not be deleted.

- **Add a `status` attribute:** Allowed values are `New` (not started/no dependencies), `In Progress`, `Completed`, and `Blocked` (unfulfilled deps or user blockers).
- **Update Scoring:** When an item's status is set to `Completed`, hardcode its Base and Final scores to `0` during the `prioritize` calculation so it naturally drops to the bottom of the list.

## 2. Implement Blocker Awareness

- **Add a `blockers` attribute:** A list of strings representing explicit roadblocks (user or AI generated). *Note: Do not merge `requires` dependencies into this list; dependencies are handled by the topological sort.*
- **Blocker-Aware Sorting:** Blockers should not change the mathematical Final Score or the topological order of the queue, but they should flag the item as unworkable.

## 3. Implement the `next` Command

Create a new CLI command (e.g., `agentic-backlog next`) designed for an autonomous agent to query what it should work on next.

- The command must iterate down the topologically sorted list and return the **highest workable item** (status is not `Completed` and `blockers` is empty).
- If the highest workable item returned is *not* the actual #1 item in the queue (because the #1 item has blockers), the JSON output must include a clear warning:

  ```json
  {
    "target": { ...item data... },
    "warning": "Top item 'X' has the highest priority but is blocked by: [list of blockers]"
  }
  ```

## 4. Implement `detect_framework()`

In `cli.py`, before initializing an empty `backlog.json`, add a function that scans the current working directory for framework signatures.

- **OpenSpec**: Check for `.openspec.yaml` or an `openspec/` directory.
- **Spec-Kit**: Check for `spec-kit.yaml` or a `specs/` directory.

## 2. Implement Seed Parsers

If a framework is detected, prompt the user (or default to yes) to import the existing items into the backlog.

- **For OpenSpec**:
  - Read `openspec/changes/*/proposal.md` or `.openspec.yaml`.
  - Extract the change names and map them to `agentic-backlog` entries.
  - Set default Impact/Effort scores (e.g., 3/3) and mark them as `ai_driven = true` so the user knows they need to calibrate the imported scores.
- **For Spec-Kit**:
  - Do the same for the Spec-Kit schema structures.

## 3. Two-Way Sync (Optional but Powerful)

Consider creating an `agentic-backlog sync` command that continuously reads from the `backlog.json` and updates the native queue files (e.g., updating an `openspec-queue.md` or native roadmap file) so the UI stays in sync with the backend JSON.

## 4. Setup Testing

Initialize `pytest` in this repository and write unit tests for the topological sorting logic and the circular dependency detection to ensure the core engine remains bulletproof as you add these integrations.
