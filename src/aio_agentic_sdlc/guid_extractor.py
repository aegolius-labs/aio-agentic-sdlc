"""The Canonical GUID Extractor: find every Intention GUID the project claims.

A file claims an Intention node in one of two ways:

- a Python comment `# aio-sdlc-node: <uuid>`, found with Tree-Sitter, so a
  marker inside a string or docstring never counts;
- an agent definition's YAML frontmatter, `metadata.node_id: <uuid>` or a
  top-level `aio-sdlc-node: <uuid>`, read with PyYAML. Agent definitions are
  the Markdown files under `.agents/agents/`, the same files Reality observes
  as agents.

The extractor is read-only. It reports what it finds and three problems:
a marker whose value is not a UUID, a GUID claimed in more than one place, and
a GUID the Intention DAG does not define. It never writes a marker: writing one
is an identity claim that goes through `dag-tool mapping` review.
"""

from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from tree_sitter import Parser, Query, QueryCursor

from aio_agentic_sdlc.parsers.python_parser import PYTHON_LANGUAGE
from aio_agentic_sdlc.reality_dag_generator import (
    is_ignored_directory,
    is_test_directory,
)
from aio_agentic_sdlc.source_markers import NODE_MARKER_PREFIX, canonical_node_marker
from aio_agentic_sdlc.workspace import INTENTION_DAG_FILE

COMMENT = "comment"
FRONTMATTER = "frontmatter"
_MARKER_CANDIDATE = re.compile(r"^#\s*aio-sdlc-node\s*:")
AGENT_DIRECTORY = ".agents/agents/"
_FRONTMATTER_KEY = NODE_MARKER_PREFIX.rstrip(":")


class GuidExtractionError(ValueError):
    """The project cannot be scanned."""


@dataclass(frozen=True)
class GuidMarker:
    guid: str
    path: str
    line: int
    source: str


@dataclass(frozen=True)
class MalformedMarker:
    path: str
    line: int
    source: str
    text: str


def _canonical(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return str(UUID(value.strip()))
    except ValueError:
        return None


_PARSER = Parser(PYTHON_LANGUAGE)
_COMMENTS = Query(PYTHON_LANGUAGE, f"({COMMENT}) @{COMMENT}")


def extract_comment_markers(
    content: bytes, path: str
) -> tuple[list[GuidMarker], list[MalformedMarker]]:
    """Return the node markers in one Python file's comments."""

    tree = _PARSER.parse(content)
    captures = QueryCursor(_COMMENTS).captures(tree.root_node)
    markers: list[GuidMarker] = []
    malformed: list[MalformedMarker] = []
    for node in sorted(captures.get(COMMENT, []), key=lambda n: n.start_byte):
        text = node.text.decode("utf-8", errors="replace")
        if not _MARKER_CANDIDATE.match(text):
            continue
        line = node.start_point.row + 1
        guid = canonical_node_marker(text)
        if guid is None:
            malformed.append(MalformedMarker(path, line, COMMENT, text.strip()))
        else:
            markers.append(GuidMarker(guid, path, line, COMMENT))
    return markers, malformed


def _frontmatter(text: str) -> tuple[str, int] | None:
    """Return the frontmatter block and its first line, or None."""

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index]), 2
    return None


def _key_line(block: str, key: str, first_line: int) -> int:
    pattern = re.compile(rf"^\s*['\"]?{re.escape(key)}['\"]?\s*:")
    for offset, line in enumerate(block.splitlines()):
        if pattern.match(line):
            return first_line + offset
    return first_line


