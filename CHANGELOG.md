# Changelog

## [Unreleased]

## [0.51.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.51.0) (2026-11-10)

### Added

- Reality observes TypeScript (Intention node Cross-language Ontology
  Portability, ONTOLOGY-AC1). `.ts` and `.tsx` files produce the same core
  nodes and edges as Python: modules, classes (entities when they extend
  `BaseModel`, `Model` or `Entity`), public functions, methods and
  function-valued constants, `contains` edges, and `depends_on` edges for
  imports, with relative imports resolved to the imported file's module.
  Interfaces, type aliases, enums, `.d.ts` files and `*.test.ts` or
  `*.spec.ts` files are not observed.
- `// aio-sdlc-node: <uuid>` gives a TypeScript definition or module its
  Intention GUID, and `dag-tool guids` reads these markers too.
- New runtime dependency: `tree-sitter-typescript`.

### Known limits

- `dag-tool mapping` approves and checks receipts in Python source only.
- TypeScript functions are never classified as endpoints.

## [0.50.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.50.0) (2026-11-10)

### Added

- The Canonical GUID Extractor (Intention node Canonical GUID Extractor).
  `dag-tool guids` lists every Intention GUID the project claims, from
  `# aio-sdlc-node:` comments read with Tree-Sitter and from agent frontmatter
  read with PyYAML. It reports malformed markers, GUIDs claimed more than once
  and GUIDs the Intention DAG does not define, and exits 1 on any of them. It
  is read-only.

## [0.49.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.49.0) (2026-11-10)

### Added

- The Approval Gate (Intention nodes Approval Gate and Operational Modes
  Config, owner decision 2026-11-09). Work that leaves the diff waits, blocked
  as awaiting approval, until a person runs `aio-sdlc approve`, which records
  the approver, time and rationale on the task. `"approval_mode": "bypass"` in
  `config.json` restores completion as soon as work leaves the diff.
- `dag-tool demo` gains a fifth gate: approving the finished work.

### Changed

- **Behavior change**: completion is gated by default. Before, a diff task
  completed as soon as it left the diff. Projects that relied on that set
  `approval_mode` to `bypass`. Setting such a task to `Completed`, or removing
  its approval blocker by hand, is now refused.

## [0.48.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.48.0) (2026-11-09)

### Changed

- Mapping receipts bind to their mapped symbol instead of the whole file, as
  the owner decided on 2026-11-09. A new or refreshed receipt carries
  `symbol_sha256`, the digest of the definition's own lines with its
  decorators. Editing the rest of the file leaves it fresh. Editing the
  symbol, or renaming it, still makes it stale and needs a person's review.
  Receipts without `symbol_sha256` stay bound to the whole file until they are
  refreshed. `mapping receipt check` reports each receipt's `binding`.

## [0.47.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.47.0) (2026-11-09)

### Added

- `dag-tool doctor` checks an installation without writing anything: the
  entry points, a real MCP handshake with the installed server, and the
  project's state files (Product Hardening, HARDENING-AC1). CI runs it from
  the installed wheel alone.
- CI validates the Claude Code plugin with Claude Code's bundled validator and
  installs it from the checkout into an empty profile.
- `doc/install-contract.md` states what is stable across releases, and
  `doc/recovery.md` explains each refusal the tooling can give and how to
  recover.

### Fixed

- The Claude Code plugin and marketplace manifests no longer declare a
  version. They had stayed at 0.33.0 for thirteen releases, and Claude Code
  treats a declared version as a cache key, so `claude plugin update`
  delivered nothing new. Claude Code now versions the plugin by commit, as in
  the organization's other plugins. The Codex manifest names the latest
  release, and a test keeps it in step with this changelog.

## [0.46.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.46.0) (2026-11-08)

### Added

- `dag-tool benchmark-intent run` and `score` measure intent translation
  against a versioned golden corpus of eight requests (ROADMAP M4, Intent
  Translation Benchmark). It reports omissions, inventions, dependency
  errors, unjustified completions, stability and correction quality against
  the corpus thresholds, which are a proposal until the owner approves the
  corpus.

## [0.45.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.45.0) (2026-11-08)

### Added

- `dag-tool demo` reproduces one requirement from an empty directory through
  intent, approval, triage, `aio-sdlc apply`, source mapping, tests, evidence
  and completion, and writes a plain-language `TRACEABILITY.md` (ROADMAP M4,
  closed-loop reference demo). It asks the named approver at each of its four
  gates unless `--yes`. CI runs it from the installed wheel.
- `dag-tool intent decide` records a person's approval or rejection as one
  appended revision, without hand-writing an Intent IR payload.
- `dag-tool triage-decide` records one triage decision bound to the current
  plan digest. It refuses to add to a stale decision file.
- `dag-tool trace` explains one requirement end to end for a reader who does
  not know the framework. Read-only.

### Changed

- `dag-tool intent create-node` creates the Intention DAG when it does not
  exist yet, so a fresh project needs no hand-written skeleton.
