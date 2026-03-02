from utils import chunk_markdown_files
from agents import Chat
from embedder import Embedder
from knowledge_manager import KnowledgeManager

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

file_name = "markdown_example.md"
kb_manager.upload(file_name)
