"""Observe TypeScript source in the same ontology as Python (ONTOLOGY-AC1/AC2).

The TypeScript parser emits only the core concepts the Python parser emits:
a `module` node per file, `component` (or `entity`) nodes for classes,
`component` nodes for functions and methods, `contains` edges from scope to
symbol, and `depends_on` edges for imports. Source locations use the same
`class` and `function` symbol kinds.

Concepts with no Python counterpart (interfaces, type aliases, enums,
declaration files) are not observed, so nothing TypeScript-specific reaches the
core schema. Identity works the same way: a `// aio-sdlc-node: <uuid>` comment
on the line directly above a definition, or above its decorators and `export`,
gives that definition the Intention node's GUID. A marker anywhere else at the
top of the file names the module.

Endpoint detection is Python-only for now: TypeScript routes are framework
specific, so TypeScript functions are always components.
"""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import tree_sitter_typescript as tstypescript
from tree_sitter import Language, Node, Parser

from aio_agentic_sdlc.dag_models import EdgeType, NodeType
from aio_agentic_sdlc.source_locations import SourceLocation
from aio_agentic_sdlc.source_markers import canonical_line_comment_marker

from .base import BaseFileParser

TYPESCRIPT_LANGUAGE = Language(tstypescript.language_typescript())
TSX_LANGUAGE = Language(tstypescript.language_tsx())
TYPESCRIPT_EXTENSIONS = (".ts", ".tsx")
_RESOLVABLE_EXTENSIONS = (".ts", ".tsx")
_CLASS_TYPES = {"class_declaration", "abstract_class_declaration"}
_FUNCTION_TYPES = {"function_declaration", "generator_function_declaration"}
_FUNCTION_VALUES = {"arrow_function", "function_expression", "generator_function"}
_ENTITY_BASES = {"BaseModel", "Model", "Entity"}
_DEFINITION_TYPES = {
    "export_statement",
    "lexical_declaration",
    *_CLASS_TYPES,
    *_FUNCTION_TYPES,
}
_STRUCTURAL_CONTAINERS = {
    "statement_block",
    "if_statement",
    "else_clause",
    "try_statement",
    "catch_clause",
    "finally_clause",
}


def _text(node: Node) -> str:
    return node.text.decode("utf-8")


def _jsdoc_text(comment: str) -> str | None:
    if not comment.startswith("/**"):
        return None
    body = comment[3:-2] if comment.endswith("*/") else comment[3:]
    lines = [re.sub(r"^\s*\*?\s?", "", line).rstrip() for line in body.splitlines()]
    text = "\n".join(lines).strip()
    return text or None


def is_declaration_file(file_path: str) -> bool:
    return file_path.casefold().endswith((".d.ts", ".d.tsx"))


class TypeScriptParser(BaseFileParser):
    """Parse one `.ts` or `.tsx` file into Reality nodes and edges."""

    def __init__(self):
        self.parsers = {
            ".ts": Parser(TYPESCRIPT_LANGUAGE),
            ".tsx": Parser(TSX_LANGUAGE),
        }

    def parse(self, generator, file_path: str):
        if is_declaration_file(file_path):
            return
        extension = os.path.splitext(file_path)[1].casefold()
        parser = self.parsers.get(extension)
        if parser is None:
            return
        try:
            raw_content = Path(file_path).read_bytes()
            content = raw_content.decode("utf-8")
        except UnicodeDecodeError:
            return

        tree = parser.parse(raw_content)
        lines = content.splitlines()
        source_sha256 = hashlib.sha256(raw_content).hexdigest()
        root = tree.root_node

        module_uuid = None
        for child in root.named_children:
            if child.type != "comment":
                continue
            marker = canonical_line_comment_marker(_text(child))
            if marker is None:
                continue
            following = child.next_named_sibling
            adjacent = (
                following is not None
                and following.type in _DEFINITION_TYPES
                and following.start_point.row == child.end_point.row + 1
            )
            if not adjacent:
                module_uuid = marker
                break

        module_id = (
            module_uuid if module_uuid else generator._resolve_module_id(file_path)
        )
        generator._add_node(
            id=module_id,
            node_type=NodeType.MODULE,
            name=os.path.basename(file_path),
            description=f"Module {module_id}",
            explicit_identity=module_uuid is not None,
            source_location=SourceLocation(
                path=generator._source_path(file_path),
                symbol_kind="module",
                symbol_name=os.path.basename(file_path),
                definition_line=1,
                marker_line=1,
                source_sha256=source_sha256,
            ),
        )
        generator._add_edge("system_root", module_id, EdgeType.CONTAINS)

        visitor = TypeScriptVisitor(
            generator,
            module_id,
            file_path=file_path,
            lines=lines,
            source_sha256=source_sha256,
        )
        for child in root.named_children:
            visitor.visit(child)


