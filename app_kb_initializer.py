from agents import Chat
from embedder import Embedder
from knowledge_manager import KnowledgeManager

print("> Knowledge base initialization")
embedder = Embedder()
chat = Chat(on_cpu=False, verbose=False)
kb_manager = KnowledgeManager(
    chat=chat,
    embedder=embedder,
    collection_name='test'
)
print("Model loading finished")