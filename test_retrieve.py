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
text_chunk = "Captain Sarah Jenkins, known for her boisterous laugh and love of vintage jazz, took command of the research vessel 'Oceanus' in 2021. She was born in Nova Scotia. In the summer of 2023, the Oceanus embarked on the Mariana Trench Expedition. During this perilous journey, her crew discovered a new species of bioluminescent squid. They officially named it 'Luxteuthis'. The expedition was heavily funded by the Global Oceanic Institute with a generous grant of $1.2 million. Jenkins later published a groundbreaking research paper about the squid in 2024, which was co-authored by Dr. Hiroshi Tanaka, the ship's lead marine biologist."
kb_manager.upload(text_chunk)

# documents = [

# """
# Captain Sarah Jenkins took command of the research vessel Oceanus in 2021.
# She was born in Nova Scotia in 1980.
# Oceanus is owned by Blue Horizon Shipping.
# """,

# """
# In 2023, Oceanus embarked on the Mariana Trench Expedition.
# The expedition was funded by the Global Oceanic Institute
# with a grant of $1.2 million.
# """,

# """
# During the expedition, the crew discovered a bioluminescent squid.
# The species was named Luxteuthis.
# The naming was approved by the International Marine Taxonomy Council.
# """,

# """
# Sarah Jenkins published a research paper in 2024 about Luxteuthis.
# It was co-authored by Dr. Hiroshi Tanaka.
# Tanaka is a marine biologist from Kyoto University.
# """,

# """
# The Global Oceanic Institute is headquartered in London.
# It frequently collaborates with Kyoto University.
# """
# ]

# for doc in documents:
#     kb_manager.upload(doc)

# Initialize Retriever
retriever = Retriever(
    graph_db=kb_manager.graph_db,
    vector_db=kb_manager.vector_db,
    embedder=embedder,
    collection_name='test'
)

# Test queries
queries = [

    # 2-hop: Expedition → funded by → organization → location
    "Where is the organization that funded the Mariana Trench Expedition headquartered?",

    # 3-hop reasoning
    "Which university is affiliated with the co-author of the Luxteuthis paper?",

    # Temporal reasoning
    "How many years after taking command did Jenkins publish her paper?",

    # Multi-entity linking
    "Which institution is connected to both the expedition funder and the paper co-author?",

    # Indirect reasoning
    "Who approved the species discovered by the Oceanus crew?",

    # Entity disambiguation
    "Who owns the ship commanded by Sarah Jenkins?"
]

for query in queries:
    print("\n==============================")
    print("QUERY:", query)

    context = retriever.retrieve(query, depth=3)

    print("\nRetrieved Context:")
    print(context)

    messages = [
        {"role": "system", "content": "Answer using ONLY the provided context. If not present, say 'Not found in context.'"},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
    ]

    answer = chat.ask(messages)
    print("\nLLM Answer:")
    print(answer)