class TypeScriptVisitor:
    def __init__(self, generator, module_id, *, file_path, lines, source_sha256):
        self.generator = generator
        self.module_id = module_id
        self.scope_stack = [module_id]
        self.file_path = file_path
        self.lines = lines
        self.source_sha256 = source_sha256

    @property
    def current_scope(self) -> str:
        return self.scope_stack[-1]

    # Identity and documentation -------------------------------------------

    def _identity(self, outer: Node) -> tuple[str | None, int]:
        """Return the marker above a definition and the line it claims."""

        row = outer.start_point.row
        marker = None
        if row > 0:
            marker = canonical_line_comment_marker(self.lines[row - 1])
        return marker, (row if marker is not None else row + 1)

    def _description(self, outer: Node, fallback: str) -> str:
        sibling = outer.prev_named_sibling
        while sibling is not None and sibling.type == "comment":
            text = _text(sibling)
            if canonical_line_comment_marker(text) is None:
                return _jsdoc_text(text) or fallback
            sibling = sibling.prev_named_sibling
        return fallback

    def _location(self, outer, node, kind, name) -> SourceLocation:
        _, marker_line = self._identity(outer)
        return SourceLocation(
            path=self.generator._source_path(self.file_path),
            symbol_kind=kind,
            symbol_name=name,
            definition_line=node.start_point.row + 1,
            marker_line=marker_line,
            source_sha256=self.source_sha256,
        )

    def _add_symbol(self, outer, node, *, kind, name, node_type, fallback):
        marker, _ = self._identity(outer)
        symbol_id = marker or f"{self.current_scope}.{name}"
        self.generator._add_node(
            id=symbol_id,
            node_type=node_type,
            name=name,
            description=self._description(outer, fallback),
            explicit_identity=marker is not None,
            source_location=self._location(outer, node, kind, name),
        )
        self.generator._add_edge(self.current_scope, symbol_id, EdgeType.CONTAINS)
        return symbol_id

    # Traversal --------------------------------------------------------------

    def visit(self, node: Node, outer: Node | None = None):
        outer = outer or node
        if node.type == "export_statement":
            declaration = node.child_by_field_name("declaration")
            if declaration is not None:
                self.visit(declaration, outer)
            if node.child_by_field_name("source") is not None:
                self._import(node)
        elif node.type in _CLASS_TYPES:
            self._class(node, outer)
        elif node.type in _FUNCTION_TYPES:
            self._function(node, outer)
        elif node.type == "lexical_declaration":
            self._function_constants(node, outer)
        elif node.type == "import_statement":
            self._import(node)
        elif node.type in _STRUCTURAL_CONTAINERS:
            for child in node.named_children:
                self.visit(child)

    def _class(self, node: Node, outer: Node):
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _text(name_node)
        node_type = (
            NodeType.ENTITY if self._extends_entity(node) else NodeType.COMPONENT
        )
        class_id = self._add_symbol(
            outer,
            node,
            kind="class",
            name=name,
            node_type=node_type,
            fallback=f"Class {name}",
        )
        body = node.child_by_field_name("body")
        if body is None:
            return
        self.scope_stack.append(class_id)
        decorators: list[Node] = []
        for child in body.named_children:
            if child.type == "decorator":
                decorators.append(child)
                continue
            if child.type == "method_definition":
                self._method(child, decorators[0] if decorators else child)
            decorators = []
        self.scope_stack.pop()

    def _extends_entity(self, node: Node) -> bool:
        for child in node.named_children:
            if child.type != "class_heritage":
                continue
            for clause in child.named_children:
                if clause.type != "extends_clause":
                    continue
                value = clause.child_by_field_name("value")
                if value is not None and _text(value) in _ENTITY_BASES:
                    return True
        return False

    def _method(self, node: Node, outer: Node):
        name_node = node.child_by_field_name("name")
        if name_node is None or name_node.type == "private_property_identifier":
            return
        name = _text(name_node)
        if name.startswith("_"):
            return
        if any(
            child.type == "accessibility_modifier" and _text(child) != "public"
            for child in node.children
        ):
            return
        self._add_symbol(
            outer,
            node,
            kind="function",
            name=name,
            node_type=NodeType.COMPONENT,
            fallback=f"Function {name}",
        )

    def _function(self, node: Node, outer: Node):
        name_node = node.child_by_field_name("name")
        if name_node is None:
            return
        name = _text(name_node)
        if name.startswith("_"):
            return
        self._add_symbol(
            outer,
            node,
            kind="function",
            name=name,
            node_type=NodeType.COMPONENT,
            fallback=f"Function {name}",
        )

    def _function_constants(self, node: Node, outer: Node):
        declarators = [
            c for c in node.named_children if c.type == "variable_declarator"
        ]
        if len(declarators) != 1:
            return
        declarator = declarators[0]
        name_node = declarator.child_by_field_name("name")
        value = declarator.child_by_field_name("value")
        if name_node is None or name_node.type != "identifier":
            return
        if value is None or value.type not in _FUNCTION_VALUES:
            return
        name = _text(name_node)
        if name.startswith("_"):
            return
        self._add_symbol(
            outer,
            node,
            kind="function",
            name=name,
            node_type=NodeType.COMPONENT,
            fallback=f"Function {name}",
        )

    # Imports ----------------------------------------------------------------

    def _import(self, node: Node):
        source = node.child_by_field_name("source")
        if source is None:
            return
        fragment = next(
            (c for c in source.named_children if c.type == "string_fragment"), None
        )
        if fragment is None:
            return
        target = self._resolve_import(_text(fragment))
        self.generator._add_edge(self.module_id, target, EdgeType.DEPENDS_ON)

    def _resolve_import(self, specifier: str) -> str:
        """Resolve a relative import to the module id its file would have."""

        if not specifier.startswith((".", "/")):
            return specifier
        base = os.path.normpath(
            os.path.join(os.path.dirname(self.file_path), specifier)
        )
        stem, extension = os.path.splitext(base)
        candidates = []
        if extension in (".js", ".jsx", ".ts", ".tsx"):
            candidates += [stem + ext for ext in _RESOLVABLE_EXTENSIONS]
        candidates += [base + ext for ext in _RESOLVABLE_EXTENSIONS]
        candidates += [
            os.path.join(base, "index" + ext) for ext in _RESOLVABLE_EXTENSIONS
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return self.generator._resolve_module_id(candidate)
        return specifier
