import os
from typing import Dict, List, Set, Any, Optional
from tree_sitter import Language, Parser, Node
import tree_sitter_python
from aio_agentic_sdlc.dag_manager import DAGManager
from aio_agentic_sdlc.dag_models import Metadata, Node as DAGNode, Edge, NodeType, EdgeType

PYTHON_LANGUAGE = Language(tree_sitter_python.language())

class TreeSitterVisitor:
    def __init__(self, generator, module_id: str):
        self.generator = generator
        self.module_id = module_id
        self.current_scope = module_id
        self.scope_stack = [module_id]

    def visit(self, node: Node):
        if node.type == 'class_definition':
            self.visit_class_definition(node, [])
        elif node.type in ('function_definition', 'async_function_definition'):
            self.visit_function_definition(node, [])
        elif node.type == 'decorated_definition':
            self.visit_decorated_definition(node)
        elif node.type == 'import_statement':
            self.visit_import_statement(node)
        elif node.type == 'import_from_statement':
            self.visit_import_from_statement(node)
        else:
            for child in node.children:
                if child.is_named:
                    self.visit(child)

    def visit_decorated_definition(self, node: Node):
        decorators = []
        for child in node.children:
            if child.type == 'decorator':
                decorators.append(child)
                
        for child in node.children:
            if child.type == 'class_definition':
                self.visit_class_definition(child, decorators)
            elif child.type in ('function_definition', 'async_function_definition'):
                self.visit_function_definition(child, decorators)

    def visit_class_definition(self, node: Node, decorators: List[Node]):
        name_node = node.child_by_field_name('name')
        if not name_node:
            return
        name = name_node.text.decode('utf8')
        class_id = f"{self.current_scope}.{name}"

        is_entity = False
        superclasses_node = node.child_by_field_name('superclasses')
        if superclasses_node:
            for child in superclasses_node.children:
                if child.type == 'identifier':
                    base_name = child.text.decode('utf8')
                    if base_name in ['BaseModel', 'Model', 'Entity']:
                        is_entity = True

        node_type = NodeType.ENTITY if is_entity else NodeType.COMPONENT
        
        docstring = f"Class {name}"
        body = node.child_by_field_name('body')
        if body and len(body.children) > 0:
            first_stmt = body.children[0]
            if first_stmt.type == 'expression_statement':
                first_expr = first_stmt.children[0]
                if first_expr.type == 'string':
                    docstring = first_expr.text.decode('utf8').strip('\'"')

        self.generator._add_node(
            id=class_id,
            node_type=node_type,
            name=name,
            description=docstring
        )
        self.generator._add_edge(self.current_scope, class_id, EdgeType.CONTAINS)

        self.scope_stack.append(class_id)
        self.current_scope = class_id
        
        if body:
            for child in body.children:
                if child.is_named:
                    self.visit(child)
                    
        self.scope_stack.pop()
        self.current_scope = self.scope_stack[-1]

    def _extract_decorator_names(self, decorators: List[Node]) -> List[str]:
        names = []
        for dec in decorators:
            for child in dec.children:
                if child.type == 'identifier':
                    names.append(child.text.decode('utf8'))
                elif child.type == 'attribute':
                    attr_name = child.child_by_field_name('attribute')
                    if attr_name:
                        names.append(attr_name.text.decode('utf8'))
                elif child.type == 'call':
                    func = child.child_by_field_name('function')
                    if func:
                        if func.type == 'identifier':
                            names.append(func.text.decode('utf8'))
                        elif func.type == 'attribute':
                            attr_name = func.child_by_field_name('attribute')
                            if attr_name:
                                names.append(attr_name.text.decode('utf8'))
        return names

    def visit_function_definition(self, node: Node, decorators: List[Node]):
        name_node = node.child_by_field_name('name')
        if not name_node:
            return
            
        name = name_node.text.decode('utf8')
        if name.startswith('_') and name != '__init__':
            return

        func_id = f"{self.current_scope}.{name}"

        is_endpoint = False
        dec_names = self._extract_decorator_names(decorators)
        for d in dec_names:
            if d in ['get', 'post', 'put', 'delete', 'patch', 'route', 'endpoint']:
                is_endpoint = True

        node_type = NodeType.ENDPOINT if is_endpoint else NodeType.COMPONENT
        
        docstring = f"Function {name}"
        body = node.child_by_field_name('body')
        if body and len(body.children) > 0:
            first_stmt = body.children[0]
            if first_stmt.type == 'expression_statement':
                first_expr = first_stmt.children[0]
                if first_expr.type == 'string':
                    docstring = first_expr.text.decode('utf8').strip('\'"')

        self.generator._add_node(
            id=func_id,
            node_type=node_type,
            name=name,
            description=docstring
        )
        self.generator._add_edge(self.current_scope, func_id, EdgeType.CONTAINS)

    def visit_import_statement(self, node: Node):
        for child in node.children:
            if child.type == 'dotted_name':
                imported_module = child.text.decode('utf8')
                self.generator._add_edge(self.module_id, imported_module, EdgeType.DEPENDS_ON)
            elif child.type == 'aliased_import':
                for subchild in child.children:
                    if subchild.type == 'dotted_name':
                        imported_module = subchild.text.decode('utf8')
                        self.generator._add_edge(self.module_id, imported_module, EdgeType.DEPENDS_ON)
                        break

    def visit_import_from_statement(self, node: Node):
        module_name_node = node.child_by_field_name('module_name')
        if module_name_node:
            imported_module = module_name_node.text.decode('utf8')
            self.generator._add_edge(self.module_id, imported_module, EdgeType.DEPENDS_ON)
        else:
            for child in node.children:
                if child.type == 'dotted_name':
                    imported_module = child.text.decode('utf8')
                    self.generator._add_edge(self.module_id, imported_module, EdgeType.DEPENDS_ON)
                    break

