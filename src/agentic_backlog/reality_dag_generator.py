import os
import ast
from typing import Dict, List, Set, Any
from agentic_backlog.dag_manager import DAGManager
from agentic_backlog.dag_models import Metadata, Node, Edge, NodeType, EdgeType

class PythonASTVisitor(ast.NodeVisitor):
    def __init__(self, generator, module_id: str):
        self.generator = generator
        self.module_id = module_id
        self.current_scope = module_id
        self.scope_stack = [module_id]

    def visit_ClassDef(self, node):
        class_id = f"{self.current_scope}.{node.name}"
        
        is_entity = False
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in ['BaseModel', 'Model', 'Entity']:
                is_entity = True
                
        node_type = NodeType.ENTITY if is_entity else NodeType.COMPONENT
        self.generator._add_node(
            id=class_id,
            node_type=node_type,
            name=node.name,
            description=ast.get_docstring(node) or f"Class {node.name}"
        )
        self.generator._add_edge(self.current_scope, class_id, EdgeType.CONTAINS)
        
        self.scope_stack.append(class_id)
        self.current_scope = class_id
        self.generic_visit(node)
        self.scope_stack.pop()
        self.current_scope = self.scope_stack[-1]

    def visit_FunctionDef(self, node):
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node):
        self._handle_function(node)

    def _handle_function(self, node):
        if node.name.startswith('_') and node.name != '__init__':
            return
            
        func_id = f"{self.current_scope}.{node.name}"
        
        is_endpoint = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch', 'route']:
                        is_endpoint = True
            elif isinstance(decorator, ast.Name):
                if decorator.id in ['route', 'endpoint']:
                    is_endpoint = True
                    
        node_type = NodeType.ENDPOINT if is_endpoint else NodeType.COMPONENT
        
        self.generator._add_node(
            id=func_id,
            node_type=node_type,
            name=node.name,
            description=ast.get_docstring(node) or f"Function {node.name}"
        )
        self.generator._add_edge(self.current_scope, func_id, EdgeType.CONTAINS)
        
        # We don't typically need to parse inside functions for structure, 
        # but if we want to detect calls/reads/writes we would visit the body here.
        # For now, we only need component declarations and imports (handled at module level).

    def visit_Import(self, node):
        for alias in node.names:
            imported_module = alias.name
            self.generator._add_edge(self.module_id, imported_module, EdgeType.DEPENDS_ON)
            
    def visit_ImportFrom(self, node):
        if node.module:
            imported_module = node.module
            self.generator._add_edge(self.module_id, imported_module, EdgeType.DEPENDS_ON)


class RealityDAGGenerator:
    """
    Generates a Reality DAG by statically analyzing source code.
    Currently implements a Python AST parser.
    """
    
    def __init__(self, root_dir: str, system_name: str = "System"):
        self.root_dir = os.path.abspath(root_dir)
        self.system_name = system_name
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        
        # Add system node
        self._add_node(
            id="system_root",
            node_type=NodeType.SYSTEM,
            name=self.system_name,
            description="Root project system"
        )
        
    def _add_node(self, id: str, node_type: NodeType, name: str, domain: str = None, description: str = None, attributes: Dict[str, Any] = None):
        if id not in self.nodes:
            self.nodes[id] = Node(
                id=id,
                type=node_type,
                name=name,
                domain=domain,
                description=description,
                attributes=attributes
            )

    def _add_edge(self, source: str, target: str, edge_type: EdgeType, description: str = None):
        # Avoid duplicate edges
        for edge in self.edges:
            if edge.source == source and edge.target == target and edge.type == edge_type:
                return
        self.edges.append(Edge(source=source, target=target, type=edge_type, description=description))

    def _resolve_module_id(self, file_path: str) -> str:
        # relative path without extension
        rel_path = os.path.relpath(file_path, self.root_dir)
        module_path, _ = os.path.splitext(rel_path)
        return module_path.replace(os.sep, '.')

    def parse_python_file(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                tree = ast.parse(f.read(), filename=file_path)
            except SyntaxError:
                return # Skip files with syntax errors
                
        module_id = self._resolve_module_id(file_path)
        
        # Add module node
        self._add_node(
            id=module_id,
            node_type=NodeType.MODULE,
            name=os.path.basename(file_path),
            description=f"Python module {module_id}"
        )
        
        # System contains module
        self._add_edge("system_root", module_id, EdgeType.CONTAINS)
        
        visitor = PythonASTVisitor(self, module_id)
        visitor.visit(tree)

    def generate(self) -> DAGManager:
        # Walk through the directory and parse python files
        for root, dirs, files in os.walk(self.root_dir):
            if '.venv' in dirs: dirs.remove('.venv')
            if '__pycache__' in dirs: dirs.remove('__pycache__')
            if '.git' in dirs: dirs.remove('.git')
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.parse_python_file(file_path)
                    
        # Filter out depends_on edges where target node doesn't exist
        # This removes dependencies on external libraries (stdlib, site-packages)
        # to keep the DAG focused on internal architecture
        valid_edges = []
        for edge in self.edges:
            if edge.type == EdgeType.DEPENDS_ON:
                if edge.target in self.nodes:
                    valid_edges.append(edge)
            else:
                valid_edges.append(edge)
                
        self.edges = valid_edges
                    
        metadata = Metadata(name=self.system_name, version="1.0.0")
        return DAGManager(metadata=metadata, nodes=list(self.nodes.values()), edges=self.edges)
