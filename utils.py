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
    
    # Post-process to merge short chunks (e.g. standalone headers) with the next chunk
    # Adjust this character threshold as needed
    MIN_CHUNK_LENGTH = 50
    
    merged_nodes = []
    i = 0
    while i < len(nodes):
        current_node = nodes[i]
        
        # If the node is too short and there's a next node, merge it with the next one
        while len(current_node.text.strip()) < MIN_CHUNK_LENGTH and i + 1 < len(nodes):
            next_node = nodes[i + 1]
            
            # Combine the text
            merged_text = current_node.text + "\n" + next_node.text
            
            # Create a new merged node inheriting the current node's metadata (or a mix)
            # We keep the current node's header_path if both have it, as the current is the higher/earlier header
            merged_metadata = current_node.metadata.copy()
            if 'header_path' in next_node.metadata and len(next_node.metadata['header_path']) > len(merged_metadata.get('header_path', '')):
                merged_metadata['header_path'] = next_node.metadata['header_path']
                
            current_node = TextNode(
                text=merged_text,
                metadata=merged_metadata
            )
            i += 1
            
        merged_nodes.append(current_node)
        i += 1
        
    return merged_nodes
