"""The intent translation benchmark (ROADMAP M4, BENCHMARK-AC1 and AC2).

The packaged reference translations are the scorer's positive control: a
faithful translation must pass every threshold. Each metric then gets a
negative control that makes exactly that metric fire.
"""

import json
import shutil

import pytest
from click.testing import CliRunner

from aio_agentic_sdlc.dag_cli import cli
from aio_agentic_sdlc.intent_benchmark import (
    BenchmarkError,
    default_corpus_path,
    load_corpus,
    render_report,
    run_translator,
    score,
    score_case,
)

REFERENCE = default_corpus_path() / "reference"


@pytest.fixture
def run_dir(tmp_path):
    target = tmp_path / "run"
    shutil.copytree(REFERENCE, target)
    return target


def _edit(run_dir, case, change):
    path = run_dir / f"{case}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    change(data)
    path.write_text(json.dumps(data), encoding="utf-8")


def _metric(report, name):
    return next(c for c in report["checks"] if c["metric"] == name)


def test_corpus_is_versioned_and_covers_every_dimension():
    corpus = load_corpus()

    assert corpus["corpus"] == "intent-translation" and corpus["version"] == 1
    expected = [case["expected"] for case in corpus["cases"]]
    assert any(e["requirements"] for e in expected)
    assert any(e["constraints"] for e in expected)
    assert any(e["dependencies"] for e in expected)
    assert any(e["ambiguities"] for e in expected)
    assert any(e["evidence"] for e in expected)
    assert sum(1 for case in corpus["cases"] if case.get("feedback")) >= 2
    assert set(corpus["thresholds"]) == {
        "omission_rate_max",
        "invention_rate_max",
        "dependency_errors_max",
        "unjustified_completions_max",
        "stability_min",
        "correction_quality_min",
    }


def test_reference_translations_pass_every_threshold():
    report = score(load_corpus(), [REFERENCE, REFERENCE])

    assert report["passed"] is True
    assert report["metrics"] == {
        "omission_rate": 0.0,
        "invention_rate": 0.0,
        "dependency_errors": 0,
        "unjustified_completions": 0,
        "stability": 1.0,
        "correction_quality": 1.0,
    }


def test_omissions_are_reported_by_item(run_dir):
    _edit(
        run_dir,
        "api-rate-limit",
        lambda d: d.update(acceptance_criteria=d["acceptance_criteria"][:1]),
    )

    report = score(load_corpus(), [run_dir])
    case = next(c for c in report["cases"] if c["id"] == "api-rate-limit")

    assert case["result"]["omitted"] == [
        "requirements:status-429",
        "requirements:retry-after",
    ]
    assert report["metrics"]["omission_rate"] > 0


def test_inventions_and_forbidden_additions_are_reported(run_dir):
    def invent(data):
        data["acceptance_criteria"].append(
            {
                "id": "AC9",
                "statement": "An email notification is sent on every lockout.",
                "required_evidence": ["test:lockout-email"],
            }
        )

    _edit(run_dir, "login-lockout", invent)

    report = score(load_corpus(), [run_dir])
    case = next(c for c in report["cases"] if c["id"] == "login-lockout")

    assert case["result"]["invented"] == [
        "An email notification is sent on every lockout."
    ]
    assert report["metrics"]["invention_rate"] > 0


def test_missing_and_invented_dependencies_are_errors(run_dir):
    _edit(
        run_dir,
        "shipping-push",
        lambda d: d.update(
            dependencies=[{"target": "SMS Relay", "type": "depends_on"}]
        ),
    )

    report = score(load_corpus(), [run_dir])

    assert report["metrics"]["dependency_errors"] == 3
    assert _metric(report, "dependency_errors")["passed"] is False
    assert report["passed"] is False


def test_self_approval_and_self_resolved_ambiguity_are_unjustified(run_dir):
    def approve(data):
        data["approval"] = {
            "state": "approved",
            "approved_by": "translator",
            "approved_at": "2026-11-08T00:00:00Z",
        }

    def resolve(data):
        data["ambiguities"][0].update(status="resolved", resolution="Guessed.")

    _edit(run_dir, "invoice-export", approve)
    _edit(run_dir, "password-reset", resolve)

    report = score(load_corpus(), [run_dir])

    assert report["metrics"]["unjustified_completions"] == 2
    assert report["passed"] is False


def test_stability_compares_what_each_run_found(run_dir, tmp_path):
    second = tmp_path / "second"
    shutil.copytree(REFERENCE, second)
    (second / "dark-mode.json").unlink()

    report = score(load_corpus(), [run_dir, second])

    assert report["metrics"]["stability"] == pytest.approx(7 / 8, abs=1e-4)
    assert next(c for c in report["cases"] if c["id"] == "dark-mode")["stable"] is False


