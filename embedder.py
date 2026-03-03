import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer

class Embedder:
    """
    A class to generate embeddings using Hugging Face models via sentence-transformers.
    """
    def __init__(self, model_name: str = "Qwen/Qwen3-Embedding-0.6B", dimensions: int = 1024):
    # def __init__(self, model_name: str = "google/embeddinggemma-300m", dimensions: int = 768):
        """
        Initializes the sentence transformer model.
        
        Args:
            model_name (str): The HuggingFace model ID.
            dimensions (int): The target output embedding dimension.
        """
        self.model_name = model_name
        self.dimensions = dimensions
        
        print(f"Initializing Embedder with model '{self.model_name}'...")
        try:
            # Some modern models support Matryoshka Representation Learning and accept truncate_dim
            self.model = SentenceTransformer(model_name, device="cuda")
            # self.model = SentenceTransformer(model_name, truncate_dim=dimensions, device="cpu")
        except Exception as e:
            print(f"Warning: Could not load '{model_name}' with native truncate_dim. Loading normally... (Error: {e})")
            try:
                self.model = SentenceTransformer(model_name, device="cpu")
            except Exception as inner_e:
                # Fallback if the requested model doesn't exist on HuggingFace Hub or fails to download
                fallback = "all-MiniLM-L6-v2"
                print(f"Failed to load '{model_name}'. Falling back to '{fallback}'. (Error: {inner_e})")
                self.model = SentenceTransformer(fallback, device="cpu")
                self.model_name = fallback
                self.dimensions = 384

    def embed_text(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Embeds a string or a list of strings into vectors.
        """
        embeddings = self.model.encode(text, convert_to_numpy=True)
        
        # Manually truncate if the model did not natively support truncate_dim
        # or if it ignores it.
        if len(embeddings.shape) == 1:
            return embeddings[:self.dimensions]
        return embeddings[:, :self.dimensions]