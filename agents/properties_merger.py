from .sys_prompt import PROPERTIES_MERGER
from .chat import Chat
from .agent import Agent
import json

class PropertiesMerger(Agent):
    def __init__(self, chat:Chat):
        super(PropertiesMerger, self).__init__(
            chat=chat,
            system_prompt=PROPERTIES_MERGER
        )

    def __call__(self, proposals:list[str], existing:list[str]):
        """
        Merges together the properties that have the same meaning.
        """
        # extracting informations
        output = self.execute_basic_call(f"Existing Properties: {existing}\nProposed Properties: {proposals}")
        equal_properties = self.parse_property_deduplication(output)
        return equal_properties

    def parse_property_deduplication(self, llm_response: str) -> dict:
        """
        Parses the dashed list output from the property deduplication agent.
        
        Args:
            llm_response (str): The raw text output from the LLM.
            
        Returns:
            dict: A mapping of {proposed_property: existing_property}.
                Returns an empty dictionary {} if no duplicates were found.
        """
        mapping = {}
        cleaned_response = llm_response.strip()
        
        # 1. Handle the case where no duplicates exist
        if cleaned_response.lower() == "none":
            return mapping
            
        # 2. Process the response line by line
        for line in cleaned_response.split('\n'):
            line = line.strip()
            
            # Skip empty lines or malformed lines that don't start with a dash
            if not line or not line.startswith('-'):
                continue
                
            # Remove the leading dash and split by the equals sign
            # Output format is: - existing_property = proposed_property
            line_content = line.lstrip('-').strip()
            
            if '=' in line_content:
                # split('=', 1) ensures we only split on the first equals sign
                parts = line_content.split('=', 1) 
                existing_prop = parts[0].strip()
                proposed_prop = parts[1].strip()
                
                # Populate the dictionary
                mapping[proposed_prop] = existing_prop
                
        return mapping