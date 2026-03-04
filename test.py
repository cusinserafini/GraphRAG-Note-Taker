from agents import Chat
from embedder import Embedder
from knowledge_manager import KnowledgeManager

import logging

logging.getLogger("qdrant_client").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)

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
