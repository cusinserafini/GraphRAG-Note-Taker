from typing import Any
from mypy_extensions import TypedDict
from dataclasses import dataclass, asdict

class MessageFormat(TypedDict):
    # defines the format message of the LLM's chat template
    role: str
    content: str

class Edge(TypedDict):
    # collects the edges info that the LLM is retrieving from the text
    subject: str
    relationship: str
    object: str
    parameters: dict
    description: str

class GraphInfo(TypedDict):
    # collects the nodes and relationships extracted from a text chunk
    nodes: dict  # name of the node: {properties}
    edges: list[Edge]

class GraphComponentsDescriptor(TypedDict):
    # collects the nodes and relationships descriptions/definitions
    node_descriptions: dict
    relationship_definitions: dict

@dataclass
class EdgePayload():
    # edge's payload present in the vector DB 
    name: str
    description: str
    type: str = "edge"

    def as_dict(self):
        return asdict(self)

@dataclass
class NodePayload():
    # node's payload present in the vector DB 
    type: str = "node"

    def as_dict(self):
        return asdict(self)

@dataclass
class GraphNode():
    # node's payload present in the vector DB 
    properties: dict[str, Any]
    label: str = "Entity"

    def as_dict(self):
        return asdict(self)