from asyncio import timeout
from time import time
import re
import queue
from jupyter_client import BlockingKernelClient

class PythonSandbox:
    def __init__(self, connection_file: str = 'connection.json'):
        """
        Initializes the connection to the sandboxed Jupyter kernel.
        """
        print("Connecting to Jupyter Kernel...")
        self.kc = BlockingKernelClient(connection_file=connection_file)
        self.kc.load_connection_file()
        self.kc.start_channels()
        self.kc.wait_for_ready(timeout=10)
        print("Kernel connected and ready!")
        
        # Regular expression to catch terminal color codes (ANSI escape sequences)
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        # setting init context
        print("Inserting agent tools")
        output = self.execute_code("""
from neo4j_db import Neo4jDBManager
from qdrant_db import QdrantDBManager
from embedder import Embedder

def get_similar_node_function(embedder:Embedder, vector_db:QdrantDBManager):
    def get_similar_nodes(name:str, description:str):
        embedding = embedder.embed_text(f"NAME={name}\\nDESCRIPTION={description}")
        similar_nodes = vector_db.search_points(
            collection_name='test',
            query_vector=embedding,
            limit=5,
            point_type="node"
        )

        node_info = []
        for node in similar_nodes[0].points:
            id = node.payload['_id']
            name = node.payload['name']
            description = node.payload['description']
            node_info.append({'id': id, 'name': name, 'description': description})

        return node_info
    return get_similar_nodes

def get_similar_relation_function(embedder:Embedder, vector_db:QdrantDBManager):
    def get_similar_relations(name:str, description:str):
        embedding = embedder.embed_text(f"NAME={name}\\nDESCRIPTION={description}")
        similar_relations = vector_db.search_points(
            collection_name='test',
            query_vector=embedding,
            limit=5,
            point_type="edge"
        )

        relation_info = []
        for relation in similar_nodes[0].points:
            name = node.payload['name']
            description = node.payload['description']
            relation_info.append({'name': name, 'description': description})

        return relation_info
    return get_similar_relations

graph_db = Neo4jDBManager()
vector_db = QdrantDBManager()
embedder = Embedder()

# functions the llm will use
get_similar_nodes = get_similar_node_function(embedder, vector_db)
get_similar_relations = get_similar_relation_function(embedder, vector_db)
execute_cypher = graph_db.execute_cypher
        """, timeout=30)

        print(output)
         

    def _strip_colors(self, text: str) -> str:
        """Removes ANSI color codes from the text so the LLM reads clean strings."""
        return self.ansi_escape.sub('', text)

    def execute_code(self, code_string: str, timeout:int=10) -> str:
        """
        Executes the code, listens for the output, and returns a clean, 
        colorless string ready to be sent back to the LLM.
        """
        # 1. Send the code to the Docker container
        self.kc.execute(code_string)
        
        output_parts = []
        
        # 2. Listen for the results on the IOPub channel
        while True:
            try:
                msg = self.kc.get_iopub_msg(timeout=timeout)
            except queue.Empty:
                output_parts.append("Error: Execution timed out. Possible infinite loop.")
                break

            msg_type = msg['header']['msg_type']
            content = msg['content']

            if msg_type == 'stream':
                # Captures standard print() outputs
                output_parts.append(content['text'])
                
            elif msg_type in ('execute_result', 'display_data'):
                # Captures the final returned variable or text representations
                if 'text/plain' in content.get('data', {}):
                    output_parts.append(content['data']['text/plain'] + "\n")
                    
            elif msg_type == 'error':
                # Captures Python tracebacks (which are heavily colorized by Jupyter)
                traceback_str = "\n".join(content.get('traceback', []))
                output_parts.append(f"Traceback Error:\n{traceback_str}\n")
                
            elif msg_type == 'status' and content.get('execution_state') == 'idle':
                # The kernel has finished executing this block
                break
                
        # 3. Combine everything and strip the colors
        raw_output = "".join(output_parts).strip()
        clean_output = self._strip_colors(raw_output)
        
        # If there is no output, let the LLM know it ran successfully
        return clean_output if clean_output else "Execution successful. No output."

    def close(self):
        """Safely shuts down the communication channels."""
        self.kc.stop_channels()
        print("Jupyter connection closed.")

    def clear_context(self) -> str:
        """
        Deletes the entire execution context (all user-defined variables and imports)
        from the running Jupyter kernel without shutting it down.
        """
        # Use the IPython magic command %reset with the -f (force) flag
        # to clear the namespace without asking for confirmation.
        return self.execute_code("%reset -f")