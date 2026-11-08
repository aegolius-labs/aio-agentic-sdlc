"""Closed-loop reference demo (ROADMAP M4, Intention node ``cb02a996``).

``dag-tool demo`` builds a throwaway project and takes one requirement
through the whole loop with the framework's public commands:

1. Intake records a person's want as Intention node, ``review_required``.
2. A person approves the intent.
3. Reality is generated and triage asks whether the implementation is
   missing; a person decides that it is, which authorizes the work.
4. ``aio-sdlc apply`` hands the task to an agent through the runtime adapter.
5. Reality is regenerated and a person approves which symbol implements it.
6. The tests run; their result is recorded as acceptance evidence, and a
   person accepts the result.
7. ``aio-sdlc apply`` runs again and the task completes because it left the
   diff, not because the agent returned.
8. ``dag-tool trace`` writes a plain-language traceability report.

Every approval is a gate. The demo stops and asks the named approver at each
one unless ``--yes`` is given, and it records that name as the approver, so
nothing in the record claims a person approved what nobody saw.

The default agent is a scripted stand-in (``python -m
aio_agentic_sdlc.closed_loop_demo agent``) so the demo is deterministic and
needs no model access. ``--agent-command "claude -p"`` runs a real agent
instead through the same ``command`` runtime.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

import yaml

DEMO_INTENT_ID = "9a3c2a51-6a8e-4c39-9d43-0d6f2b6a4f10"
DEMO_DAG_NAME = "Closed-loop demo"
DEMO_REQUIREMENT = "Token Verifier"
DEMO_WANT = (
    "API tokens must be compared in constant time, so response timing does "
    "not leak how much of a guessed token was right."
)
GENERATOR = "aio-agentic-sdlc/closed-loop-demo"
INTAKE_ACTOR = "sdlc_intake"
REPORT_FILE = "TRACEABILITY.md"

AGENT_SOURCE = '''"""Token verification for the demo application."""

import hmac


def verify_token(expected: str, provided: str) -> bool:
    """Return whether provided matches expected, compared in constant time."""
    return hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8"))
'''

AGENT_TESTS = """import unittest

from demo_app.tokens import verify_token


class VerifyTokenTest(unittest.TestCase):
    def test_matching_token_is_accepted(self):
        self.assertTrue(verify_token("s3cret-token", "s3cret-token"))

    def test_other_tokens_are_rejected(self):
        for guess in ("s3cret-tokeN", "s3cret", "", "s3cret-token-and-more"):
            self.assertFalse(verify_token("s3cret-token", guess))


if __name__ == "__main__":
    unittest.main()
"""


class DemoError(RuntimeError):
    """The loop did not close; the message says where it stopped."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def intake_payload() -> dict:
    """The Intent IR Intake records for the stated want, before approval."""

    return {
        "schema_version": 1,
        "provenance": [
            {
                "source_type": "human_statement",
                "reference": "closed-loop-demo:stated-want",
                "statement": DEMO_WANT,
            }
        ],
        "assumptions": [
            "One function performs the comparison, so one symbol implements it."
        ],
        "ambiguities": [],
        "confidence": 0.9,
        "acceptance_criteria": [
            {
                "id": "TOKEN-AC1",
                "statement": (
                    "A matching token is accepted and every other token is "
                    "rejected, using a constant-time comparison."
                ),
                "required_evidence": ["test:token-verifier"],
            },
            {
                "id": "TOKEN-AC2",
                "statement": "A reviewer accepts the implementation.",
                "required_evidence": ["review:token-verifier-acceptance"],
            },
        ],
        "revision_history": [
            {
                "revision": 1,
                "recorded_at": _now(),
                "actor": INTAKE_ACTOR,
                "generator_version": GENERATOR,
                "summary": "Compiled the stated want into reviewable intent.",
            }
        ],
        "responsible_agent": INTAKE_ACTOR,
        "generator_version": GENERATOR,
        "approval": {"state": "review_required"},
    }


