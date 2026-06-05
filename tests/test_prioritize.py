"""Tests for the topological sorting and scoring engine in prioritize_cmd."""
import json
import os
import sys
import pytest

# Ensure the source package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agentic_backlog.cli import load_backlog, save_backlog, BACKLOG_FILE


@pytest.fixture(autouse=True)
def clean_backlog(tmp_path, monkeypatch):
    """Run every test inside a temporary directory so backlog.json is isolated."""
    monkeypatch.chdir(tmp_path)


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_item(impact, effort, requires=None, **extra):
    item = {
        "impact": impact,
        "effort": effort,
        "category": extra.get("category", "Business Value"),
        "requires": requires or [],
        "ai_driven": False,
        "scores": {},
    }
    item.update(extra)
    return item


def _run_prioritize():
    """Import and call prioritize_cmd programmatically."""
    from agentic_backlog.cli import prioritize_cmd
    import argparse
    prioritize_cmd(argparse.Namespace())


def _load():
    return load_backlog()


def _save(items_dict):
    save_backlog({"items": items_dict})


# ── tests ────────────────────────────────────────────────────────────────────

class TestSingleItem:
    def test_single_item_scores(self):
        _save({"alpha": _make_item(impact=5, effort=2)})
        _run_prioritize()
        data = _load()
        item = data["items"]["alpha"]
        # base = impact + (5 - effort) = 5 + 3 = 8
        assert item["scores"]["base"] == 8
        assert item["scores"]["final"] == 8  # no dependents → no boost


class TestLinearChain:
    """A → B → C  (C requires B, B requires A)."""

    def test_order_and_scores(self):
        _save({
            "A": _make_item(3, 3),
            "B": _make_item(4, 2, requires=["A"]),
            "C": _make_item(5, 1, requires=["B"]),
        })
        _run_prioritize()
        data = _load()
        keys = list(data["items"].keys())
        # Topological: A before B before C
        assert keys.index("A") < keys.index("B") < keys.index("C")


class TestDiamondDependency:
    """
    D depends on B and C; B and C both depend on A.
         A
        / \\
       B   C
        \\ /
         D
    """

    def test_diamond(self):
        _save({
            "A": _make_item(2, 2),
            "B": _make_item(3, 3, requires=["A"]),
            "C": _make_item(3, 3, requires=["A"]),
            "D": _make_item(4, 1, requires=["B", "C"]),
        })
        _run_prioritize()
        data = _load()
        keys = list(data["items"].keys())
        assert keys.index("A") < keys.index("B")
        assert keys.index("A") < keys.index("C")
        assert keys.index("B") < keys.index("D")
        assert keys.index("C") < keys.index("D")


class TestCircularDependency:
    def test_circular_raises(self):
        _save({
            "X": _make_item(3, 3, requires=["Y"]),
            "Y": _make_item(3, 3, requires=["X"]),
        })
        with pytest.raises(SystemExit):
            _run_prioritize()
