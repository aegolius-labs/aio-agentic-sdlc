# Recovery procedures

The tooling fails closed: when it cannot tell what the right state is, it stops
and says so instead of guessing. This page lists each refusal an adopter can
meet, what it means, and how to recover. Start with `dag-tool doctor`, which
reports which state file does not load.

Never fix these by editing state files by hand. Every write goes through the
tooling so locks, revision checks and the audit journal hold (ADR 0001).

## Backlog (`backlog.json`, gitignored)

The backlog is derived from the diff of the two DAGs, so it can always be
rebuilt from them. The committed DAGs and evidence are the durable state.

| Message | Meaning | Recovery |
| --- | --- | --- |
| `Backlog write used stale revision N; current revision is M` | Another process wrote first | Run the command again, so it reloads the new revision first |
| `Backlog hash does not match either side of incomplete transaction ...; refusing to guess` | A write was interrupted, and something else changed the file afterwards | See [Rebuild the backlog](#rebuild-the-backlog) |
| `Invalid audit record at line N` | `state-audit.jsonl` is damaged before its last line. A torn last line is repaired on its own and logged as `audit_tail_truncated` | Move the journal aside, then rebuild the backlog |
| A newer `schema_version` is refused | The backlog was written by a newer release | Upgrade the package. Older releases never downgrade a newer file |
| A legacy, unversioned backlog | It predates ADR 0001 | `aio-sdlc migrate-state` |
| A lock timeout | Another CLI or MCP process holds the lock | Let it finish, or stop it. The lock file itself can stay; it is reused |

### Rebuild the backlog

1. Stop every process using the project: CLI runs, the MCP server in your
   agent host, and any orchestrator loop.
2. Keep the evidence. Move `.aio-agentic-sdlc/backlog.json` and
   `.aio-agentic-sdlc/state-audit.jsonl` into a dated folder outside the
   workspace.
3. Run `dag-tool doctor` to confirm the project loads. A missing backlog
   reads as empty, revision 0.
4. The next `aio-sdlc apply` ingests the diff into the new backlog before it
   dispatches any work. `aio-sdlc plan` shows that diff without writing it.

Execution status recorded only in the old backlog is lost. It is recoverable
from the moved file by reading it, and the audit journal records every change
that led to it.

## Intention DAG (`intention-dag.yaml`, committed)

The Intention DAG is layer 1 and lives in git, so git is its recovery path.

- **Does not load or validate**: `git diff` and `git log -p` on the file show
  the change that broke it. Restore it with `git restore`, or revert that
  commit, then redo the intended change with `dag-tool intent set`.
- **`expected revision` refused**: someone changed the node since you read it.
  Run `dag-tool intent-summary --node-id <id>` and retry with the revision it
  shows.

## Reality DAG (`reality-dag.yaml`, committed)

Reality is an observation and is never edited. Regenerate it:

```bash
dag-tool generate-reality --dir . --system "<Intention DAG metadata name>"
```

Use the Intention DAG's metadata name as the system name. Mapping review
compares against Reality generated that way.

## Mapping receipts (in source files)

A `# aio-sdlc-mapping-approval:` receipt binds to the source of its mapped
symbol. Any edit inside that symbol, or a rename, makes the receipt stale, and
CI fails. An older receipt without `symbol_sha256` binds to the whole file
until it is refreshed.

1. `dag-tool mapping receipt check` lists the stale receipts.
2. `dag-tool mapping receipt review` shows fresh evidence for one of them.
3. A person decides whether the symbol is still the node's implementation.
   `dag-tool mapping receipt refresh` records that decision. Never refresh a
   receipt without that review.

## Node markers

`dag-tool guids` reports three problems with `# aio-sdlc-node:` markers and
agent frontmatter GUIDs.

- **Malformed**: the value is not a UUID. Fix the typo against the Intention
  DAG node it was meant to name.
- **Claimed more than once**: two places claim the same node, so its identity
  is ambiguous. Keep the one the mapping receipt names and remove the other.
- **Not an Intention DAG node**: the node was removed or the GUID is wrong.
  Do not add an Intention node to make the marker valid; that would turn an
  observation into intent. Remove the marker, or map the symbol to the right
  node with `dag-tool mapping review`.

## Triage decisions

Triage decisions bind to a digest of both DAGs and the evidence ledger. Any
change makes them stale, and `stale triage decisions: plan_digest does not
match current DAG state` refuses them. Run `dag-tool triage` again, then record
each decision anew with `dag-tool triage-decide`. Do not edit the digest.

## Evidence ledger (`evidence.json`, committed)

Only `dag-tool evidence record` writes the ledger, and it keeps one record per
criterion and reference. A damaged ledger is restored from git like the
Intention DAG.

## Backups the tooling keeps

Spec promotion, mapping and document generation keep the original and any
conflicting version under `.aio-agentic-sdlc/backups/`, which is gitignored.
They accumulate. Review them with no writers running before you delete any.

## MCP server does not connect

1. Run `dag-tool doctor` in the project. If its MCP check fails, the problem is
   the installation, not the host.
2. The plugins start the server through `uvx`, which needs network access on
   the first start. A host with a short startup timeout may give up while it
   downloads. Run `uvx --from git+https://github.com/aegolius-labs/aio-agentic-sdlc
   dag-tool --version` once to fill the cache, then restart the host.
3. Two servers registered under the same name collide. Give a local override
   its own name (see `doc/claude-code-plugin.md`).
