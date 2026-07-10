# Changelog

## [0.3.0](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/compare/aio-agentic-sdlc-v0.2.1...aio-agentic-sdlc-v0.3.0) (2026-06-19)


### Features

* add 'agb' as a shorter CLI alias ([9aa7121](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9aa71214fd63d22032c57c3e6b22606d828de727))
* add blocker awareness with block/unblock commands and auto-status ([1306b35](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1306b358fcd5c3d686c412ad1f4d3fa438ad5c02))
* add framework detection and seeding via init --empty ([92d9120](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/92d91200d489547630e5d8a71f24bf1e90c3226b))
* add multi-line description field support to backlog items ([#3](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/3)) ([b43a4f8](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/b43a4f89cc3a2690fec4940322afc141bdcb5ec6))
* add next command and refactor sort logic into _compute_sorted_items ([58b3d1a](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/58b3d1acbc036326014cbcc6c13df3e60b882e8e))
* add status tracking with retention and zero-scoring for completed items ([475053c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/475053c37d3cc10c750cb3245ad5cd65d33ee733))
* add uv.lock for dependency management and clean up gitignore entry for qa_tests ([7456e30](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7456e3089e7060f5c8e218bec2232a6089f055e5))
* **core:** enforce non-empty task descriptions ([da81046](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/da8104606401af8e5c1690cea2c8f158ab026904))
* expose backlog via native MCP server ([457c9ec](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/457c9ec88e5b86c076e2274d2e255f052c4d5600))
* implement DAG graph schema and SDD reconciliation sync layer ([b590392](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/b5903923473fcb0c99438bf0de6a484bafcfb73d))
* implement DAG graph schema and SDD reconciliation sync layer ([f8a0303](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/f8a0303c60e7d8581d4c3038d5e644d9fad0d7f7))
* implement GitHub Projects V2 integration ([7a8a27c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7a8a27ccd3f098d7275cb4513858e12ec174ce9b))
* implement Open-Spec and Spec-Kit seed parsers ([1bdcdd4](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1bdcdd4a1b1280c370cd90697d5d64dcdb1b6485))
* implement remove command to safely delete backlog items ([#5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/5)) ([79cb3bf](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/79cb3bf65912a53e981ecd53e85c815a7b0bc041))
* package agent skill natively and make init idempotent ([a9cf959](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a9cf9597253273582c2388d5bddea9d16596d4ee))
* package agent skill natively and make init idempotent ([9a7965d](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9a7965d28a78c666015c69bcc61f370eab1fb798))


### Bug Fixes

* configure release-please manifest ([fc89be9](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/fc89be9cd512d05af8b94f078ef6313e2c4a808a))
* configure release-please manifest to base from 0.2.1 ([c0915b3](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/c0915b3e9373df95e119c94b266f0c628a6fdd6c))
* make core logic and mcp server workspace-aware by injecting project_path ([1367e39](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1367e394085c9cfb4b5337e9b6e3578463d31946))
* orchestrate git commits for backlog migration and delete archive file ([8a71a3b](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/8a71a3b6aec74e2a08c5b11027b3a26f09bc2a3b))
* update release-please action path to resolve deprecation warning ([aaeed04](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/aaeed04ba39c0255e3e901d57190fe5cb573d806))


### Documentation

* add architecture documentation with mermaid diagrams ([a1f4969](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a1f49693c4d99fad503804452f23400956a9f4a0))
* add Buy Me a Coffee sponsorship option ([c4c7bfa](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/c4c7bfa9c315a7e8a9fd2e913acf9d4cf1a90621))
* add global uv tool install instructions ([7c0c1a5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7c0c1a578f6ad88864f6c263cdd70e9ecab2723e))
* **architecture:** add GitHub mode and SDD reconciliation layer ([3ae255c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/3ae255c366c8a0a94fab1c736de598b281a19f7d))
* clarify agent behavior rules in SKILL.md ([#2](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/2)) ([e055466](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/e055466f16665205a97e738597c5500441a310df))
* update distribution paths to use GitHub natively via uvx ([cfa5bb7](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/cfa5bb7599ff3d2b4a23bd756ea82cd51bbd9c49))

## 0.1.0 (2026-06-19)


### Features

* add 'agb' as a shorter CLI alias ([9aa7121](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9aa71214fd63d22032c57c3e6b22606d828de727))
* add blocker awareness with block/unblock commands and auto-status ([1306b35](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1306b358fcd5c3d686c412ad1f4d3fa438ad5c02))
* add framework detection and seeding via init --empty ([92d9120](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/92d91200d489547630e5d8a71f24bf1e90c3226b))
* add multi-line description field support to backlog items ([#3](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/3)) ([b43a4f8](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/b43a4f89cc3a2690fec4940322afc141bdcb5ec6))
* add next command and refactor sort logic into _compute_sorted_items ([58b3d1a](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/58b3d1acbc036326014cbcc6c13df3e60b882e8e))
* add status tracking with retention and zero-scoring for completed items ([475053c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/475053c37d3cc10c750cb3245ad5cd65d33ee733))
* add uv.lock for dependency management and clean up gitignore entry for qa_tests ([7456e30](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7456e3089e7060f5c8e218bec2232a6089f055e5))
* expose backlog via native MCP server ([457c9ec](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/457c9ec88e5b86c076e2274d2e255f052c4d5600))
* implement GitHub Projects V2 integration ([7a8a27c](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7a8a27ccd3f098d7275cb4513858e12ec174ce9b))
* implement Open-Spec and Spec-Kit seed parsers ([1bdcdd4](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1bdcdd4a1b1280c370cd90697d5d64dcdb1b6485))
* implement remove command to safely delete backlog items ([#5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/5)) ([79cb3bf](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/79cb3bf65912a53e981ecd53e85c815a7b0bc041))
* package agent skill natively and make init idempotent ([a9cf959](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a9cf9597253273582c2388d5bddea9d16596d4ee))
* package agent skill natively and make init idempotent ([9a7965d](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/9a7965d28a78c666015c69bcc61f370eab1fb798))


### Bug Fixes

* make core logic and mcp server workspace-aware by injecting project_path ([1367e39](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/1367e394085c9cfb4b5337e9b6e3578463d31946))
* orchestrate git commits for backlog migration and delete archive file ([8a71a3b](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/8a71a3b6aec74e2a08c5b11027b3a26f09bc2a3b))
* update release-please action path to resolve deprecation warning ([aaeed04](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/aaeed04ba39c0255e3e901d57190fe5cb573d806))


### Documentation

* add architecture documentation with mermaid diagrams ([a1f4969](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/a1f49693c4d99fad503804452f23400956a9f4a0))
* add Buy Me a Coffee sponsorship option ([c4c7bfa](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/c4c7bfa9c315a7e8a9fd2e913acf9d4cf1a90621))
* add global uv tool install instructions ([7c0c1a5](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/7c0c1a578f6ad88864f6c263cdd70e9ecab2723e))
* clarify agent behavior rules in SKILL.md ([#2](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/issues/2)) ([e055466](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/e055466f16665205a97e738597c5500441a310df))
* update distribution paths to use GitHub natively via uvx ([cfa5bb7](https://github.com/aegolius-labs/aio-agentic-sdlc-cli/commit/cfa5bb7599ff3d2b4a23bd756ea82cd51bbd9c49))