def test_correction_quality_counts_feedback_taken_in(run_dir):
    _edit(
        run_dir,
        "password-reset.after",
        lambda d: d.update(acceptance_criteria=d["acceptance_criteria"][:1]),
    )

    report = score(load_corpus(), [run_dir])

    assert report["metrics"]["correction_quality"] == 0.5
    assert _metric(report, "correction_quality")["passed"] is False


def test_a_missing_translation_omits_everything_it_expected(run_dir):
    (run_dir / "admin-audit-log.json").unlink()

    report = score(load_corpus(), [run_dir])

    assert report["totals"]["missing_translations"] == 1
    assert report["metrics"]["omission_rate"] > 0.1
    assert "admin-audit-log: no translation" in render_report(report)


def test_a_translation_that_is_not_intent_ir_fails_its_case(run_dir):
    (run_dir / "dark-mode.json").write_text('{"summary": "dark"}', encoding="utf-8")

    report = score(load_corpus(), [run_dir])

    assert report["totals"]["invalid_translations"] == 1
    case = next(c for c in report["cases"] if c["id"] == "dark-mode")
    assert case["invalid"].startswith("not valid Intent IR")
    assert "dark-mode: invalid translation" in render_report(report)


def test_score_case_rejects_a_payload_that_is_not_intent_ir():
    with pytest.raises(BenchmarkError, match="not valid Intent IR"):
        score_case({"requirements": []}, {"summary": "dark"})


def test_matching_uses_word_starts_not_arbitrary_substrings():
    expected = {
        "requirements": [{"id": "default", "match": [["os"], ["default"]]}],
    }
    base = json.loads((REFERENCE / "dark-mode.json").read_text(encoding="utf-8"))
    base["acceptance_criteria"] = [
        {
            "id": "AC1",
            "statement": "Most users get the default theme.",
            "required_evidence": ["test:x"],
        }
    ]

    assert score_case(expected, base)["omitted"] == ["requirements:default"]


def test_score_command_exits_by_thresholds(run_dir):
    runner = CliRunner()
    passed = runner.invoke(
        cli, ["benchmark-intent", "score", "--translations", str(run_dir)]
    )
    assert passed.exit_code == 0, passed.output
    assert "PASSED" in passed.output

    (run_dir / "shipping-push.json").unlink()
    failed = runner.invoke(
        cli,
        [
            "benchmark-intent",
            "score",
            "--translations",
            str(run_dir),
            "--format",
            "json",
        ],
    )
    assert failed.exit_code == 1
    assert json.loads(failed.output)["passed"] is False


def test_run_writes_one_translation_per_case_and_feedback_revisions(tmp_path):
    script = tmp_path / "translator.py"
    script.write_text(
        "import json, pathlib, sys\n"
        "prompt = sys.stdin.read()\n"
        f"ref = pathlib.Path({str(REFERENCE)!r})\n"
        "import yaml\n"
        "for case in yaml.safe_load(open(ref.parent / 'corpus.yaml'))['cases']:\n"
        "    if case['request'] in prompt:\n"
        "        name = case['id'] + ('.after' if 'feedback:' in prompt else '')\n"
        "        print('Here it is:', (ref / (name + '.json')).read_text())\n",
        encoding="utf-8",
    )
    import sys

    failures = run_translator(
        load_corpus(), [sys.executable, str(script)], tmp_path / "out"
    )

    assert failures == []
    written = sorted(p.name for p in (tmp_path / "out").iterdir())
    assert written == sorted(p.name for p in REFERENCE.iterdir())
    assert score(load_corpus(), [tmp_path / "out"])["passed"] is True


def test_splitting_a_requirement_over_criteria_is_not_an_invention(run_dir):
    def split(data):
        data["acceptance_criteria"] = [
            {
                "id": "AC1",
                "statement": "After 5 failed logins in a row an account is locked.",
                "required_evidence": ["test:lockout"],
            },
            {
                "id": "AC2",
                "statement": "A locked account stays locked for 15 minutes.",
                "required_evidence": ["test:lockout-duration"],
            },
            {
                "id": "AC3",
                "statement": "Administrators get a CAPTCHA instead of a lockout.",
                "required_evidence": ["test:admin-captcha"],
            },
        ]

    _edit(run_dir, "login-lockout", split)

    case = next(
        c
        for c in score(load_corpus(), [run_dir])["cases"]
        if c["id"] == "login-lockout"
    )

    assert case["result"]["invented"] == []
    assert case["result"]["omitted"] == []
