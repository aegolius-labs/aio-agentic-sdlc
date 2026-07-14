import os
from tree_sitter import Language, Parser
import tree_sitter_python as tspython
from aio_agentic_sdlc.dag_models import NodeType, EdgeType
from .base import BaseFileParser

PYTHON_LANGUAGE = Language(tspython.language())

class TreeSitterParser(BaseFileParser):
    def __init__(self, language: Language, visitor_class: type):
        self.parser = Parser(language)
        self.visitor_class = visitor_class

    def parse(self, generator, file_path: str):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            return
            
        tree = self.parser.parse(bytes(content, 'utf8'))
        
        module_id = generator._resolve_module_id(file_path)
        
        generator._add_node(
            id=module_id,
            node_type=NodeType.MODULE,
            name=os.path.basename(file_path),
            description=f"Module {module_id}"
        )
        
        generator._add_edge("system_root", module_id, EdgeType.CONTAINS)
        
        visitor = self.visitor_class(generator, module_id)
        visitor.visit(tree.root_node)

