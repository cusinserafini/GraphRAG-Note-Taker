from utils import chunk_markdown_files
from agents import Chat
from embedder import Embedder
from knowledge_manager import KnowledgeManager

import logging

logging.getLogger("qdrant_client").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)

embedder = None
chat = None

# models initialization
embedder = Embedder()
chat = Chat(on_cpu=False, verbose=False, n_ctx=4096)

kb_manager = KnowledgeManager(
    chat=chat,
    embedder=embedder,
    collection_name='test'
)

file_name = "examples\markdown_example.md"
kb_manager.upload(file_name)
