"""Intent translation benchmark (ROADMAP M4, Intention node ``d64fbc3a``).

Measures how faithfully a translator, normally the Intake agent, turns a
stated request into Intent IR. A versioned golden corpus says what each
translation must contain, and a deterministic scorer reports:

- **omissions**: expected requirements, constraints, ambiguities and
  evidence the translation lacks;
- **inventions**: acceptance criteria that restate none of what the person
  asked for, or that add something the corpus forbids;
- **dependency errors**: relationships to existing components that are
  missing or made up;
- **unjustified completions**: translations that approve themselves or mark
  a real ambiguity resolved without the person resolving it;
- **stability**: whether repeated runs find the same items;
- **correction quality**: whether feedback is taken in.

Matching is keyword based and deterministic, so no model judges a model.
That is crude on purpose: a miss shows up as an omission a person can read,
never as a hidden score. A translation is an Intent IR payload with an
optional ``dependencies`` list of ``{"target": name, "type": edge type}``.
"""

from __future__ import annotations

import importlib.resources
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Sequence

import yaml

from .intent_ir import IntentIR

CORPUS_PACKAGE = ("benchmarks", "intent_translation", "v1")
CATEGORIES = ("requirements", "constraints", "ambiguities", "evidence")

TRANSLATOR_INSTRUCTIONS = """You translate one stated software request into \
Intent IR v1 for human review. Reply with one JSON object and nothing else.

Rules:
- Put every requirement and constraint the person stated in \
acceptance_criteria, each with required_evidence such as "test:<slug>".
- Do not add requirements the person did not state.
- Record every question the request leaves open in ambiguities with status \
"open". Never resolve an ambiguity yourself.
- approval.state is "review_required". Never approve.
- If the request names existing components, list them in a top-level \
"dependencies" array of {"target": "<component name>", "type": \
"depends_on" or "subscribes"}.
- provenance is one human_statement quoting the request.
- Use exactly these top-level fields and no others:

{
  "schema_version": 1,
  "provenance": [{"source_type": "human_statement",
                  "reference": "request", "statement": "<the request>"}],
  "assumptions": ["<anything you assumed that the person did not say>"],
  "ambiguities": [{"question": "<open question>", "status": "open"}],
  "confidence": 0.7,
  "acceptance_criteria": [{"id": "AC1", "statement": "<one testable criterion>",
                           "required_evidence": ["test:<slug>"]}],
  "revision_history": [{"revision": 1, "recorded_at": "2026-01-01T00:00:00Z",
                        "actor": "sdlc_intake", "generator_version": "intake",
                        "summary": "Translated the request."}],
  "responsible_agent": "sdlc_intake",
  "generator_version": "intake",
  "approval": {"state": "review_required"},
  "dependencies": [{"target": "<existing component>", "type": "depends_on"}]
}
"""


class BenchmarkError(ValueError):
    """The corpus or a translation cannot be used."""


def default_corpus_path() -> Path:
    """The corpus shipped with the package."""

    root = importlib.resources.files("aio_agentic_sdlc").joinpath(*CORPUS_PACKAGE)
    return Path(str(root))


