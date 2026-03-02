from .chat import Chat
from .agent import Agent
from .sys_prompt import DESCRIPTOR
from .data_types import GraphComponentsDescriptor, GraphInfo


class Descriptor(Agent):
    def __init__(self, chat:Chat):
        super(Descriptor, self).__init__(
            chat=chat,
            system_prompt=DESCRIPTOR
        )

    def __call__(self, text:str, graph_info:GraphInfo) -> GraphInfo:
        # formatting the input message
        nodes = list(graph_info['nodes'].keys())
        relationships = [edge['relationship'] for edge in graph_info['edges']]

        nodes_str = ""
        for node in nodes:
            nodes_str += f"- {node}\n"

        relationships_str = ""
        for relation in relationships:
            relationships_str += f"- {relation}\n"

        # TODO: make more robust the extraction: what happens if the LLM does not generate the json?
        # TODO: llama.cpp gives the possibility to enforce the generation of a JSON output: investigate

        user_message = f"**Source Text:** {text}\n\n**Extracted Nodes:**\n{nodes_str}\n**Extracted Relationships:**\n{relationships_str}\n\When you write the names and description, wirte just plain text, not markdown or quotation marks."
        output = self.execute_basic_call(user_message)
        descriptions = self.parse_graph_ontology(output)

        # updating the graph_info
        # TODO: manage possible errors
        for node_name, node_description in zip(descriptions['node_descriptions'].keys(), descriptions['node_descriptions'].values()):
            graph_info['nodes'][node_name]['description'] = node_description

        for edge in graph_info['edges']:
            relationship_name = edge['relationship']
            edge['description'] = descriptions['relationship_definitions'][relationship_name]

        return graph_info

    def parse_graph_ontology(self, llm_output: str) -> GraphComponentsDescriptor:
        """
        Parses LLM output containing node descriptions and relationship definitions.
        
        Returns a dictionary with two main keys:
        - 'node_descriptions': A dictionary mapping node names to their descriptions.
        - 'relationship_definitions': A dictionary mapping relationship names to their universal definitions.
        """
        parsed_data = GraphComponentsDescriptor(node_descriptions={}, relationship_definitions={})
        
        # State tracker to know which section we are currently parsing
        current_section = None
        
        # Process line by line, ignoring empty lines
        lines = [line.strip() for line in llm_output.strip().split('\n') if line.strip()]
        
        for line in lines:
            # 1. IDENTIFY SECTIONS
            # We look for keywords to switch our parsing state
            line_lower = line.lower()
            if "node descriptions:" in line_lower:
                current_section = "node_descriptions"
                continue
            elif "relationship definitions:" in line_lower:
                current_section = "relationship_definitions"
                continue
                
            # 2. PARSE LIST ITEMS
            # If we are in a section and the line is a dashed list item
            if current_section and line.startswith("-"):
                # Strip the leading dash and any surrounding whitespace
                content = line.lstrip("-").strip()
                
                # Split only on the first colon to separate the name from the description
                if ":" in content:
                    name_part, desc_part = content.split(":", 1)
                    
                    name = name_part.strip().lower()
                    description = desc_part.strip()
                    
                    # Assign to the correct dictionary based on the current state
                    parsed_data[current_section][name] = description

        return parsed_data