- `aio-sdlc apply` gives the agent a work order with the requirement's name,
  description, provenance and acceptance criteria, and the rule that approval
  stays with people. It used to receive only the task's one-line summary,
  which named the intent by GUID alone.

- CI fails on a stale or invalid mapping receipt instead of only annotating
  it. The two stale receipts were refreshed, and the owner-approved mappings
  and triage decisions of 2026-11-08 are recorded under
  `.aio-agentic-sdlc/changes/mapping-triage-2026-11-08/`.

## [0.44.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.44.0) (2026-11-08)

### Added

- `dag-tool export-abk` projects the work drift triage authorizes into an
  Agentic Backlog Kit manifest (Seam A forward, contract `seam-a-work` v1).
  It writes one file and never calls GitHub; the kit's plan and apply flow
  makes every GitHub write. See `doc/authority-model.md`.

## [0.43.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.43.0) (2026-11-08)

### Added

- `aio-sdlc init --hierarchy simple|deep --validation strict|flex` chooses
  without prompting, and `--yes` never prompts.

### Fixed

- `init` no longer waits for input when stdin is not a terminal. An agent
  harness that holds stdin open as a pipe used to hang on the hierarchy
  prompt; it now gets the defaults (simple hierarchy, flex validation).
- CI installs the built wheel alone, without dev dependencies, and runs both
  entry points, `init` and the MCP server import in an empty project.

## [0.42.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.42.0) (2026-11-08)

### Added

- `dag-tool mapping receipt check` reports every `# aio-sdlc-mapping-approval:`
  receipt whose source changed since approval, or that no longer validates.
  It is read-only and exits 1 on a stale or invalid receipt unless
  `--warn-only`. `--format github` emits pull request annotations, and CI now
  runs it on every pull request.

## [0.41.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.41.0) (2026-11-08)

### Added

- `aio-sdlc --version` (and its `aio-agentic-sdlc` and `agb` aliases) and
  `dag-tool --version` print the installed framework version. Both work
  before `init` and touch no files. The MCP server already reports the same
  version in its handshake. `aio_agentic_sdlc.__version__` now reads the
  installed distribution instead of a hard-coded `0.3.0`.

## [0.40.0](https://github.com/aegolius-labs/aio-agentic-sdlc/releases/tag/v0.40.0) (2026-11-08)

### Breaking: the Antigravity SDK is now an optional extra

`plan` and `apply` run agents through a runtime adapter (ROADMAP M6). Claude
Code and Codex users select the `command` runtime and no longer need
`google-antigravity`. If you run agents on Antigravity, install the extra to
keep `plan` and `apply` working:

```bash
pip install 'aio-agentic-sdlc[antigravity]'
```

Without it, those commands stop with an error that names the extra. This
ships as a minor version because the project is pre-1.0.

### Releases 0.4.0 to 0.39.0

