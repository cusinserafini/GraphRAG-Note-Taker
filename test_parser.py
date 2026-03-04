from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import MarkdownNodeParser

reader = SimpleDirectoryReader(input_files=['markdown_example.md'])
documents = reader.load_data()
parser = MarkdownNodeParser()
nodes = parser.get_nodes_from_documents(documents)

for i, node in enumerate(nodes):
    print(f"--- Node {i} ---")
    print(f"Text: {repr(node.text)}")
    print(f"Metadata: {node.metadata}")