def extract_frontmatter_markers(
    text: str, path: str
) -> tuple[list[GuidMarker], list[MalformedMarker]]:
    """Return the node GUIDs an agent definition's frontmatter declares."""

    found = _frontmatter(text)
    if found is None:
        return [], []
    block, first_line = found
    try:
        data = yaml.safe_load(block)
    except yaml.YAMLError:
        return [], [MalformedMarker(path, first_line, FRONTMATTER, "invalid YAML")]
    if not isinstance(data, dict):
        return [], []

    values = []
    metadata = data.get("metadata")
    if isinstance(metadata, dict) and "node_id" in metadata:
        values.append(("node_id", metadata["node_id"]))
    if _FRONTMATTER_KEY in data:
        values.append((_FRONTMATTER_KEY, data[_FRONTMATTER_KEY]))

    markers: list[GuidMarker] = []
    malformed: list[MalformedMarker] = []
    for key, value in values:
        line = _key_line(block, key, first_line)
        guid = _canonical(value)
        if guid is None:
            malformed.append(
                MalformedMarker(path, line, FRONTMATTER, f"{key}: {value}")
            )
        else:
            markers.append(GuidMarker(guid, path, line, FRONTMATTER))
    return markers, malformed


def _iter_files(root: Path):
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(
            name
            for name in dirs
            if not is_ignored_directory(name) and not is_test_directory(name)
        )
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            is_agent = name.endswith(".md") and relative.startswith(AGENT_DIRECTORY)
            if (name.endswith(".py") or is_agent) and not path.is_symlink():
                if path.is_file():
                    yield path


def _intention_ids(root: Path) -> set[str] | None:
    path = root / INTENTION_DAG_FILE
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as error:
        raise GuidExtractionError(f"{INTENTION_DAG_FILE} does not load: {error}")
    nodes = data.get("nodes") if isinstance(data, dict) else None
    if not isinstance(nodes, list):
        raise GuidExtractionError(f"{INTENTION_DAG_FILE} has no node list")
    return {
        str(node["id"]) for node in nodes if isinstance(node, dict) and "id" in node
    }


def scan_project(project_path: str | Path = ".") -> dict[str, Any]:
    """Extract every claimed GUID under the project and report the problems."""

    root = Path(project_path).resolve()
    if not root.is_dir():
        raise GuidExtractionError(f"not a directory: {root}")

    markers: list[GuidMarker] = []
    malformed: list[MalformedMarker] = []
    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        content = path.read_bytes()
        if path.suffix == ".py":
            found, bad = extract_comment_markers(content, relative)
        else:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                continue
            found, bad = extract_frontmatter_markers(text, relative)
        markers.extend(found)
        malformed.extend(bad)

    by_guid: dict[str, list[GuidMarker]] = {}
    for marker in markers:
        by_guid.setdefault(marker.guid, []).append(marker)
    duplicates = {
        guid: [f"{m.path}:{m.line}" for m in claimed]
        for guid, claimed in sorted(by_guid.items())
        if len(claimed) > 1
    }

    known = _intention_ids(root)
    unknown = (
        [] if known is None else [asdict(m) for m in markers if m.guid not in known]
    )

    return {
        "project_root": str(root),
        "intention_dag": known is not None,
        "passed": not (malformed or duplicates or unknown),
        "markers": [asdict(m) for m in markers],
        "malformed": [asdict(m) for m in malformed],
        "duplicates": duplicates,
        "unknown": unknown,
    }


def render_scan(report: dict[str, Any]) -> str:
    lines = [f"{len(report['markers'])} node markers found."]
    for item in report["malformed"]:
        lines.append(
            f"malformed {item['source']} marker at {item['path']}:{item['line']}: "
            f"{item['text']}"
        )
    for guid, places in report["duplicates"].items():
        lines.append(f"{guid} is claimed more than once: {', '.join(places)}")
    for item in report["unknown"]:
        lines.append(
            f"{item['guid']} at {item['path']}:{item['line']} is not an "
            "Intention DAG node"
        )
    if not report["intention_dag"]:
        lines.append(f"No {INTENTION_DAG_FILE}; unknown GUIDs were not checked.")
    lines.append("No problems." if report["passed"] else "Problems found.")
    return "\n".join(lines)
