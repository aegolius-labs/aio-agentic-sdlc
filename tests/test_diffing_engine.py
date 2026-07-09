import pytest

from agentic_backlog.dag_models import Metadata, Node, Edge, NodeType, EdgeType
from agentic_backlog.dag_manager import DAGManager
from agentic_backlog.diffing_engine import DiffingEngine

def create_sample_dag(name="Sample", nodes=None, edges=None):
    if nodes is None:
        nodes = []
    if edges is None:
        edges = []
    meta = Metadata(name=name, version="1.0")
    return DAGManager(meta, nodes, edges)

def test_missing_node():
    node_intent = Node(id="app-service", type=NodeType.CONTAINER, name="App Service")
    intent = create_sample_dag(nodes=[node_intent])
    reality = create_sample_dag()
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    task_name = "Create Container 'App Service'"
    assert task_name in nodes
    assert nodes[task_name]["item_type"] == "Task"
    assert "Missing node in Reality DAG." in nodes[task_name]["description"]

def test_extraneous_node():
    node_real = Node(id="old-service", type=NodeType.CONTAINER, name="Old Service")
    intent = create_sample_dag()
    reality = create_sample_dag(nodes=[node_real])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    task_name = "Remove Container 'Old Service'"
    assert task_name in nodes
    assert nodes[task_name]["category"] == "Cleanup"
    assert "exists in Reality but not in Intention" in nodes[task_name]["description"]

def test_drift_node():
    node_intent = Node(id="db", type=NodeType.CONTAINER, name="DB", domain="users", attributes={"version": "14"})
    node_real = Node(id="db", type=NodeType.CONTAINER, name="DB", domain="legacy", attributes={"version": "12"})
    
    intent = create_sample_dag(nodes=[node_intent])
    reality = create_sample_dag(nodes=[node_real])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    task_name = "Update Container 'DB'"
    assert task_name in nodes
    desc = nodes[task_name]["description"]
    assert "Domain drift: intention 'users', reality 'legacy'" in desc
    assert "Attribute 'version' drift: intention '14', reality '12'" in desc

def test_missing_edge():
    n1 = Node(id="ui", type=NodeType.CONTAINER, name="UI")
    n2 = Node(id="api", type=NodeType.CONTAINER, name="API")
    edge = Edge(source="ui", target="api", type=EdgeType.CALLS)
    
    intent = create_sample_dag(nodes=[n1, n2], edges=[edge])
    reality = create_sample_dag(nodes=[n1, n2], edges=[])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    edges = diff["edges"]
    task_name = "Connect 'ui' to 'api' (calls)"
    
    assert task_name in nodes
    assert nodes[task_name]["item_type"] == "Task"
    
    # Requires should be empty since nodes exist in reality
    assert len(edges) == 0

def test_missing_edge_with_missing_nodes():
    n1 = Node(id="ui", type=NodeType.CONTAINER, name="UI")
    n2 = Node(id="api", type=NodeType.CONTAINER, name="API")
    edge = Edge(source="ui", target="api", type=EdgeType.CALLS)
    
    intent = create_sample_dag(nodes=[n1, n2], edges=[edge])
    reality = create_sample_dag() # empty reality
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    backlog_edges = diff["edges"]
    
    task_edge = "Connect 'ui' to 'api' (calls)"
    assert task_edge in nodes
    
    # We should have dependencies on node creation
    task_create_ui = "Create Container 'UI'"
    task_create_api = "Create Container 'API'"
    assert task_create_ui in nodes
    assert task_create_api in nodes
    
    deps = [e["to"] for e in backlog_edges if e["from"] == task_edge]
    assert task_create_ui in deps
    assert task_create_api in deps

def test_extraneous_edge():
    n1 = Node(id="ui", type=NodeType.CONTAINER, name="UI")
    n2 = Node(id="api", type=NodeType.CONTAINER, name="API")
    edge = Edge(source="ui", target="api", type=EdgeType.CALLS)
    
    intent = create_sample_dag(nodes=[n1, n2], edges=[])
    reality = create_sample_dag(nodes=[n1, n2], edges=[edge])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    task_name = "Disconnect 'ui' from 'api' (calls)"
    assert task_name in nodes


# Implicit Roll-up Tests

def test_unmapped_node_with_no_parents():
    node_a = Node(id="a", type=NodeType.CONTAINER, name="A")
    node_b = Node(id="b", type=NodeType.CONTAINER, name="B")
    
    intent = create_sample_dag(nodes=[node_a])
    reality = create_sample_dag(nodes=[node_a, node_b])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    assert "Remove Container 'B'" in nodes

def test_unmapped_node_with_unmapped_parent():
    node_a = Node(id="a", type=NodeType.CONTAINER, name="A")
    node_b = Node(id="b", type=NodeType.CONTAINER, name="B")
    node_c = Node(id="c", type=NodeType.CONTAINER, name="C")
    edge = Edge(source="b", target="c", type=EdgeType.CONTAINS)
    
    intent = create_sample_dag(nodes=[node_a])
    reality = create_sample_dag(nodes=[node_b, node_c], edges=[edge])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    assert "Remove Container 'B'" in nodes
    assert "Remove Container 'C'" in nodes

def test_unmapped_node_with_mapped_parent():
    node_a = Node(id="a", type=NodeType.CONTAINER, name="A")
    node_b = Node(id="b", type=NodeType.CONTAINER, name="B")
    edge = Edge(source="a", target="b", type=EdgeType.CONTAINS)
    
    intent = create_sample_dag(nodes=[node_a])
    reality = create_sample_dag(nodes=[node_a, node_b], edges=[edge])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    assert "Remove Container 'B'" not in nodes

def test_unmapped_node_with_mapped_grandparent():
    node_a = Node(id="a", type=NodeType.CONTAINER, name="A")
    node_b = Node(id="b", type=NodeType.CONTAINER, name="B")
    node_c = Node(id="c", type=NodeType.CONTAINER, name="C")
    edge1 = Edge(source="a", target="b", type=EdgeType.CONTAINS)
    edge2 = Edge(source="b", target="c", type=EdgeType.CONTAINS)
    
    intent = create_sample_dag(nodes=[node_a])
    reality = create_sample_dag(nodes=[node_a, node_b, node_c], edges=[edge1, edge2])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    assert "Remove Container 'B'" not in nodes
    assert "Remove Container 'C'" not in nodes

def test_circular_dependency_resiliency():
    node_b = Node(id="b", type=NodeType.CONTAINER, name="B")
    node_c = Node(id="c", type=NodeType.CONTAINER, name="C")
    node_d = Node(id="d", type=NodeType.CONTAINER, name="D")
    
    edge1 = Edge(source="b", target="c", type=EdgeType.CONTAINS)
    edge2 = Edge(source="c", target="d", type=EdgeType.CONTAINS)
    edge3 = Edge(source="d", target="b", type=EdgeType.CONTAINS)
    
    intent = create_sample_dag(nodes=[])
    reality = create_sample_dag(nodes=[node_b, node_c, node_d], edges=[edge1, edge2, edge3])
    
    engine = DiffingEngine(intent, reality)
    diff = engine.calculate_diff()
    
    nodes = diff["nodes"]
    assert "Remove Container 'B'" in nodes
    assert "Remove Container 'C'" in nodes
    assert "Remove Container 'D'" in nodes
