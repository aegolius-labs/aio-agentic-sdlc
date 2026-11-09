"""Check that an installation works, without changing anything (HARDENING-AC1).

`dag-tool doctor` answers the adopter's first question, "is this installed
correctly?", through the same contracts the hosts use: the console entry
points, a real MCP handshake over stdio, and, when the current directory is a
project, whether its state files load. It never writes a file.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from aio_agentic_sdlc import __version__

ENTRY_POINTS = ("aio-sdlc", "dag-tool", "aio-agentic-sdlc-mcp")
SERVER_NAME = "aio-agentic-sdlc"


@dataclass
class Check:
    name: str
    passed: bool
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


def _entry_point(name: str) -> str | None:
    """Prefer the script next to this interpreter: that is the installed copy."""

    suffix = ".exe" if os.name == "nt" else ""
    beside = Path(sys.executable).with_name(name + suffix)
    if beside.is_file():
        return str(beside)
    return shutil.which(name)


def check_entry_points() -> Check:
    found = {name: _entry_point(name) for name in ENTRY_POINTS}
    missing = [name for name, path in found.items() if path is None]
    if missing:
        return Check(
            "entry points",
            False,
            "not found: " + ", ".join(missing),
            {"paths": found},
        )
    return Check("entry points", True, "all three found", {"paths": found})


async def _handshake(command: str, cwd: Path, timeout: float) -> dict[str, Any]:
    from mcp import StdioServerParameters, stdio_client
    from mcp.client import Client

    transport = stdio_client(StdioServerParameters(command=command, cwd=cwd))
    async with asyncio.timeout(timeout):
        async with Client(transport, mode="auto", raise_exceptions=True) as client:
            info = client.server_info
            protocol = client.protocol_version
            tools = await client.list_tools()
            resources = await client.list_resources()
            prompts = await client.list_prompts()
    return {
        "server": info.name if info else None,
        "server_version": info.version if info else None,
        "protocol": protocol,
        "tools": sorted(tool.name for tool in tools.tools),
        "resources": len(resources.resources),
        "prompts": len(prompts.prompts),
    }


def check_mcp_server(project_root: Path, *, timeout: float = 60.0) -> Check:
    command = _entry_point("aio-agentic-sdlc-mcp")
    if command is None:
        return Check("MCP server", False, "aio-agentic-sdlc-mcp is not installed")
    try:
        result = asyncio.run(_handshake(command, project_root, timeout))
    except Exception as error:  # noqa: BLE001 - any failure is the finding
        reason = str(error) or type(error).__name__
        return Check("MCP server", False, f"handshake failed: {reason}")
    if result["server"] != SERVER_NAME or not result["tools"]:
        return Check(
            "MCP server",
            False,
            f"unexpected server {result['server']!r} with "
            f"{len(result['tools'])} tools",
            result,
        )
    return Check(
        "MCP server",
        True,
        f"{result['server']} {result['server_version']}, protocol "
        f"{result['protocol']}: {len(result['tools'])} tools, "
        f"{result['resources']} resources, {result['prompts']} prompts",
        result,
    )


def check_project(project_root: Path) -> Check:
    """Load whatever project state exists. A directory with none is not a failure."""

    from aio_agentic_sdlc.dag_manager import DAGManager
    from aio_agentic_sdlc.evidence import EVIDENCE_LEDGER_FILE, load_evidence_ledger
    from aio_agentic_sdlc.workspace import (
        INTENTION_DAG_FILE,
        REALITY_DAG_FILE,
        WORKSPACE_DIR,
    )

    workspace = project_root / WORKSPACE_DIR
    if not workspace.is_dir():
        return Check(
            "project",
            True,
            f"no {WORKSPACE_DIR}/ here; run `aio-sdlc init` to start a project",
            {"initialized": False},
        )

    loaded: list[str] = []
    problems: list[str] = []
    for label, relative in (
        ("Intention DAG", INTENTION_DAG_FILE),
        ("Reality DAG", REALITY_DAG_FILE),
    ):
        path = project_root / relative
        if not path.is_file():
            continue
        try:
            manager = DAGManager.load(str(path))
            manager.validate()
            if relative == INTENTION_DAG_FILE:
                manager.validate_intent_ir(require_all=False)
            loaded.append(f"{label} ({len(manager.nodes)} nodes)")
        except Exception as error:  # noqa: BLE001 - any failure is the finding
            problems.append(f"{relative}: {error}")

    ledger = project_root / EVIDENCE_LEDGER_FILE
    if ledger.is_file():
        try:
            records = load_evidence_ledger(ledger).records
            loaded.append(f"evidence ledger ({len(records)} records)")
        except Exception as error:  # noqa: BLE001 - any failure is the finding
            problems.append(f"{EVIDENCE_LEDGER_FILE}: {error}")

    data = {"initialized": True, "loaded": loaded, "problems": problems}
    if problems:
        return Check("project", False, "; ".join(problems), data)
    detail = ", ".join(loaded) if loaded else "initialized, no state files yet"
    return Check("project", True, detail, data)


def run_doctor(
    project_root: str | Path = ".",
    *,
    mcp: bool = True,
    timeout: float = 60.0,
) -> dict[str, Any]:
    root = Path(project_root).resolve()
    checks = [
        Check(
            "package",
            True,
            f"aio-agentic-sdlc {__version__} on Python "
            f"{sys.version_info.major}.{sys.version_info.minor}",
            {"version": __version__},
        ),
        check_entry_points(),
    ]
    if mcp:
        checks.append(check_mcp_server(root, timeout=timeout))
    checks.append(check_project(root))
    return {
        "passed": all(check.passed for check in checks),
        "project_root": str(root),
        "checks": [asdict(check) for check in checks],
    }


def render_doctor(report: dict[str, Any]) -> str:
    lines = []
    for check in report["checks"]:
        mark = "ok  " if check["passed"] else "FAIL"
        lines.append(f"{mark} {check['name']}: {check['detail']}")
    lines.append("")
    lines.append("All checks passed." if report["passed"] else "Some checks failed.")
    return "\n".join(lines)
