# Map the new code (2026-11-11)

`mapping-batch.json` holds the mapping review digests for two nodes whose
code merged in #169 and #170. They wait on the owner's decision:

- Canonical GUID Extractor (`2e8a1562`) to `scan_project`.
- Cross-language Ontology Portability (`15302505`) to `TypeScriptParser`.

A digest goes stale on any DAG or source change, so run `dag-tool mapping
review` again before approving.
