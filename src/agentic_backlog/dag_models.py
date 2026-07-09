from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class NodeType(str, Enum):
    SYSTEM = "system"
    CONTAINER = "container"
    MODULE = "module"
    COMPONENT = "component"
    ENDPOINT = "endpoint"
    ENTITY = "entity"

class EdgeType(str, Enum):
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    CALLS = "calls"
    PUBLISHES = "publishes"
    SUBSCRIBES = "subscribes"
    READS = "reads"
    WRITES = "writes"
    IMPLEMENTS = "implements"

class Metadata(BaseModel):
    name: str
    version: str

class Node(BaseModel):
    id: str
    type: NodeType
    name: str
    domain: Optional[str] = None
    description: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None

class Edge(BaseModel):
    source: str
    target: str
    type: EdgeType
    description: Optional[str] = None
