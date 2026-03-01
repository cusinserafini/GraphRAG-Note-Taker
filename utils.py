import os
from typing import Union, List
from llama_index.core import SimpleDirectoryReader
from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.schema import TextNode

def chunk_markdown_files(file_paths: Union[str, List[str]]) -> List[TextNode]:
    """
    Chunks one or more markdown files into semantic nodes based on headers.
    This is highly effective for Markdown as it preserves the document structure.

    Args:
        file_paths: A single file path string, or a list of file path strings.

    Returns:
        A list of parsed markdown TextNodes (chunks), where each chunk contains
        the text and structural metadata associated with its original header section.
    """
    if isinstance(file_paths, str):
        file_paths = [file_paths]
        
    # Verify files exist
    valid_paths = []
    for path in file_paths:
        if not os.path.exists(path):
            print(f"Warning: File not found - {path}")
            continue
        valid_paths.append(path)
        
    if not valid_paths:
        return []

    # Load documents using LlamaIndex
    reader = SimpleDirectoryReader(input_files=valid_paths)
    documents = reader.load_data()
    
    # Parse into markdown nodes
    # MarkdownNodeParser splits documents intelligently by headers (H1, H2, etc.)
    parser = MarkdownNodeParser()
    nodes = parser.get_nodes_from_documents(documents)
    
    return nodes
