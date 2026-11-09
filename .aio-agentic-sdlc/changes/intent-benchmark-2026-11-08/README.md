# Intent translation benchmark, first measurements, 2026-11-08

`dag-tool benchmark-intent` was run against corpus v1 with `claude -p`
(Claude Code 2.1.319) as the translator, on 2026-11-08 in a cloud session.

| Run | Prompt | Result |
| --- | --- | --- |
| `claude-no-schema-run` | Rules only, no field list | Failed: 7 of 8 translations were not valid Intent IR |
| `claude-run-1`, `claude-run-2` | Rules plus the Intent IR field list | Passed every threshold; stability 1.0 |

## What the runs showed

- Without the field list, the model invented its own shape (`title`,
  `intent_ir_version`, `approval.approver`). The benchmark caught it, and the
  translator prompt now carries the exact fields. This matters beyond the
  benchmark: the Intake agent role still writes PRDs, not Intent IR, so the
  first M4 outcome ("Intake turns a stated want into a reviewable Intention
  node") needs the same contract.
- The first scorer counted a requirement split over several criteria as an
  invention (7 false positives in these runs). A criterion now counts as
  grounded when it carries at least half of one expected item, or names a
  component the person named. Forbidden additions are still inventions.

## Weak spots, stated plainly

- A perfect score on the second attempt suggests corpus v1 is too easy to
  separate good translators from adequate ones. Harder cases are worth
  adding: conflicting requirements, implicit dependencies, and requests that
  must be refused or split.
- Keyword matching misses paraphrases that use none of a case's
  alternatives. A miss reads as an omission a person can check; it is never
  hidden in a score.
- Two runs of one model is a small sample for stability.
- The thresholds are a proposal until the owner approves the corpus
  (BENCHMARK-AC1, `review:golden-case-approval`).
