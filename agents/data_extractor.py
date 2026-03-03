import re
from .chat import Chat
from .agent import Agent
from typing import Dict, Any
from .data_types import GraphInfo
from .sys_prompt import DATA_EXTRACTOR

class DataExtractor(Agent):
    def __init__(self, chat:Chat):
        super(DataExtractor, self).__init__(
            chat=chat,
            system_prompt=DATA_EXTRACTOR
        )

    def __call__(self, text:str, current_entities:list[dict], current_relations:list[dict]):
        """
        Extracts entities, properties and relationships from a text chunk
        """

        # TODO: make more robust the extraction: what happens if the LLM does not generate the json?
        # TODO: llama.cpp gives the possibility to enforce the generation of a JSON output: investigate

        # extracting informations
        output = self.execute_basic_call(f"**Input:**\nExisting Entities: {current_entities}\nExisting Relations: {current_relations}\nText: {text}\n\nBe far-sighted: the distinction between properties and node is important.")
        graph_data = self.parse_property_graph(output)
        return graph_data

    def parse_property_graph(self, llm_output: str) -> Dict[str, Any]:
        """
        Parses LLM output into a structured format for a Property Graph.
        
        Returns a dictionary with two main keys:
        - 'nodes': A dictionary mapping entity names to their attributes.
        - 'edges': A list of relationships (subject, relationship, object, parameters).
        """
        graph_data = GraphInfo(nodes={}, edges=[])
        
        # Process line by line, ignoring empty lines
        lines = [line.strip() for line in llm_output.strip().split('\n') if line.strip()]
        
        for line in lines:
            # Only process lines that follow the output format
            if not line.startswith("-"):
                continue
                
            # Strip the leading dash and any surrounding whitespace
            content = line.lstrip("-").strip()
            
            # 1. PARSE RELATIONSHIPS (EDGES)
            # We check for '->' to identify a relationship line
            if "->" in content:
                # Split by '->' to isolate subject, relationship(+params), and object
                parts = [p.strip() for p in content.split("->")]
                
                if len(parts) >= 3:
                    subject_entity = parts[0].lower()
                    object_entity = parts[-1].lower()
                    
                    # Rejoin just in case the relationship name itself somehow had an arrow
                    rel_with_params = "->".join(parts[1:-1])
                    
                    relationship_name = rel_with_params
                    parameters = {}
                    
                    # Extract parameters if they exist inside { }
                    param_match = re.search(r'\{(.*?)\}', rel_with_params)
                    if param_match:
                        # Everything before the '{' is the relationship name
                        relationship_name = rel_with_params[:param_match.start()].strip()
                        
                        # Parse the comma-separated key=value pairs
                        param_str = param_match.group(1)
                        for param_pair in param_str.split(','):
                            if '=' in param_pair:
                                k, v = param_pair.split('=', 1)
                                val = v.strip()
                                clean_val = val.strip('\'"')
                                try:
                                    val = float(clean_val) if '.' in clean_val else int(clean_val)
                                except ValueError:
                                    pass
                                parameters[k.strip()] = val
                    else:
                        relationship_name = relationship_name.strip()
                    
                    # Add to edges list
                    graph_data["edges"].append({
                        "subject": subject_entity,
                        "relationship": relationship_name.lower(),
                        "object": object_entity,
                        "parameters": parameters
                    })
                    
                    # Ensure the entities exist in the nodes dictionary
                    if subject_entity not in graph_data["nodes"]:
                        graph_data["nodes"][subject_entity] = {}
                    if object_entity not in graph_data["nodes"]:
                        graph_data["nodes"][object_entity] = {}

            # 2. PARSE ATTRIBUTES (NODE PROPERTIES)
            # We check for ':' and '=' to identify an attribute line
            elif ":" in content and "=" in content:
                # Split only on the first colon to separate entity from the attribute definition
                entity_part, attr_part = content.split(":", 1)
                entity_name = entity_part.strip().lower()
                
                # Split only on the first equals sign to separate key and value
                if "=" in attr_part:
                    attr_name, attr_val = attr_part.split("=", 1)
                    
                    # Ensure entity exists in nodes dictionary
                    if entity_name not in graph_data["nodes"]:
                        graph_data["nodes"][entity_name] = {}
                    
                    # Assign the attribute
                    val = attr_val.strip()
                    clean_val = val.strip('\'"')
                    try:
                        val = float(clean_val) if '.' in clean_val else int(clean_val)
                    except ValueError:
                        pass
                    graph_data["nodes"][entity_name][attr_name.strip()] = val

        return graph_data
