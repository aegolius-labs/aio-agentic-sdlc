"""A write that would close a dependency cycle is rejected before it lands."""

import pytest

from aio_agentic_sdlc.cli import load_backlog, save_backlog
from aio_agentic_sdlc.core import BacklogOperationError, add_item, update_item


@pytest.fixture(autouse=True)
def clean_backlog(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_backlog({})


def _add(name, requires=None):
    add_item(name, 3, 3, "core", description=f"{name} work", requires=requires)


def _requires():
    edges = load_backlog().get("edges", [])
    return sorted((e["from"], e["to"]) for e in edges if e["relation"] == "requires")


def test_add_rejects_self_dependency():
    with pytest.raises(BacklogOperationError, match="D -> D"):
        _add("D", requires="D")
    assert "D" not in load_backlog()["nodes"]


def test_update_rejects_dependency_that_closes_a_cycle():
    _add("A")
    _add("B", requires="A")
    _add("C", requires="B")
    before = load_backlog()

    with pytest.raises(BacklogOperationError, match="A -> C -> B -> A"):
        update_item("A", requires="C")

    assert load_backlog() == before


def test_acyclic_dependencies_are_still_accepted():
    _add("A")
    _add("B", requires="A")
    _add("C", requires="A,B")
    update_item("A", requires="")
    assert _requires() == [("B", "A"), ("C", "A"), ("C", "B")]


def test_missing_dependency_is_still_created_as_placeholder():
    warnings = add_item("A", 3, 3, "core", description="A work", requires="Later")
    assert any("Later" in warning for warning in warnings)
    assert "Later" in load_backlog()["nodes"]
