"""
Embedding generation for Code Review AI
"""
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import structlog
import openai
from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class EmbeddingResult:
    """Embedding result data structure"""
    vector: List[float]
    model: str
    dimension: int
    text_hash: str
    metadata: Dict[str, Any]


class EmbeddingGenerator:
    """Generate embeddings for code and text"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL_EMBEDDINGS
        self.dimension = self._get_model_dimension()

    def _get_model_dimension(self) -> int:
        """Get embedding dimension for model"""
        model_dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536
        }
        return model_dimensions.get(self.model, 1536)

    async def generate_embedding(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> EmbeddingResult:
        """
        Generate embedding for text
        """
        try:
            logger.debug("Generating embedding", model=self.model, text_length=len(text))
            
            # Generate text hash for deduplication
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            
            # Call OpenAI API
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=text
            )
            
            embedding_vector = response.data[0].embedding
            
            result = EmbeddingResult(
                vector=embedding_vector,
                model=self.model,
                dimension=self.dimension,
                text_hash=text_hash,
                metadata=metadata or {}
            )
            
            logger.debug("Embedding generated", dimension=len(embedding_vector))
            return result
            
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise

    async def generate_batch_embeddings(
        self,
        texts: List[str],
        metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts
        """
        try:
            logger.debug("Generating batch embeddings", count=len(texts))
            
            # Call OpenAI API for batch
            response = await self.openai_client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            results = []
            for i, embedding_data in enumerate(response.data):
                text = texts[i]
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else {}
                
                result = EmbeddingResult(
                    vector=embedding_data.embedding,
                    model=self.model,
                    dimension=self.dimension,
                    text_hash=text_hash,
                    metadata=metadata
                )
                results.append(result)
            
            logger.debug("Batch embeddings generated", count=len(results))
            return results
            
        except Exception as e:
            logger.error("Batch embedding generation failed", error=str(e))
            raise

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        """
        try:
            import numpy as np
            
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error("Similarity calculation failed", error=str(e))
            return 0.0

    def find_similar_embeddings(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[EmbeddingResult],
        threshold: float = 0.7,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find similar embeddings based on cosine similarity
        """
        try:
            similarities = []
            
            for candidate in candidate_embeddings:
                similarity = self.calculate_similarity(query_embedding, candidate.vector)
                
                if similarity >= threshold:
                    similarities.append({
                        "embedding": candidate,
                        "similarity": similarity,
                        "metadata": candidate.metadata
                    })
            
            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Return top-k results
            return similarities[:top_k]
            
        except Exception as e:
            logger.error("Similar embedding search failed", error=str(e))
            return []

    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get embedding generation statistics"""
        return {
            "model": self.model,
            "dimension": self.dimension,
            "supported_models": [
                "text-embedding-3-small",
                "text-embedding-3-large", 
                "text-embedding-ada-002"
            ]
        }
