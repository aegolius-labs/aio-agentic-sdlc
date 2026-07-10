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
        
        assert "system_root" in node_ids
        assert node_ids["system_root"].type == NodeType.SYSTEM
        
        assert "main" in node_ids
        assert node_ids["main"].type == NodeType.MODULE
        
        assert "main.UserModel" in node_ids
        assert node_ids["main.UserModel"].type == NodeType.ENTITY
        
        assert "main.UserService" in node_ids
        assert node_ids["main.UserService"].type == NodeType.COMPONENT
        
        assert "main.UserService.get_user" in node_ids
        assert node_ids["main.UserService.get_user"].type == NodeType.COMPONENT
        
        assert "main.list_users" in node_ids
        assert node_ids["main.list_users"].type == NodeType.ENDPOINT
        
        # Verify edges
        edges = dag.edges
        
        def has_edge(source, target, type):
            return any(e.source == source and e.target == target and e.type == type for e in edges)
            
        assert has_edge("system_root", "main", EdgeType.CONTAINS)
        assert has_edge("main", "main.UserModel", EdgeType.CONTAINS)
        assert has_edge("main", "main.UserService", EdgeType.CONTAINS)
        assert has_edge("main.UserService", "main.UserService.get_user", EdgeType.CONTAINS)
        assert has_edge("main", "main.list_users", EdgeType.CONTAINS)
        
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
            
        assert has_edge("main", "utils", EdgeType.DEPENDS_ON)
