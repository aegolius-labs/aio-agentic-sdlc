import os
import tempfile
import pytest

from aio_agentic_sdlc.reality_dag_generator import RealityDAGGenerator
from aio_agentic_sdlc.dag_models import NodeType, EdgeType

def test_reality_generator_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a sample python file
        file_content = """
import os
from datetime import datetime

class UserModel(BaseModel):
    pass

class UserService:
    def __init__(self):
        pass
        
    def get_user(self):
        pass

@app.get('/users')
def list_users():
    pass
"""
        with open(os.path.join(tmpdir, "main.py"), "w", encoding="utf-8") as f:
            f.write(file_content)
            
        generator = RealityDAGGenerator(root_dir=tmpdir, system_name="TestSystem")
        dag = generator.generate()
        
        # Verify nodes
        node_ids = {n.id: n for n in dag.nodes.values()}
        
        assert generator._id_to_uuid("system_root") in node_ids
        assert node_ids[generator._id_to_uuid("system_root")].type == NodeType.SYSTEM
        
        assert generator._id_to_uuid("main") in node_ids
        assert node_ids[generator._id_to_uuid("main")].type == NodeType.MODULE
        
        assert generator._id_to_uuid("main.UserModel") in node_ids
        assert node_ids[generator._id_to_uuid("main.UserModel")].type == NodeType.ENTITY
        
        assert generator._id_to_uuid("main.UserService") in node_ids
        assert node_ids[generator._id_to_uuid("main.UserService")].type == NodeType.COMPONENT
        
        assert generator._id_to_uuid("main.UserService.get_user") in node_ids
        assert node_ids[generator._id_to_uuid("main.UserService.get_user")].type == NodeType.COMPONENT
        
        assert generator._id_to_uuid("main.list_users") in node_ids
        assert node_ids[generator._id_to_uuid("main.list_users")].type == NodeType.ENDPOINT
        
        # Verify edges
        edges = dag.edges
        
        def has_edge(source, target, type):
            return any(e.source == source and e.target == target and e.type == type for e in edges)
            
        assert has_edge(generator._id_to_uuid("system_root"), generator._id_to_uuid("main"), EdgeType.CONTAINS)
        assert has_edge(generator._id_to_uuid("main"), generator._id_to_uuid("main.UserModel"), EdgeType.CONTAINS)
        assert has_edge(generator._id_to_uuid("main"), generator._id_to_uuid("main.UserService"), EdgeType.CONTAINS)
        assert has_edge(generator._id_to_uuid("main.UserService"), generator._id_to_uuid("main.UserService.get_user"), EdgeType.CONTAINS)
        assert has_edge(generator._id_to_uuid("main"), generator._id_to_uuid("main.list_users"), EdgeType.CONTAINS)
        
        # Depends on
        # Note: os and datetime are not part of the nodes, so they should be filtered out by the generator.
        # Let's check if the filter worked:
        assert not has_edge("main", "os", EdgeType.DEPENDS_ON)
        assert not has_edge("main", "datetime", EdgeType.DEPENDS_ON)

def test_reality_generator_depends_on():
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "utils.py"), "w", encoding="utf-8") as f:
            f.write("def helper(): pass\n")
            
        with open(os.path.join(tmpdir, "main.py"), "w", encoding="utf-8") as f:
            f.write("import utils\n")
            
        generator = RealityDAGGenerator(root_dir=tmpdir)
        dag = generator.generate()
        
        def has_edge(source, target, type):
            return any(e.source == source and e.target == target and e.type == type for e in dag.edges)
            
        assert has_edge(generator._id_to_uuid("main"), generator._id_to_uuid("utils"), EdgeType.DEPENDS_ON)

def test_reality_generator_agents():
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = os.path.join(tmpdir, ".agents", "agents")
        os.makedirs(agents_dir, exist_ok=True)
        agent_content = """---
name: ArchitectAgent
type: agent
description: An agent that designs architecture.
---
# Some body
"""
        with open(os.path.join(agents_dir, "architect.md"), "w", encoding="utf-8") as f:
            f.write(agent_content)

        generator = RealityDAGGenerator(root_dir=tmpdir, system_name="TestSystem")
        dag = generator.generate()

        node_ids = {n.id: n for n in dag.nodes.values()}
        
        agent_id = generator._id_to_uuid("ArchitectAgent")
        assert agent_id in node_ids
        assert node_ids[agent_id].type == NodeType.AGENT
        assert node_ids[agent_id].name == "ArchitectAgent"
        assert node_ids[agent_id].description == "An agent that designs architecture."

        def has_edge(source, target, type):
            return any(e.source == source and e.target == target and e.type == type for e in dag.edges)
            
        assert has_edge(generator._id_to_uuid("system_root"), agent_id, EdgeType.CONTAINS)
