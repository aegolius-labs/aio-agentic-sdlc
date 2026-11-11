"""TypeScript is observed in the same ontology as Python (ONTOLOGY-AC1/AC2).

Evidence for Cross-language Ontology Portability:
`test:cross-language-ontology-contract`, `fixture:mixed-python-typescript-project`
(tests/fixtures/mixed-python-typescript) and
`test:mixed-project-guid-traceability`.
"""

import shutil
from pathlib import Path

import pytest

from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Metadata, Node, NodeType
from aio_agentic_sdlc.guid_extractor import scan_project
from aio_agentic_sdlc.reality_dag_generator import RealityDAGGenerator
from aio_agentic_sdlc.reconciliation import ReconciliationEngine, normalize_node_name

FIXTURE = Path(__file__).parent / "fixtures" / "mixed-python-typescript"
PY_GUID = "11111111-1111-4111-8111-111111111111"
TS_GUID = "22222222-2222-4222-8222-222222222222"
# The one concept each language spells its own way.
EQUIVALENT_NAMES = {"__init__": "constructor"}


def _generate(root):
    generator = RealityDAGGenerator(str(root), "Shop")
    return generator, generator.generate()


def _nodes(manager):
    nodes = manager.nodes
    return nodes if isinstance(nodes, dict) else {node.id: node for node in nodes}


def _projection(root):
    """Return the language-neutral shape of one observed project."""

    generator, manager = _generate(root)
    nodes = _nodes(manager)

    def label(node_id):
        node = nodes[node_id]
        name = node.name
        if node.type == NodeType.MODULE:
            name = name.rsplit(".", 1)[0]
        name = EQUIVALENT_NAMES.get(name, name)
        kinds = {loc.symbol_kind for loc in generator.source_locations.get(node_id, [])}
        return (node.type.value, normalize_node_name(name), tuple(sorted(kinds)))

    shape_nodes = sorted(label(node_id) for node_id in nodes)
    shape_edges = sorted(
        (label(edge.source), edge.type.value, label(edge.target))
        for edge in manager.edges
    )
    return shape_nodes, shape_edges, nodes


def test_cross_language_ontology_contract():
    py_nodes, py_edges, _ = _projection(FIXTURE / "py")
    ts_nodes, ts_edges, _ = _projection(FIXTURE / "ts")

    assert ts_nodes == py_nodes
    assert ts_edges == py_edges
    assert ("entity", "order", ("class",)) in ts_nodes
    assert any(edge[1] == "depends_on" for edge in ts_edges)


def test_typescript_only_concepts_do_not_reach_the_core_schema():
    _, manager = _generate(FIXTURE / "ts")
    names = {node.name for node in _nodes(manager).values()}

    for absent in (
        "PriceRule",
        "Currency",
        "Rounding",
        "rounding",
        "rate",
        "testCreateOrder",
        "legacyPrice",
        "globals.d.ts",
        "orders.test.ts",
    ):
        assert absent not in names
    assert {node.type for node in _nodes(manager).values()} <= {
        NodeType.SYSTEM,
        NodeType.MODULE,
        NodeType.COMPONENT,
        NodeType.ENTITY,
    }


def test_mixed_project_guid_traceability(tmp_path):
    shutil.copytree(FIXTURE / "py", tmp_path / "py")
    shutil.copytree(FIXTURE / "ts", tmp_path / "ts")
    generator, reality = _generate(tmp_path)
    nodes = _nodes(reality)

    assert nodes[PY_GUID].name == "PriceCalculator"
    assert nodes[TS_GUID].name == "PriceCalculator"
    paths = {
        guid: [loc.path for loc in generator.source_locations[guid]]
        for guid in (PY_GUID, TS_GUID)
    }
    assert paths == {
        PY_GUID: ["py/shop/pricing.py"],
        TS_GUID: ["ts/shop/pricing.ts"],
    }
    ts_location = generator.source_locations[TS_GUID][0]
    assert (ts_location.marker_line, ts_location.definition_line) == (2, 3)

    intention = DAGManager(
        Metadata(name="Shop", version="1.0"),
        [
            Node(id=PY_GUID, type=NodeType.COMPONENT, name="Python pricing"),
            Node(id=TS_GUID, type=NodeType.COMPONENT, name="TypeScript pricing"),
        ],
        [],
    )
    report = ReconciliationEngine(intention, reality).analyze(max_items=100)
    classification = {
        item["intent"]["id"]: item["classification"]
        for item in report["items"]
        if item["subject_kind"] == "intent"
    }
    assert classification == {PY_GUID: "confirmed", TS_GUID: "confirmed"}

    extracted = scan_project(tmp_path)
    assert sorted((m["guid"], m["path"]) for m in extracted["markers"]) == [
        (PY_GUID, "py/shop/pricing.py"),
        (TS_GUID, "ts/shop/pricing.ts"),
    ]


def test_one_guid_claimed_in_both_languages_is_refused(tmp_path):
    (tmp_path / "a.py").write_text(f"# aio-sdlc-node: {PY_GUID}\nclass A:\n    pass\n")
    (tmp_path / "b.ts").write_text(
        f"// aio-sdlc-node: {PY_GUID}\nexport class B {{}}\n"
    )

    with pytest.raises(ValueError, match="collides with existing identity"):
        _generate(tmp_path)
    assert list(scan_project(tmp_path)["duplicates"]) == [PY_GUID]


def test_markers_name_modules_methods_and_decorated_definitions(tmp_path):
    method = "33333333-3333-4333-8333-333333333333"
    decorated = "44444444-4444-4444-8444-444444444444"
    (tmp_path / "service.tsx").write_text(
        f"// aio-sdlc-node: {TS_GUID}\n"
        "\n"
        "import React from 'react';\n"
        f"// aio-sdlc-node: {decorated}\n"
        "@Injectable()\n"
        "export class Service {\n"
        f"  // aio-sdlc-node: {method}\n"
        "  @Get()\n"
        "  list() { return <div />; }\n"
        "  #hidden() {}\n"
        "}\n"
    )
    generator, manager = _generate(tmp_path)
    nodes = _nodes(manager)

    assert nodes[TS_GUID].type == NodeType.MODULE
    assert nodes[decorated].name == "Service"
    assert nodes[method].name == "list"
    assert nodes[method].type == NodeType.COMPONENT
    assert generator.source_locations[method][0].marker_line == 7


def test_a_marker_in_a_string_is_not_identity(tmp_path):
    (tmp_path / "a.ts").write_text(
        f'const note = "// aio-sdlc-node: {TS_GUID}";\nexport function run() {{}}\n'
    )
    _, manager = _generate(tmp_path)

    assert TS_GUID not in _nodes(manager)
    assert scan_project(tmp_path)["markers"] == []


def test_relative_imports_resolve_to_index_files(tmp_path):
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "index.ts").write_text("export function lib() {}\n")
    (tmp_path / "main.ts").write_text(
        'import { lib } from "./lib";\nimport x from "./missing";\n'
        'export { lib as again } from "./lib/index.js";\n'
    )
    _, manager = _generate(tmp_path)
    nodes = _nodes(manager)
    edges = {
        (nodes[e.source].name, nodes[e.target].name)
        for e in manager.edges
        if e.type.value == "depends_on"
    }

    assert edges == {("main.ts", "index.ts")}
