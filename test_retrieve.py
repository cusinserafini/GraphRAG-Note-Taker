from agents import Chat
from embedder import Embedder
from knowledge_manager import KnowledgeManager
from retriever import Retriever

# Initialize models
embedder = Embedder()
chat = Chat(
    on_cpu=False,
    verbose=False
)

# Initialize KB
kb_manager = KnowledgeManager(
    chat=chat,
    embedder=embedder,
    collection_name='test'
)

# Upload knowledge
text_chunk = """
Captain Sarah Jenkins, known for her boisterous laugh and love of vintage jazz,
took command of the research vessel 'Oceanus' in 2021.
She was born in Nova Scotia.
In the summer of 2023, the Oceanus embarked on the Mariana Trench Expedition.
During this perilous journey, her crew discovered a new species of bioluminescent squid.
They officially named it 'Luxteuthis'.
The expedition was heavily funded by the Global Oceanic Institute
with a generous grant of $1.2 million.
Jenkins later published a groundbreaking research paper about the squid in 2024,
which was co-authored by Dr. Hiroshi Tanaka,
the ship's lead marine biologist.
"""

kb_manager.upload(text_chunk)

# Initialize Retriever
retriever = Retriever(
    graph_db=kb_manager.graph_db,
    vector_db=kb_manager.vector_db,
    embedder=embedder,
    collection_name='test'
)

# Test queries
queries = [
    "Who funded the expedition?",
    "Who commanded Oceanus?",
    "Who co-authored the research paper?",
    "Where was Sarah Jenkins born?"
]

for query in queries:
    print("\n==============================")
    print("QUERY:", query)

    context = retriever.retrieve(query, depth=2)

    print("\nRetrieved Context:")
    print(context)

    # Generate final answer
    messages = [
        {"role": "system", "content": "Answer using ONLY the provided context."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
    ]

    answer = chat.ask(messages)
    print("\nLLM Answer:")
    print(answer)