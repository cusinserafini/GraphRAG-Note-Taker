from .sys_prompt import NODE_RELATION_MERGER
from .chat import Chat
from .agent import Agent
import json
import re

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

        output = self.execute_basic_call(f"Proposed Entity: NAME={proposal['name']};DESCRIPTION={proposal['description']}\nExisting Entities:\n{numbered_list}\n\nYou are not obliged to select the existing ones, you can keep the proposal. Just think if they relate or not. you can Just return the json")
        selection = self.parse_entity_resolution_output(output)
        return selection

    def parse_entity_resolution_output(self, llm_response: str):
        """
        Robust parser for LLM responses that contain reasoning plus JSON.
        Returns:
            int or None: the selected entity index, or None if a new entity.
        """
        # 1. Clean markdown backticks
        cleaned = llm_response.strip()
        cleaned = re.sub(r'^```(?:json)?', '', cleaned)
        cleaned = re.sub(r'```$', '', cleaned)
        
        # 2. Find all JSON objects in the text
        json_matches = re.findall(r'\{.*?\}', cleaned, re.DOTALL)
        if not json_matches:
            print(f"Warning: No JSON found in LLM output:\n{llm_response}")
            return None
        
        # 3. Take the **last JSON object** (usually the one the LLM intends as output)
        last_json_str = json_matches[-1]

        # 4. Parse safely
        try:
            data = json.loads(last_json_str)
            if "selected" in data:
                return data["selected"]
            else:
                print(f"Warning: 'selected' key not found in JSON: {data}")
                return None
        except json.JSONDecodeError as e:
            print(f"Error: Failed to decode JSON. Raw extracted JSON: '{last_json_str}'. Details: {e}")
            return None
    