from embedder import Embedder
from agents import Chat
from knowledge_manager import KnowledgeManager

import logging

logging.getLogger("qdrant_client").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("neo4j").setLevel(logging.ERROR)

# models initialization
embedder = Embedder()
chat = Chat(on_cpu=False, verbose=False, n_ctx=8192)

kb_manager = KnowledgeManager(
    chat=chat,
    embedder=embedder,
    collection_name='test'
)

file_name = "data\markdown_example.md"
kb_manager.upload(file_name)
