# TypeScript parser (2026-11-10)

Builds Cross-language Ontology Portability (`15302505`), ONTOLOGY-AC1: the
Reality generator observes `.ts` and `.tsx` files in the same core ontology as
Python.

`ParserFactory` gains the TypeScript entries, which makes its mapping receipt
stale. The identity is unchanged: the class still selects a parser by file
extension. `refresh-batch.json` holds the review digest for the owner's
refresh decision.

Evidence for the acceptance criteria:

- `test:cross-language-ontology-contract` and
  `fixture:mixed-python-typescript-project`: `tests/test_typescript_parser.py`
  and `tests/fixtures/mixed-python-typescript/`.
- `test:mixed-project-guid-traceability`: the same test file.
- `review:ontology-boundary` (ONTOLOGY-AC2) needs the owner.
