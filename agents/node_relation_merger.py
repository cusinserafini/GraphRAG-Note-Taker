from .sys_prompt import NODE_RELATION_MERGER
from .chat import Chat
from .agent import Agent
import json

class NodeRelationMerger(Agent):
    def __init__(self, chat:Chat):
        super(NodeRelationMerger, self).__init__(
            chat=chat,
            system_prompt=NODE_RELATION_MERGER
        )

    def __call__(self, proposal:dict, data_list:list[dict]):
        """
        Given a list of nodes/relations present in the graph and a proposed node/relation,
        the agent decides wether to use the one just created or the proposed one.
        """
        # extracting informations
        numbered_list = ""
        for i, item in enumerate(data_list):
            numbered_list += f"{i+1}. NAME={item['name']};DESCRIPTION={item['description']}\n"

        output = self.execute_basic_call(f"Proposed Entity: NAME={proposal['name']};DESCRIPTION={proposal['description']}\nExisting Entities:\n{numbered_list}\nJust return the json")
        selection = self.parse_entity_resolution_output(output)
        return selection

    def parse_entity_resolution_output(self, llm_response: str):
        """
        Parses the JSON output from the entity resolution agent.
        
        Args:
            llm_response (str): The raw text output from the LLM.
            
        Returns:
            int or None: The selected entity index, or None if a new entity must be created.
                        Returns None on failure (or you could choose to raise an exception).
        """
        # 1. Clean the response (strip whitespace and potential markdown backticks)
        cleaned_response = llm_response.strip()
        
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        elif cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
            
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
            
        cleaned_response = cleaned_response.strip()

        # 2. Parse the JSON and extract the value
        try:
            data = json.loads(cleaned_response)
            
            if "selected" in data:
                # Will be an integer or None (since JSON 'null' parses to Python 'None')
                return data["selected"] 
            else:
                print(f"Error: The key 'selected' was not found in the output: {data}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode JSON. Raw output: '{llm_response}'. Details: {e}")
            return None