from agents import Chat
from embedder import Embedder
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
    collection_name='test',
    agentic=True
)

# Test queries
# ==============================
# LEVEL 1 — Direct Fact Retrieval
# ==============================

level_1_queries = [
    "Where was J. Oppenheimer born?",
    "In which year was Apple founded?",
    "Who co-authored the research paper about Luxteuthis?",
    "Which city is a global leader in robotics and electronics?",
    "Who directed the Los Alamos Laboratory?",
    "Who took command of the Oceanus in 2021?",
    "What expedition discovered Luxteuthis?",
    "Who is the British designer mentioned in the text?"
]


# ==============================
# LEVEL 2 — Relationship Retrieval
# ==============================

level_2_queries = [
    "Who funded the Mariana Trench Expedition?",
    "Which organization funded scientific research about bioluminescent squid?",
    "Who worked under Steve Jobs?",
    "Which project is compared to the Manhattan Project?",
    "Who published a research paper in 2024?",
    "Which vessel embarked on the Mariana Trench Expedition?"
]


# ==============================
# LEVEL 3 — Property Filtering
# ==============================

level_3_queries = [
    "Which person was born in Nova Scotia?",
    "Which scientist won two Nobel Prizes?",
    "Which company generated 383 billion USD in revenue?",
    "Which historical figure was born in 1904?",
    "Which city is the capital of France?",
    "Which designer emphasized simplicity and honesty in materials?"
]


# ==============================
# LEVEL 4 — Multi-Hop Reasoning
# ==============================

level_4_queries = [
    "Who funded the expedition led by Captain Sarah Jenkins?",
    "Which scientist led a secret laboratory during World War II?",
    "Which modern tech company is metaphorically linked to the Manhattan Project?",
    "Who collaborated with the lead marine biologist?",
    "Which people are connected to Apple?",
    "Which historical project is linked philosophically to Silicon Valley?"
]


# ==============================
# LEVEL 5 — Cross-Chunk Linking
# ==============================

level_5_queries = [
    "What connects Oppenheimer and Project Purple?",
    "Which organization did Jony Ive work at and where is it located?",
    "Which individuals are associated with the Atomic Age?",
    "Which cities are described as innovation hubs across time?",
    "Which scientists contributed to physics before the modern computing era?"
]


# ==============================
# LEVEL 6 — Entity Resolution Stress Tests
# ==============================

level_6_queries = [
    "Who worked under Steve Jobs at Apple?",
    "Who led a secret research laboratory?",
    "Which project harnessed atomic power?",
    "Which project harnessed microprocessor power?",
    "Which Apple employee focused on aesthetics?",
    "Who funded a GraphRAG company?",
    "What is GraphRAG?",
    "Is Project Purple related to the Manhattan Project?"
]


# ==============================
# LEVEL 7 — Failure / Hallucination Tests
# ==============================

level_7_queries = [
    "What is Steve Jobs' birth date?",
    "Where was Marie Curie born?",
    "What was Apple's revenue in 2023?",
    "Who discovered Luxteuthis alone?",
    "Which Nobel Prize did Oppenheimer win?"
]


# ==============================
# ALL QUERIES TOGETHER
# ==============================

all_queries = (
    level_1_queries +
    level_2_queries +
    level_3_queries +
    level_4_queries +
    level_5_queries +
    level_6_queries +
    level_7_queries
)

# for query in level_7_queries:
query = "Which organization did Jony Ive work at and where is it located?"
print("\n==============================")
print("QUERY:", query)

context = retriever.retrieve(query, top_k=5, depth=3, chat=chat)

print("\nRetrieved Context:")
print(context)

messages = [
    {"role": "system", "content": "Answer using ONLY the provided context. If not present, say 'Not found in context.'"},
    {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
]

answer = chat.ask(messages)
print("\nLLM Answer:")
print(answer)