def load_corpus(path: str | Path | None = None) -> dict[str, Any]:
    directory = Path(path) if path else default_corpus_path()
    file = directory / "corpus.yaml" if directory.is_dir() else directory
    try:
        corpus = yaml.safe_load(file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise BenchmarkError(f"cannot read the corpus at {file}: {error}") from error
    if not isinstance(corpus, dict) or not corpus.get("cases"):
        raise BenchmarkError("the corpus has no cases")
    ids = [case["id"] for case in corpus["cases"]]
    if len(ids) != len(set(ids)):
        raise BenchmarkError("case ids must be unique")
    return corpus


def _matches(spec: Sequence[Sequence[str]], text: str) -> bool:
    """Every group needs one alternative, matched as a word prefix."""

    lowered = text.casefold()
    for group in spec:
        found = False
        for alternative in group:
            needle = str(alternative).casefold()
            prefix = r"(?<!\w)" if needle[:1].isalnum() else ""
            if re.search(prefix + re.escape(needle), lowered):
                found = True
                break
        if not found:
            return False
    return True


def _grounded(
    criterion: str, claimed: Sequence[dict[str, Any]], targets: Sequence[str]
) -> bool:
    """A criterion is grounded when it restates part of what was asked.

    Splitting one requirement over several criteria is faithful, so a
    criterion needs at least half the groups of one expected requirement or
    constraint, or to name a component the person named. Anything else is an
    invention.
    """

    lowered = criterion.casefold()
    if any(target and target in " ".join(lowered.split()) for target in targets):
        return True
    for item in claimed:
        groups = item["match"]
        hits = sum(1 for group in groups if _matches([group], criterion))
        if groups and hits * 2 >= len(groups):
            return True
    return False


def _texts(translation: dict[str, Any]) -> dict[str, Any]:
    criteria = [c.get("statement", "") for c in translation["acceptance_criteria"]]
    evidence = " ".join(
        ref
        for criterion in translation["acceptance_criteria"]
        for ref in criterion.get("required_evidence", [])
    )
    open_questions = " ".join(
        a.get("question", "")
        for a in translation.get("ambiguities", [])
        if a.get("status", "open") == "open"
    )
    resolved_questions = " ".join(
        a.get("question", "")
        for a in translation.get("ambiguities", [])
        if a.get("status") == "resolved"
    )
    return {
        "criteria": criteria,
        "requirements": " \n ".join(criteria),
        "constraints": " \n ".join(criteria),
        "ambiguities": open_questions,
        "resolved": resolved_questions,
        "evidence": evidence,
    }


def _normalize_dependency(dependency: Any) -> tuple[str, str]:
    if not isinstance(dependency, dict):
        raise BenchmarkError("each dependency is an object with target and type")
    target = " ".join(str(dependency.get("target", "")).casefold().split())
    return target, str(dependency.get("type", "depends_on")).casefold()


def validate_translation(translation: Any) -> dict[str, Any]:
    """A translation must be valid Intent IR, plus optional dependencies."""

    if not isinstance(translation, dict):
        raise BenchmarkError("a translation is a JSON object")
    payload = {k: v for k, v in translation.items() if k != "dependencies"}
    try:
        IntentIR.model_validate(payload)
    except ValueError as error:
        raise BenchmarkError(f"not valid Intent IR: {error}") from error
    for dependency in translation.get("dependencies", []) or []:
        _normalize_dependency(dependency)
    return translation


def score_case(
    expected: dict[str, Any],
    translation: dict[str, Any],
    *,
    after_feedback: bool = False,
) -> dict[str, Any]:
    """Score one translation against one expectation."""

    validate_translation(translation)
    texts = _texts(translation)
    found: list[str] = []
    omitted: list[str] = []
    total = 0
    for category in CATEGORIES:
        for item in expected.get(category, []) or []:
            total += 1
            key = f"{category}:{item['id']}"
            if _matches(item["match"], texts[category]):
                found.append(key)
            else:
                omitted.append(key)

    claimed = [
        *(expected.get("requirements") or []),
        *(expected.get("constraints") or []),
    ]
    targets = [
        _normalize_dependency(d)[0] for d in expected.get("dependencies", []) or []
    ]
    invented = [
        criterion
        for criterion in texts["criteria"]
        if not _grounded(criterion, claimed, targets)
    ]
    forbidden = [
        criterion
        for criterion in texts["criteria"]
        for spec in expected.get("forbidden", []) or []
        if _matches(spec, criterion)
    ]
    for criterion in forbidden:
        if criterion not in invented:
            invented.append(criterion)

    expected_deps = {
        _normalize_dependency(d) for d in expected.get("dependencies", []) or []
    }
    actual_deps = {
        _normalize_dependency(d) for d in translation.get("dependencies", []) or []
    }
    dependency_errors = sorted(
        [f"missing {t} ({k})" for t, k in expected_deps - actual_deps]
        + [f"invented {t} ({k})" for t, k in actual_deps - expected_deps]
    )

    unjustified = []
    if translation["approval"]["state"] == "approved":
        unjustified.append("the translation approved itself")
    if not after_feedback:
        for item in expected.get("ambiguities", []) or []:
            if _matches(item["match"], texts["resolved"]):
                unjustified.append(
                    f"ambiguity {item['id']} was marked resolved without feedback"
                )

    result = {
        "expected_items": total,
        "found": found,
        "omitted": omitted,
        "criteria": len(texts["criteria"]),
        "invented": invented,
        "dependency_errors": dependency_errors,
        "unjustified_completions": unjustified,
    }
    if after_feedback:
        targets = expected.get("feedback_items", []) or []
        fixed = [
            item_id
            for item_id in targets
            if any(key.endswith(f":{item_id}") for key in found)
        ]
        result["feedback_items"] = len(targets)
        result["feedback_fixed"] = fixed
    return result


def _read_translation(directory: Path, name: str) -> dict[str, Any] | None:
    path = directory / f"{name}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BenchmarkError(f"{path} is not valid JSON: {error}") from error


def score(corpus: dict[str, Any], runs: Sequence[str | Path]) -> dict[str, Any]:
    """Score one or more runs of translations against the corpus.

    The first run gives every metric except stability; stability needs at
    least two runs and compares the items each run found per case.
    """

    if not runs:
        raise BenchmarkError("at least one run of translations is required")
    directories = [Path(run) for run in runs]
    cases = []
    totals = {
        "expected_items": 0,
        "omitted": 0,
        "criteria": 0,
        "invented": 0,
        "dependency_errors": 0,
        "unjustified_completions": 0,
        "feedback_items": 0,
        "feedback_fixed": 0,
        "stable_cases": 0,
        "missing_translations": 0,
        "invalid_translations": 0,
    }
    for case in corpus["cases"]:
        entry: dict[str, Any] = {"id": case["id"]}
        translation = _read_translation(directories[0], case["id"])
        if translation is None:
            # A missing translation omits everything the case expects.
            expected_total = sum(
                len(case["expected"].get(c, []) or []) for c in CATEGORIES
            )
            entry["missing"] = True
            totals["missing_translations"] += 1
            totals["expected_items"] += expected_total
            totals["omitted"] += expected_total
            totals["dependency_errors"] += len(
                case["expected"].get("dependencies", []) or []
            )
            totals["feedback_items"] += len(
                (case.get("expected_after_feedback") or {}).get("feedback_items", [])
            )
            cases.append(entry)
            continue
        try:
            result = score_case(case["expected"], translation)
        except BenchmarkError as error:
            translation = None
            invalid = str(error).splitlines()[0]
        if translation is None:
            expected_total = sum(
                len(case["expected"].get(c, []) or []) for c in CATEGORIES
            )
            entry["invalid"] = invalid
            totals["invalid_translations"] += 1
            totals["expected_items"] += expected_total
            totals["omitted"] += expected_total
            totals["dependency_errors"] += len(
                case["expected"].get("dependencies", []) or []
            )
            totals["feedback_items"] += len(
                (case.get("expected_after_feedback") or {}).get("feedback_items", [])
            )
            cases.append(entry)
            continue
        entry["result"] = result
        totals["expected_items"] += result["expected_items"]
        totals["omitted"] += len(result["omitted"])
        totals["criteria"] += result["criteria"]
        totals["invented"] += len(result["invented"])
        totals["dependency_errors"] += len(result["dependency_errors"])
        totals["unjustified_completions"] += len(result["unjustified_completions"])

        if case.get("feedback"):
            expected_after = case["expected_after_feedback"]
            totals["feedback_items"] += len(expected_after.get("feedback_items", []))
            after = _read_translation(directories[0], f"{case['id']}.after")
            try:
                after_result = (
                    score_case(expected_after, after, after_feedback=True)
                    if after is not None
                    else None
                )
            except BenchmarkError as error:
                after_result = None
                entry["after_feedback_invalid"] = str(error).splitlines()[0]
            if after_result is not None:
                entry["after_feedback"] = after_result
                totals["feedback_fixed"] += len(after_result["feedback_fixed"])
                totals["unjustified_completions"] += len(
                    after_result["unjustified_completions"]
                )

        if len(directories) > 1:
            found_sets = [frozenset(result["found"])]
            for directory in directories[1:]:
                other = _read_translation(directory, case["id"])
                try:
                    found_sets.append(
                        frozenset(score_case(case["expected"], other)["found"])
                        if other is not None
                        else frozenset({"<missing>"})
                    )
                except BenchmarkError:
                    found_sets.append(frozenset({"<invalid>"}))
            entry["stable"] = len(set(found_sets)) == 1
            totals["stable_cases"] += int(entry["stable"])
        cases.append(entry)

    case_count = len(corpus["cases"])
    metrics = {
        "omission_rate": _rate(totals["omitted"], totals["expected_items"]),
        "invention_rate": _rate(totals["invented"], totals["criteria"]),
        "dependency_errors": totals["dependency_errors"],
        "unjustified_completions": totals["unjustified_completions"],
        "stability": (
            _rate(totals["stable_cases"], case_count) if len(directories) > 1 else None
        ),
        "correction_quality": (
            _rate(totals["feedback_fixed"], totals["feedback_items"])
            if totals["feedback_items"]
            else None
        ),
    }
    thresholds = corpus.get("thresholds", {})
    checks = _check(metrics, thresholds)
    return {
        "schema_version": 1,
        "corpus": corpus.get("corpus"),
        "corpus_version": corpus.get("version"),
        "runs": len(directories),
        "metrics": metrics,
        "thresholds": thresholds,
        "checks": checks,
        "passed": all(c["passed"] for c in checks if c["passed"] is not None),
        "totals": totals,
        "cases": cases,
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def _check(metrics: dict[str, Any], thresholds: dict[str, Any]) -> list[dict]:
    rules = [
        ("omission_rate", "omission_rate_max", "max"),
        ("invention_rate", "invention_rate_max", "max"),
        ("dependency_errors", "dependency_errors_max", "max"),
        ("unjustified_completions", "unjustified_completions_max", "max"),
        ("stability", "stability_min", "min"),
        ("correction_quality", "correction_quality_min", "min"),
    ]
    checks = []
    for metric, key, kind in rules:
        if key not in thresholds:
            continue
        value = metrics[metric]
        limit = thresholds[key]
        if value is None:
            passed = None
        elif kind == "max":
            passed = value <= limit
        else:
            passed = value >= limit
        checks.append(
            {
                "metric": metric,
                "value": value,
                "kind": kind,
                "limit": limit,
                "passed": passed,
            }
        )
    return checks


def render_report(report: dict[str, Any]) -> str:
    lines = [
        f"Intent translation benchmark: {report['corpus']} v{report['corpus_version']}, "
        f"{report['runs']} run(s), {len(report['cases'])} cases",
        "",
    ]
    for check in report["checks"]:
        if check["passed"] is None:
            status = "not measured"
        else:
            status = "pass" if check["passed"] else "FAIL"
        bound = "at most" if check["kind"] == "max" else "at least"
        value = "n/a" if check["value"] is None else check["value"]
        lines.append(
            f"  {status:12} {check['metric']}: {value} ({bound} {check['limit']})"
        )
    lines.append("")
    for case in report["cases"]:
        if case.get("missing"):
            lines.append(f"- {case['id']}: no translation")
            continue
        if case.get("invalid"):
            lines.append(f"- {case['id']}: invalid translation ({case['invalid']})")
            continue
        result = case["result"]
        problems = (
            [f"omitted {key}" for key in result["omitted"]]
            + [f'invented "{text}"' for text in result["invented"]]
            + result["dependency_errors"]
            + result["unjustified_completions"]
        )
        after = case.get("after_feedback")
        if after is not None:
            missed = sorted(set(case_item for case_item in after.get("omitted", [])))
            problems += [f"after feedback, omitted {key}" for key in missed]
        if case.get("stable") is False:
            problems.append("runs disagree")
        lines.append(f"- {case['id']}: " + ("; ".join(problems) or "ok"))
    lines.append("")
    lines.append("PASSED" if report["passed"] else "FAILED")
    return "\n".join(lines) + "\n"


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise BenchmarkError("the translator's reply has no JSON object")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise BenchmarkError(f"the translator's reply is not JSON: {error}") from error


def _ask(command: Sequence[str], prompt: str, timeout: int) -> str:
    try:
        result = subprocess.run(
            list(command),
            input=prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise BenchmarkError(f"the translator failed: {error}") from error
    if result.returncode != 0:
        raise BenchmarkError(
            f"the translator exited with {result.returncode}: {result.stderr[-500:]}"
        )
    return result.stdout


def run_translator(
    corpus: dict[str, Any],
    command: Sequence[str],
    output: str | Path,
    *,
    timeout: int = 300,
) -> list[str]:
    """Translate every case with an agent CLI and write one run directory.

    The prompt goes to the command's stdin, like the ``command`` runtime;
    its stdout must contain the JSON translation. A case the translator
    fails on is written as nothing, which the scorer counts as omissions.
    """

    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    failures = []
    for case in corpus["cases"]:
        prompt = f"{TRANSLATOR_INSTRUCTIONS}\nRequest: {case['request']}\n"
        try:
            first = _extract_json(_ask(command, prompt, timeout))
            (directory / f"{case['id']}.json").write_text(
                json.dumps(first, indent=2) + "\n", encoding="utf-8"
            )
            if case.get("feedback"):
                revision = (
                    f"{TRANSLATOR_INSTRUCTIONS}\nRequest: {case['request']}\n\n"
                    f"Your previous translation:\n{json.dumps(first, indent=2)}\n\n"
                    f"The person's feedback: {case['feedback']}\n"
                    "Revise the translation. Ambiguities the feedback answers "
                    "may now be marked resolved with its answer as resolution.\n"
                )
                after = _extract_json(_ask(command, revision, timeout))
                (directory / f"{case['id']}.after.json").write_text(
                    json.dumps(after, indent=2) + "\n", encoding="utf-8"
                )
        except BenchmarkError as error:
            failures.append(f"{case['id']}: {error}")
    return failures
