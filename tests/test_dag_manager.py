import pytest
from agentic_backlog.dag_models import Node, Edge, NodeType, EdgeType, Metadata
from agentic_backlog.dag_manager import DAGManager

def test_dag_manager_initialization():
    metadata = Metadata(name="Test DAG", version="1.0.0")
    node = Node(id="n1", type=NodeType.SYSTEM, name="System 1")
    edge = Edge(source="n1", target="n1", type=EdgeType.CALLS)
    
    manager = DAGManager(metadata, [node], [edge])
    assert manager.metadata.name == "Test DAG"
    assert "n1" in manager.nodes
    assert len(manager.edges) == 1

def test_dag_manager_add_node():
    manager = DAGManager(Metadata(name="Test", version="1.0"), [], [])
    node = Node(id="n1", type=NodeType.SYSTEM, name="Sys1")
    manager.add_node(node)
    
    assert "n1" in manager.nodes
    
    with pytest.raises(ValueError, match="already exists"):
        manager.add_node(node)

def test_dag_manager_remove_node():
    node1 = Node(id="n1", type=NodeType.SYSTEM, name="Sys1")
    node2 = Node(id="n2", type=NodeType.SYSTEM, name="Sys2")
    edge = Edge(source="n1", target="n2", type=EdgeType.CALLS)
    manager = DAGManager(Metadata(name="Test", version="1.0"), [node1, node2], [edge])
    
    manager.remove_node("n1")
    assert "n1" not in manager.nodes
    assert len(manager.edges) == 0

def test_dag_manager_update_node():
    node1 = Node(id="n1", type=NodeType.SYSTEM, name="Sys1")
    manager = DAGManager(Metadata(name="Test", version="1.0"), [node1], [])
    manager.update_node("n1", name="Updated Sys1", domain="test")
    
    n = manager.get_node("n1")
    assert n.name == "Updated Sys1"
    assert n.domain == "test"

def test_dag_manager_add_edge():
    node1 = Node(id="n1", type=NodeType.SYSTEM, name="Sys1")
    node2 = Node(id="n2", type=NodeType.SYSTEM, name="Sys2")
    manager = DAGManager(Metadata(name="Test", version="1.0"), [node1, node2], [])
    
    edge = Edge(source="n1", target="n2", type=EdgeType.CALLS)
    manager.add_edge(edge)
    assert len(manager.edges) == 1
    
    with pytest.raises(ValueError, match="Source node not_exist does not exist"):
        manager.add_edge(Edge(source="not_exist", target="n2", type=EdgeType.CALLS))

def test_dag_manager_remove_edge():
    node1 = Node(id="n1", type=NodeType.SYSTEM, name="Sys1")
    node2 = Node(id="n2", type=NodeType.SYSTEM, name="Sys2")
    edge = Edge(source="n1", target="n2", type=EdgeType.CALLS)
    manager = DAGManager(Metadata(name="Test", version="1.0"), [node1, node2], [edge])
    
    manager.remove_edge("n1", "n2", EdgeType.CALLS)
    assert len(manager.edges) == 0

def test_cycle_detection():
    node1 = Node(id="n1", type=NodeType.SYSTEM, name="Sys1")
    node2 = Node(id="n2", type=NodeType.SYSTEM, name="Sys2")
    node3 = Node(id="n3", type=NodeType.SYSTEM, name="Sys3")
    
    # n1 -> n2 -> n3
    edge1 = Edge(source="n1", target="n2", type=EdgeType.DEPENDS_ON)
    edge2 = Edge(source="n2", target="n3", type=EdgeType.DEPENDS_ON)
    
    manager = DAGManager(Metadata(name="Test", version="1.0"), [node1, node2, node3], [edge1, edge2])
    manager.validate() # Should not raise
    
    # n3 -> n1 (cycle)
    edge3 = Edge(source="n3", target="n1", type=EdgeType.DEPENDS_ON)
    manager.add_edge(edge3)
    
    with pytest.raises(ValueError, match="Cycle detected"):
        manager.validate()

def test_find_nodes():
    node1 = Node(id="n1", type=NodeType.SYSTEM, name="Sys1", domain="core")
    node2 = Node(id="n2", type=NodeType.CONTAINER, name="Cont1", domain="core")
    node3 = Node(id="n3", type=NodeType.SYSTEM, name="Sys2", domain="other")
    manager = DAGManager(Metadata(name="Test", version="1.0"), [node1, node2, node3], [])
    
    res = manager.find_nodes(domain="core")
    assert len(res) == 2
    
    res = manager.find_nodes(type=NodeType.SYSTEM)
    assert len(res) == 2
    
    res = manager.find_nodes(type=NodeType.SYSTEM, domain="core")
    assert len(res) == 1
    assert res[0].id == "n1"
