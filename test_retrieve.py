from embedder import Embedder
from agents import Chat
from knowledge_manager import KnowledgeManager
from retriever import Retriever

# Initialize models
embedder = Embedder()
chat = Chat(on_cpu=False, verbose=False, n_ctx=8192)

# Initialize KB
kb_manager = KnowledgeManager(
    chat=chat,
    embedder=embedder,
    collection_name='test'
)

# Initialize Retriever
retriever = Retriever(
    graph_db=kb_manager.graph_db,
    vector_db=kb_manager.vector_db,
    embedder=embedder,
    collection_name='test'
)

query = "Explain how Alan Turing, ARPANET, CERN, NASA, and the Apollo program collectively shaped modern technological infrastructure."
print("QUERY:\n", query)

context = retriever.retrieve(query, top_k=5, depth=1, agentic=False, chat=None)

print("\nRetrieved Context:")
print(context)

messages = [
    {"role": "system", "content": "Answer using ONLY the provided context. If not present, say 'Not found in context.'"},
    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
]

answer = chat.ask(messages, streaming=False)
print("\nLLM Answer:")
print(answer)
# for token in answer:
#     print(token, end="", flush=True)