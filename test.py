from agents import Chat
from embedder import Embedder
from knowledge_manager import KnowledgeManager

# models initialization
embedder = Embedder()
chat = Chat(
    on_cpu=False,
    verbose=False
)

kb_manager = KnowledgeManager(
    chat=chat,
    embedder=embedder,
    collection_name='test'
)

text_chunk = "Captain Sarah Jenkins, known for her boisterous laugh and love of vintage jazz, took command of the research vessel 'Oceanus' in 2021. She was born in Nova Scotia. In the summer of 2023, the Oceanus embarked on the Mariana Trench Expedition. During this perilous journey, her crew discovered a new species of bioluminescent squid. They officially named it 'Luxteuthis'. The expedition was heavily funded by the Global Oceanic Institute with a generous grant of $1.2 million. Jenkins later published a groundbreaking research paper about the squid in 2024, which was co-authored by Dr. Hiroshi Tanaka, the ship's lead marine biologist."
kb_manager.upload(text_chunk)
