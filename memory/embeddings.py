"""Embedding generation for semantic search"""

import logging
from typing import List

from config import Config

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for memory items"""

    def __init__(self, config: Config):
        self.config = config
        self.model = None
        self._initialize_model()

    def _initialize_model(self):
        """Initialize the embedding model"""
        try:
            # Try to use sentence-transformers if available
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(self.config.embeddings.model)
                self.embedding_type = "sentence_transformers"
                logger.info(f"Loaded sentence-transformers model: {self.config.embeddings.model}")
            except ImportError:
                logger.warning("sentence-transformers not available, using dummy embeddings")
                self.embedding_type = "dummy"

        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            self.embedding_type = "dummy"

    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a text string"""
        if not text.strip():
            return self._get_zero_embedding()

        try:
            if self.embedding_type == "sentence_transformers" and self.model:
                embedding = self.model.encode(text).tolist()
                return embedding
            else:
                # Dummy embedding for development
                return self._generate_dummy_embedding(text)

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return self._generate_dummy_embedding(text)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self.embedding_type == "sentence_transformers" and self.model:
            try:
                embeddings = self.model.encode(texts).tolist()
                return embeddings
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                return [self.generate_embedding(text) for text in texts]
        else:
            return [self.generate_embedding(text) for text in texts]

    def _generate_dummy_embedding(self, text: str) -> List[float]:
        """Generate a dummy embedding for development/testing"""
        # Simple hash-based dummy embedding
        hash_val = hash(text.lower())
        dimension = self.config.embeddings.dimension

        # Create a pseudo-random but deterministic embedding
        embedding = []
        for i in range(dimension):
            val = ((hash_val + i) * 9973) % 2147483647  # Large prime
            normalized = (val / 2147483647.0) * 2.0 - 1.0  # Normalize to [-1, 1]
            embedding.append(normalized)

        return embedding

    def _get_zero_embedding(self) -> List[float]:
        """Return zero embedding for empty text"""
        return [0.0] * self.config.embeddings.dimension

    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Compute cosine similarity between two embeddings"""
        if len(embedding1) != len(embedding2):
            return 0.0

        # Cosine similarity
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2, strict=False))
        magnitude1 = sum(a * a for a in embedding1) ** 0.5
        magnitude2 = sum(b * b for b in embedding2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
