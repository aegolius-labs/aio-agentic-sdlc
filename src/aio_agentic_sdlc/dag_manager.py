# aio-sdlc-node: cb432b58-db06-4d49-a6ab-c11c9e86bcc2
import yaml
from typing import List, Dict, Any, Set
from pydantic import ValidationError
from aio_agentic_sdlc.dag_models import Metadata, Node, Edge, NodeType, EdgeType

class DAGManager:
    def __init__(self, metadata: Metadata, nodes: List[Node], edges: List[Edge]):
        self.metadata = metadata
        self.nodes: Dict[str, Node] = {n.id: n for n in nodes}
        self.edges: List[Edge] = edges

    @classmethod
    def load(cls, filepath: str) -> "DAGManager":
        with open(filepath, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
        metadata = Metadata(**data.get("metadata", {}))
        nodes = [Node(**n) for n in data.get("nodes", [])]
        edges = [Edge(**e) for e in data.get("edges", [])]
        
        return cls(metadata, nodes, edges)

    def save(self, filepath: str):
        data = {
            "metadata": self.metadata.model_dump(mode='json', exclude_none=True),
            "nodes": [n.model_dump(mode='json', exclude_none=True) for n in self.nodes.values()],
            "edges": [e.model_dump(mode='json', exclude_none=True) for e in self.edges]
        }
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False)

    def validate(self):
        # Reference Integrity
        for edge in self.edges:
            if edge.source not in self.nodes:
                raise ValueError(f"Edge source node {edge.source} does not exist.")
            if edge.target not in self.nodes:
                raise ValueError(f"Edge target node {edge.target} does not exist.")

        # Cycle detection for specific edge types
        graph = {n_id: [] for n_id in self.nodes}
        for edge in self.edges:
            if edge.type in [EdgeType.DEPENDS_ON, EdgeType.CALLS, EdgeType.CONTAINS]:
                graph[edge.source].append(edge.target)

        visited = set()
        rec_stack = set()

        def dfs(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph.get(node_id, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node_id in self.nodes:
            if node_id not in visited:
                if dfs(node_id):
                    raise ValueError(f"Cycle detected involving node {node_id}.")

    def add_node(self, node: Node):
        if node.id in self.nodes:
            raise ValueError(f"Node {node.id} already exists.")
        self.nodes[node.id] = node

    def update_node(self, node_id: str, **kwargs):
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist.")
        
        node = self.nodes[node_id]
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        updated_node = node.model_copy(update=update_data)
        self.nodes[node_id] = updated_node

    def remove_node(self, node_id: str):
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist.")
        
        del self.nodes[node_id]
        
        # Cascade remove edges
        self.edges = [e for e in self.edges if e.source != node_id and e.target != node_id]

    def get_node(self, node_id: str) -> Node:
        if node_id not in self.nodes:
            raise ValueError(f"Node {node_id} does not exist.")
        return self.nodes[node_id]

    def find_nodes(self, **filters) -> List[Node]:
        result = []
        for node in self.nodes.values():
            match = True
            for k, v in filters.items():
                if v is None:
                    continue
                if getattr(node, k, None) != v:
                    match = False
                    break
            if match:
                result.append(node)
        return result

    def add_edge(self, edge: Edge):
        if edge.source not in self.nodes:
            raise ValueError(f"Source node {edge.source} does not exist.")
        if edge.target not in self.nodes:
            raise ValueError(f"Target node {edge.target} does not exist.")
        
        self.edges.append(edge)
        
        try:
            self.validate()
        except ValueError as e:
            # Revert if adding creates an invalid DAG
            self.edges.pop()
            raise e

    def remove_edge(self, source: str, target: str, edge_type: EdgeType):
        initial_len = len(self.edges)
        self.edges = [
            e for e in self.edges 
            if not (e.source == source and e.target == target and e.type == edge_type)
        ]
        if len(self.edges) == initial_len:
            raise ValueError(f"Edge {source} -> {target} ({edge_type}) does not exist.")

    def get_edges(self, source: str = None, target: str = None, edge_type: EdgeType = None) -> List[Edge]:
        result = []
        for edge in self.edges:
            if source and edge.source != source:
                continue
            if target and edge.target != target:
                continue
            if edge_type and edge.type != edge_type:
                continue
            result.append(edge)
        return result