class RealityDAGGenerator:
    """
    Generates a Reality DAG by statically analyzing source code.
    Implements a tree-sitter parser to be stack-agnostic.
    """
    
    def __init__(self, root_dir: str, system_name: str = "System"):
        self.root_dir = os.path.abspath(root_dir)
        self.system_name = system_name
        self.nodes: Dict[str, DAGNode] = {}
        self.edges: List[Edge] = []
        self.parser = Parser(PYTHON_LANGUAGE)
        
        # Add system node
        self._add_node(
            id="system_root",
            node_type=NodeType.SYSTEM,
            name=self.system_name,
            description="Root project system"
        )
        
    def _add_node(self, id: str, node_type: NodeType, name: str, domain: str = None, description: str = None, attributes: Dict[str, Any] = None):
        if id not in self.nodes:
            self.nodes[id] = DAGNode(
                id=id,
                type=node_type,
                name=name,
                domain=domain,
                description=description,
                attributes=attributes
            )

    def _add_edge(self, source: str, target: str, edge_type: EdgeType, description: str = None):
        for edge in self.edges:
            if edge.source == source and edge.target == target and edge.type == edge_type:
                return
        self.edges.append(Edge(source=source, target=target, type=edge_type, description=description))

    def _resolve_module_id(self, file_path: str) -> str:
        rel_path = os.path.relpath(file_path, self.root_dir)
        module_path, _ = os.path.splitext(rel_path)
        return module_path.replace(os.sep, '.')

    def parse_python_file(self, file_path: str):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        tree = self.parser.parse(bytes(content, 'utf8'))
        
        module_id = self._resolve_module_id(file_path)
        
        self._add_node(
            id=module_id,
            node_type=NodeType.MODULE,
            name=os.path.basename(file_path),
            description=f"Python module {module_id}"
        )
        
        self._add_edge("system_root", module_id, EdgeType.CONTAINS)
        
        visitor = TreeSitterVisitor(self, module_id)
        visitor.visit(tree.root_node)

    def generate(self) -> DAGManager:
        for root, dirs, files in os.walk(self.root_dir):
            if '.venv' in dirs: dirs.remove('.venv')
            if '__pycache__' in dirs: dirs.remove('__pycache__')
            if '.git' in dirs: dirs.remove('.git')
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.parse_python_file(file_path)
                    
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
