import re
import ast
from typing import List
import re
from .chat import Chat
from .agent import Agent
from typing import Dict, Any
from .data_types import GraphInfo
from .sys_prompt import AGENTIC_RESEARCHER

class AgenticSearch(Agent):
    def __init__(self, chat:Chat):
        super(AgenticSearch, self).__init__(
            chat=chat,
            system_prompt=AGENTIC_RESEARCHER
        )

        self.history = [self.chat.get_message_format(role='system', content=self.system_prompt)]

    def __call__(self, text:str=None):
        """
        Extracts entities, properties and relationships from a text chunk
        """

        # TODO: make more robust the extraction: what happens if the LLM does not generate the json?
        # TODO: llama.cpp gives the possibility to enforce the generation of a JSON output: investigate

        # extracting informations
        if text is not None:
            # it means that we are passing the user query
            self.history.append(self.chat.get_message_format(role="user", content=text))

        output = self.chat.ask(self.history)
        code = self.extract_python_code(output)
        return output, code

    def is_valid_python(self, code: str) -> bool:
        """
        Check whether a string is syntactically valid Python.
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False


    def extract_python_code(self, text: str) -> List[str]:
        """
        Extract Python code blocks from arbitrary text.
        
        Detects:
        - Markdown fenced blocks (```python ... ```)
        - Generic fenced blocks (``` ... ```)
        - Indented code blocks
        - Inline standalone code fragments
        
        Returns:
            List of unique valid Python code snippets.
        """
        candidates = set()

        # --- 1. Extract fenced Markdown blocks ---
        fenced_pattern = re.compile(
            r"```(?:python)?\s*\n(.*?)```",
            re.DOTALL | re.IGNORECASE
        )
        for match in fenced_pattern.findall(text):
            code = match.strip()
            if self.is_valid_python(code):
                candidates.add(code)

        # --- 2. Extract indented blocks (4+ spaces or tab) ---
        indented_pattern = re.compile(
            r"(?:^|\n)((?:[ \t]{4,}.*\n?)+)",
            re.MULTILINE
        )
        for match in indented_pattern.findall(text):
            # Normalize indentation
            lines = match.splitlines()
            stripped = "\n".join(line[4:] if line.startswith("    ") else line.lstrip() for line in lines)
            stripped = stripped.strip()
            if stripped and self.is_valid_python(stripped):
                candidates.add(stripped)

        # --- 3. Heuristic detection of inline code ---
        # Look for likely Python constructs
        heuristic_pattern = re.compile(
            r"(def\s+\w+\(.*?\):.*?)(?=\n\S|\Z)",
            re.DOTALL
        )
        for match in heuristic_pattern.findall(text):
            code = match.strip()
            if self.is_valid_python(code):
                candidates.add(code)

        # --- 4. Detect standalone statements (imports, assignments, etc.)
        lines = text.splitlines()
        buffer = []
        for line in lines:
            stripped = line.strip()
            if re.match(r"(import |from |class |def |if |for |while |try |with |@)", stripped):
                buffer.append(line)
            elif buffer:
                buffer.append(line)
                candidate = "\n".join(buffer).strip()
                if self.is_valid_python(candidate):
                    candidates.add(candidate)
                    buffer = []

        return sorted(candidates)

    
    def append_code_output(self, output:str):
        self.history.append(self.chat.get_message_format(role="user", content=f"CODE OUTPUT:\n{output}"))