def scripted_agent(stdin_text: str, project: Path) -> None:
    """The deterministic stand-in agent: implement what the work order asks.

    It refuses a work order that does not carry the requirement, so the demo
    proves the agent is told what to build rather than guessing.
    """

    if DEMO_REQUIREMENT not in stdin_text or "TOKEN-AC1" not in stdin_text:
        raise DemoError("the work order does not carry the requirement")
    package = project / "src" / "demo_app"
    package.mkdir(parents=True, exist_ok=True)
    (package / "tokens.py").write_text(AGENT_SOURCE, encoding="utf-8")
    tests = project / "tests"
    tests.mkdir(exist_ok=True)
    (tests / "test_tokens.py").write_text(AGENT_TESTS, encoding="utf-8")


class ClosedLoopDemo:
    """Run the loop in ``project`` with the framework's public commands."""

    def __init__(
        self,
        project: str | Path,
        *,
        approver: str,
        confirm: Callable[[str], bool],
        agent_command: Sequence[str] | None = None,
        echo: Callable[[str], None] = print,
    ):
        if not approver.strip():
            raise DemoError("an approver name is required")
        self.project = Path(project).resolve()
        self.approver = approver.strip()
        self.confirm = confirm
        self.agent_command = (
            list(agent_command)
            if agent_command
            else [
                sys.executable,
                "-m",
                "aio_agentic_sdlc.closed_loop_demo",
                "agent",
            ]
        )
        self.echo = echo
        self.workspace = self.project / ".aio-agentic-sdlc"
        self.intention = self.workspace / "intention-dag.yaml"
        self.reality = self.workspace / "reality-dag.yaml"
        self.decisions = self.workspace / "changes" / "demo-triage-decisions.json"

    # -- plumbing ---------------------------------------------------------

    def _run(
        self,
        program: str,
        args: Sequence[str],
        *,
        env: dict | None = None,
        quiet: bool = False,
    ) -> str:
        module = {
            "dag-tool": "aio_agentic_sdlc.dag_cli",
            "aio-sdlc": "aio_agentic_sdlc.cli",
        }[program]
        shown = " ".join(shlex.quote(a) for a in args)
        self.echo(f"  $ {program} {shown}")
        result = subprocess.run(
            [sys.executable, "-m", module, *args],
            cwd=self.project,
            env={**os.environ, **(env or {})},
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise DemoError(
                f"`{program} {shown}` failed:\n{result.stderr or result.stdout}"
            )
        if not quiet and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                self.echo(f"    {line}")
        return result.stdout

    def _gate(self, title: str, details: Sequence[str]) -> None:
        self.echo("")
        self.echo(f"APPROVAL GATE: {title}")
        for line in details:
            self.echo(f"  {line}")
        if not self.confirm(f"Approve as {self.approver}?"):
            raise DemoError(f"stopped at the gate: {title}")

    def _step(self, number: int, title: str) -> None:
        self.echo("")
        self.echo(f"[{number}/8] {title}")

    def _generate_reality(self) -> dict:
        self._run(
            "dag-tool",
            [
                "generate-reality",
                "--dir",
                ".",
                "--system",
                DEMO_DAG_NAME,
                "--output",
                ".aio-agentic-sdlc/reality-dag.yaml",
            ],
        )
        return yaml.safe_load(self.reality.read_text(encoding="utf-8")) or {}

    def _triage(self, decisions: bool = False) -> dict:
        args = [
            "triage",
            "--intention",
            ".aio-agentic-sdlc/intention-dag.yaml",
            "--reality",
            ".aio-agentic-sdlc/reality-dag.yaml",
            "--format",
            "json",
        ]
        if decisions:
            args += ["--decisions", str(self.decisions.relative_to(self.project))]
        return json.loads(self._run("dag-tool", args, quiet=True))

    def _triage_item(self, report: dict) -> dict | None:
        for item in report["items"]:
            if item["audit"].get("subject_key") == f"intent:{DEMO_INTENT_ID}":
                return item
        return None

    # -- the loop ---------------------------------------------------------

    def run(self) -> Path:
        self.project.mkdir(parents=True, exist_ok=True)
        if any(self.project.iterdir()):
            raise DemoError(f"the demo needs an empty directory: {self.project}")

        self._step(1, "Create an empty project and initialize the framework")
        package = self.project / "src" / "demo_app"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            '"""Demo application."""\n', encoding="utf-8"
        )
        self._run("aio-sdlc", ["init", "--yes", "--empty"], quiet=True)
        (self.workspace / "config.json").write_text(
            json.dumps(
                {
                    **json.loads(
                        (self.workspace / "config.json").read_text(encoding="utf-8")
                    ),
                    "runtime": "command",
                    "runtime_command": self.agent_command,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        self.echo(f"  Agent runtime: {' '.join(self.agent_command)}")

        self._step(2, "Intake records the stated want as reviewable intent")
        self.echo(f'  Want: "{DEMO_WANT}"')
        payload = self.workspace / "changes" / "demo-intake-payload.json"
        payload.write_text(json.dumps(intake_payload(), indent=2), encoding="utf-8")
        self._run(
            "dag-tool",
            [
                "intent",
                "create-node",
                "--file",
                ".aio-agentic-sdlc/intention-dag.yaml",
                "--dag-name",
                DEMO_DAG_NAME,
                "--node-id",
                DEMO_INTENT_ID,
                "--type",
                "component",
                "--name",
                DEMO_REQUIREMENT,
                "--domain",
                "security",
                "--description",
                "Compares API tokens in constant time.",
                "--payload-file",
                str(payload.relative_to(self.project)),
            ],
        )
        self._gate(
            "approve the intent",
            [
                f"Requirement: {DEMO_REQUIREMENT}",
                "TOKEN-AC1: a matching token is accepted, every other token is "
                "rejected, in constant time (needs a passing test).",
                "TOKEN-AC2: a reviewer accepts the implementation (needs a "
                "person's acceptance).",
            ],
        )
        self._run(
            "dag-tool",
            [
                "intent",
                "decide",
                "--file",
                ".aio-agentic-sdlc/intention-dag.yaml",
                "--node-id",
                DEMO_INTENT_ID,
                "--state",
                "approved",
                "--decided-by",
                self.approver,
                "--decided-at",
                _now(),
                "--rationale",
                "The requirement and its acceptance criteria say what is wanted.",
                "--expected-revision",
                "1",
            ],
        )

        self._step(3, "Compare intent with reality and authorize the work")
        self._generate_reality()
        item = self._triage_item(self._triage())
        if item is None or item["classification"] != "needs_classification":
            raise DemoError(f"expected triage to ask for a decision, got {item}")
        self.echo(f"  Triage: {item['reason']}")
        self._gate(
            "decide that the implementation is missing",
            [
                "No code in src/ implements the requirement yet.",
                "Deciding 'missing implementation' authorizes an agent to build it.",
            ],
        )
        self._run(
            "dag-tool",
            [
                "triage-decide",
                "--intention",
                ".aio-agentic-sdlc/intention-dag.yaml",
                "--reality",
                ".aio-agentic-sdlc/reality-dag.yaml",
                "--decisions",
                str(self.decisions.relative_to(self.project)),
                "--subject-key",
                f"intent:{DEMO_INTENT_ID}",
                "--classification",
                "missing_implementation",
                "--rationale",
                "src/demo_app has no token verifier.",
                "--evidence",
                "src/demo_app",
                "--decided-by",
                self.approver,
                "--decided-at",
                _now(),
            ],
        )

        self._step(4, "apply hands the authorized task to the agent")
        before = {
            node["id"]
            for node in (yaml.safe_load(self.reality.read_text("utf-8")) or {}).get(
                "nodes", []
            )
        }
        self._run(
            "aio-sdlc",
            ["apply", "--decisions", str(self.decisions.relative_to(self.project))],
        )

        self._step(5, "Regenerate reality and approve which code implements it")
        reality = self._generate_reality()
        added = [
            node
            for node in reality.get("nodes", [])
            if node["id"] not in before and node.get("type") == "component"
        ]
        if len(added) != 1:
            names = ", ".join(n["name"] for n in added) or "none"
            raise DemoError(
                f"expected the agent to add exactly one component, found: {names}"
            )
        candidate = added[0]
        review = json.loads(
            self._run(
                "dag-tool",
                [
                    "mapping",
                    "review",
                    "--project-path",
                    str(self.project),
                    "--intent-id",
                    DEMO_INTENT_ID,
                    "--candidate-reality-id",
                    candidate["id"],
                    "--format",
                    "json",
                ],
                quiet=True,
            )
        )
        if not review["approval"].get("supported"):
            raise DemoError(f"mapping review blocked: {review['approval']}")
        source = review["candidates"][0]["source"]
        self._gate(
            "approve which code implements the requirement",
            [
                f"`{source['symbol_name']}` ({source['symbol_kind']}) in "
                f"{source['path']}, line {source['definition_line']}.",
                "This links identity only: it does not prove the acceptance "
                "criteria.",
            ],
        )
        self._run(
            "dag-tool",
            [
                "mapping",
                "approve",
                "--project-path",
                str(self.project),
                "--intent-id",
                DEMO_INTENT_ID,
                "--candidate-reality-id",
                candidate["id"],
                "--evidence-digest",
                review["evidence_digest"],
                "--selection-mode",
                "explicit_observed_guid",
                "--approved-by",
                self.approver,
                "--approved-at",
                _now(),
                "--rationale",
                f"{source['symbol_name']} performs the token comparison.",
            ],
            quiet=True,
        )
        self._generate_reality()

        self._step(6, "Run the tests and record the acceptance evidence")
        self.echo("  $ python -m unittest discover -s tests")
        tests = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
            cwd=self.project,
            env={**os.environ, "PYTHONPATH": str(self.project / "src")},
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        summary = (tests.stderr.strip().splitlines() or ["no output"])[-1]
        ran = next(
            (line for line in tests.stderr.splitlines() if line.startswith("Ran ")),
            summary,
        )
        self.echo(f"    {ran}: {summary}")
        if tests.returncode != 0:
            raise DemoError(
                f"the tests failed, so no evidence is recorded:\n{tests.stderr}"
            )
        self._run(
            "dag-tool",
            [
                "evidence",
                "record",
                "--project-path",
                ".",
                "--intent-id",
                DEMO_INTENT_ID,
                "--criterion-id",
                "TOKEN-AC1",
                "--reference",
                "test:token-verifier",
                "--level",
                "tested",
                "--locator",
                "tests/test_tokens.py",
                "--summary",
                f"python -m unittest discover -s tests: {ran}, {summary}",
                "--recorded-by",
                "closed-loop-demo",
                "--recorded-at",
                _now(),
            ],
        )
        self._gate(
            "accept the implementation",
            [
                f"The tests passed ({ran}).",
                f"Read {source['path']} before accepting.",
            ],
        )
        self._run(
            "dag-tool",
            [
                "evidence",
                "record",
                "--project-path",
                ".",
                "--intent-id",
                DEMO_INTENT_ID,
                "--criterion-id",
                "TOKEN-AC2",
                "--reference",
                "review:token-verifier-acceptance",
                "--level",
                "approved",
                "--locator",
                source["path"],
                "--summary",
                f"{self.approver} accepted the implementation after the tests passed.",
                "--recorded-by",
                self.approver,
                "--recorded-at",
                _now(),
                "--approved-by",
                self.approver,
            ],
        )

        self._step(7, "apply again: the task completes because it left the diff")
        self._run("aio-sdlc", ["apply"])
        if self._triage_item(self._triage()) is not None:
            raise DemoError("the requirement is still in the diff")
        backlog = json.loads(
            (self.workspace / "backlog.json").read_text(encoding="utf-8")
        )
        statuses = [
            item.get("status")
            for item in backlog.get("nodes", {}).values()
            if item.get("canonical_intent_id") == DEMO_INTENT_ID
        ]
        if statuses != ["Completed"]:
            raise DemoError(f"expected one completed task, found {statuses}")
        self.echo("  The requirement left the diff and its task is Completed.")

        self._step(8, "Write the traceability report")
        report = self.project / REPORT_FILE
        self._run(
            "dag-tool",
            [
                "trace",
                "--project-path",
                ".",
                "--intent-id",
                DEMO_INTENT_ID,
                "--decisions",
                str(self.decisions.relative_to(self.project)),
                "--output",
                REPORT_FILE,
            ],
        )
        self.echo("")
        self.echo(f"The loop closed. Read the report: {report}")
        return report


def _agent_main() -> int:
    try:
        scripted_agent(sys.stdin.read(), Path.cwd())
    except DemoError as error:
        print(f"scripted agent: {error}", file=sys.stderr)
        return 1
    print("scripted agent: wrote src/demo_app/tokens.py and tests/test_tokens.py")
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["agent"]:
        raise SystemExit(_agent_main())
    print("usage: python -m aio_agentic_sdlc.closed_loop_demo agent", file=sys.stderr)
    raise SystemExit(2)
