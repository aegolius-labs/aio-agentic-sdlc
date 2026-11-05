# Explicit Evidence Model

Implements Intention node Explicit Evidence Model (`6b1b3459`) as decided in
[ADR 0003](../../../doc/adr/0003-explicit-evidence-model.md).

- The node is mapped to `EvidenceEvaluator` in `src/aio_agentic_sdlc/evidence.py`.
- `.aio-agentic-sdlc/evidence.json` records its four required references:
  two tests, the schema, and this directory's `report.json` as the demo run.
- `report.json` is `dag-tool reconcile --evidence` on this repository. Seven
  of 62 nodes are complete, 55 are incomplete and 82 criteria are unverified.
  Six of the complete nodes are legacy nodes whose only required reference is
  their own mapping. Sharper criteria for them are ROADMAP M1 work.
- `decisions.json` carries the five still-unbuilt group B classifications
  forward to the regenerated Reality DAG's plan digest. The Explicit Evidence
  Model no longer needs one because it is now confirmed.