These were not recorded in this file. Their notes are on the
[GitHub Releases](https://github.com/aegolius-labs/aio-agentic-sdlc/releases)
page.

## [0.3.0](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/compare/aio-agentic-sdlc-v0.2.1...aio-agentic-sdlc-v0.3.0) (2026-06-19)

### Features

- add 'agb' as a shorter CLI alias ([9aa7121](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9aa71214fd63d22032c57c3e6b22606d828de727))
- add blocker awareness with block/unblock commands and auto-status ([1306b35](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1306b358fcd5c3d686c412ad1f4d3fa438ad5c02))
- add framework detection and seeding via init --empty ([92d9120](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/92d91200d489547630e5d8a71f24bf1e90c3226b))
- add multi-line description field support to backlog items ([#3](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/3)) ([b43a4f8](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/b43a4f89cc3a2690fec4940322afc141bdcb5ec6))
- add next command and refactor sort logic into _compute_sorted_items ([58b3d1a](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/58b3d1acbc036326014cbcc6c13df3e60b882e8e))
- add status tracking with retention and zero-scoring for completed items ([475053c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/475053c37d3cc10c750cb3245ad5cd65d33ee733))
- add uv.lock for dependency management and clean up gitignore entry for qa_tests ([7456e30](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7456e3089e7060f5c8e218bec2232a6089f055e5))
- **core:** enforce non-empty task descriptions ([da81046](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/da8104606401af8e5c1690cea2c8f158ab026904))
- expose backlog via native MCP server ([457c9ec](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/457c9ec88e5b86c076e2274d2e255f052c4d5600))
- implement DAG graph schema and SDD reconciliation sync layer ([b590392](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/b5903923473fcb0c99438bf0de6a484bafcfb73d))
- implement DAG graph schema and SDD reconciliation sync layer ([f8a0303](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/f8a0303c60e7d8581d4c3038d5e644d9fad0d7f7))
- implement GitHub Projects V2 integration ([7a8a27c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7a8a27ccd3f098d7275cb4513858e12ec174ce9b))
- implement Open-Spec and Spec-Kit seed parsers ([1bdcdd4](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1bdcdd4a1b1280c370cd90697d5d64dcdb1b6485))
- implement remove command to safely delete backlog items ([#5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/5)) ([79cb3bf](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/79cb3bf65912a53e981ecd53e85c815a7b0bc041))
- package agent skill natively and make init idempotent ([a9cf959](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a9cf9597253273582c2388d5bddea9d16596d4ee))
- package agent skill natively and make init idempotent ([9a7965d](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9a7965d28a78c666015c69bcc61f370eab1fb798))

### Bug Fixes

- configure release-please manifest ([fc89be9](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/fc89be9cd512d05af8b94f078ef6313e2c4a808a))
- configure release-please manifest to base from 0.2.1 ([c0915b3](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/c0915b3e9373df95e119c94b266f0c628a6fdd6c))
- make core logic and mcp server workspace-aware by injecting project_path ([1367e39](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1367e394085c9cfb4b5337e9b6e3578463d31946))
- orchestrate git commits for backlog migration and delete archive file ([8a71a3b](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/8a71a3b6aec74e2a08c5b11027b3a26f09bc2a3b))
- update release-please action path to resolve deprecation warning ([aaeed04](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/aaeed04ba39c0255e3e901d57190fe5cb573d806))

### Documentation

- add architecture documentation with mermaid diagrams ([a1f4969](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a1f49693c4d99fad503804452f23400956a9f4a0))
- add Buy Me a Coffee sponsorship option ([c4c7bfa](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/c4c7bfa9c315a7e8a9fd2e913acf9d4cf1a90621))
- add global uv tool install instructions ([7c0c1a5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7c0c1a578f6ad88864f6c263cdd70e9ecab2723e))
- **architecture:** add GitHub mode and SDD reconciliation layer ([3ae255c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/3ae255c366c8a0a94fab1c736de598b281a19f7d))
- clarify agent behavior rules in SKILL.md ([#2](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/2)) ([e055466](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/e055466f16665205a97e738597c5500441a310df))
- update distribution paths to use GitHub natively via uvx ([cfa5bb7](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/cfa5bb7599ff3d2b4a23bd756ea82cd51bbd9c49))

## 0.1.0 (2026-06-19)

### Features

- add 'agb' as a shorter CLI alias ([9aa7121](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9aa71214fd63d22032c57c3e6b22606d828de727))
- add blocker awareness with block/unblock commands and auto-status ([1306b35](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1306b358fcd5c3d686c412ad1f4d3fa438ad5c02))
- add framework detection and seeding via init --empty ([92d9120](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/92d91200d489547630e5d8a71f24bf1e90c3226b))
- add multi-line description field support to backlog items ([#3](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/3)) ([b43a4f8](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/b43a4f89cc3a2690fec4940322afc141bdcb5ec6))
- add next command and refactor sort logic into _compute_sorted_items ([58b3d1a](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/58b3d1acbc036326014cbcc6c13df3e60b882e8e))
- add status tracking with retention and zero-scoring for completed items ([475053c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/475053c37d3cc10c750cb3245ad5cd65d33ee733))
- add uv.lock for dependency management and clean up gitignore entry for qa_tests ([7456e30](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7456e3089e7060f5c8e218bec2232a6089f055e5))
- expose backlog via native MCP server ([457c9ec](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/457c9ec88e5b86c076e2274d2e255f052c4d5600))
- implement GitHub Projects V2 integration ([7a8a27c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7a8a27ccd3f098d7275cb4513858e12ec174ce9b))
- implement Open-Spec and Spec-Kit seed parsers ([1bdcdd4](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1bdcdd4a1b1280c370cd90697d5d64dcdb1b6485))
- implement remove command to safely delete backlog items ([#5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/5)) ([79cb3bf](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/79cb3bf65912a53e981ecd53e85c815a7b0bc041))
- package agent skill natively and make init idempotent ([a9cf959](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a9cf9597253273582c2388d5bddea9d16596d4ee))
- package agent skill natively and make init idempotent ([9a7965d](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9a7965d28a78c666015c69bcc61f370eab1fb798))

### Bug Fixes

- make core logic and mcp server workspace-aware by injecting project_path ([1367e39](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1367e394085c9cfb4b5337e9b6e3578463d31946))
- orchestrate git commits for backlog migration and delete archive file ([8a71a3b](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/8a71a3b6aec74e2a08c5b11027b3a26f09bc2a3b))
- update release-please action path to resolve deprecation warning ([aaeed04](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/aaeed04ba39c0255e3e901d57190fe5cb573d806))

### Documentation

- add architecture documentation with mermaid diagrams ([a1f4969](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a1f49693c4d99fad503804452f23400956a9f4a0))
- add Buy Me a Coffee sponsorship option ([c4c7bfa](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/c4c7bfa9c315a7e8a9fd2e913acf9d4cf1a90621))
- add global uv tool install instructions ([7c0c1a5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7c0c1a578f6ad88864f6c263cdd70e9ecab2723e))
- clarify agent behavior rules in SKILL.md ([#2](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/2)) ([e055466](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/e055466f16665205a97e738597c5500441a310df))
- update distribution paths to use GitHub natively via uvx ([cfa5bb7](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/cfa5bb7599ff3d2b4a23bd756ea82cd51bbd9c49))
