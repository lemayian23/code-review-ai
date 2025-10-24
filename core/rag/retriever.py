"""
Context retrieval for RAG system
"""
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import structlog
from core.rag.embeddings import EmbeddingGenerator
from core.rag.chunking import CodeChunker
from observability.metrics import record_retrieval_metrics

logger = structlog.get_logger(__name__)


@dataclass
class RetrievedDocument:
    """Retrieved document data structure"""
    content: str
    file_path: str
    function_name: Optional[str]
    class_name: Optional[str]
    line_start: Optional[int]
    line_end: Optional[int]
    similarity_score: float
    metadata: Dict[str, Any]


class ContextRetriever:
    """Retrieve relevant context for code analysis"""
    
    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.code_chunker = CodeChunker()
        self.retrieval_cache = {}

    async def retrieve_context(
        self,
        diff_content: str,
        file_paths: List[str],
        repository_id: str,
        max_documents: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[RetrievedDocument]:
        """
        Retrieve relevant context documents for code analysis
        """
        start_time = time.time()
        
        try:
            logger.info(
                "Starting context retrieval",
                file_paths=file_paths,
                repository_id=repository_id,
                max_documents=max_documents
            )

            # Generate query embedding from diff content
            query_embedding = await self.embedding_generator.generate_embedding(
                text=diff_content,
                metadata={"type": "query", "file_paths": file_paths}
            )

            # Retrieve relevant documents
            documents = await self._retrieve_documents(
                query_embedding=query_embedding.vector,
                repository_id=repository_id,
                file_paths=file_paths,
                max_documents=max_documents,
                similarity_threshold=similarity_threshold
            )

            processing_time = time.time() - start_time

            # Record metrics
            record_retrieval_metrics(
                processing_time=processing_time,
                documents_retrieved=len(documents),
                repository_id=repository_id
            )

            logger.info(
                "Context retrieval completed",
                documents_retrieved=len(documents),
                processing_time=processing_time
            )

            return documents

        except Exception as e:
            logger.error("Context retrieval failed", error=str(e))
            raise

    async def _retrieve_documents(
        self,
        query_embedding: List[float],
        repository_id: str,
        file_paths: List[str],
        max_documents: int,
        similarity_threshold: float
    ) -> List[RetrievedDocument]:
        """Retrieve documents from vector database"""
        try:
            # This would integrate with Weaviate or similar vector database
            # For now, return mock data
            documents = []
            
            # Mock retrieval logic
            mock_documents = self._get_mock_documents(repository_id, file_paths)
            
            for doc_data in mock_documents:
                # Calculate similarity (mock)
                similarity = self._calculate_mock_similarity(query_embedding, doc_data)
                
                if similarity >= similarity_threshold:
                    document = RetrievedDocument(
                        content=doc_data["content"],
                        file_path=doc_data["file_path"],
                        function_name=doc_data.get("function_name"),
                        class_name=doc_data.get("class_name"),
                        line_start=doc_data.get("line_start"),
                        line_end=doc_data.get("line_end"),
                        similarity_score=similarity,
                        metadata=doc_data.get("metadata", {})
                    )
                    documents.append(document)
            
            # Sort by similarity and limit results
            documents.sort(key=lambda x: x.similarity_score, reverse=True)
            return documents[:max_documents]
            
        except Exception as e:
            logger.error("Document retrieval failed", error=str(e))
            return []

    def _get_mock_documents(self, repository_id: str, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Get mock documents for testing"""
        return [
            {
                "content": "def calculate_total(items):\n    return sum(item.price for item in items)",
                "file_path": "src/calculations.py",
                "function_name": "calculate_total",
                "class_name": None,
                "line_start": 10,
                "line_end": 12,
                "metadata": {"language": "python", "complexity": 0.3}
            },
            {
                "content": "class UserService:\n    def __init__(self):\n        self.db = Database()",
                "file_path": "src/services.py",
                "function_name": "__init__",
                "class_name": "UserService",
                "line_start": 1,
                "line_end": 3,
                "metadata": {"language": "python", "complexity": 0.1}
            }
        ]

    def _calculate_mock_similarity(self, query_embedding: List[float], doc_data: Dict[str, Any]) -> float:
        """Calculate mock similarity score"""
        # Simple mock similarity based on content length and keywords
        content = doc_data["content"]
        base_similarity = 0.5
        
        # Boost similarity for matching file paths
        if any(keyword in content.lower() for keyword in ["def", "class", "function"]):
            base_similarity += 0.2
        
        # Boost for longer, more detailed content
        if len(content) > 100:
            base_similarity += 0.1
        
        return min(base_similarity, 1.0)

    async def retrieve_similar_functions(
        self,
        function_code: str,
        repository_id: str,
        max_functions: int = 5
    ) -> List[RetrievedDocument]:
        """Retrieve similar functions for pattern matching"""
        try:
            logger.debug("Retrieving similar functions", repository_id=repository_id)
            
            # Generate embedding for function code
            function_embedding = await self.embedding_generator.generate_embedding(
                text=function_code,
                metadata={"type": "function", "repository_id": repository_id}
            )
            
            # Retrieve similar functions
            similar_functions = await self._retrieve_documents(
                query_embedding=function_embedding.vector,
                repository_id=repository_id,
                file_paths=[],
                max_documents=max_functions,
                similarity_threshold=0.6
            )
            
            # Filter for functions only
            function_docs = [
                doc for doc in similar_functions
                if doc.function_name is not None
            ]
            
            logger.debug("Similar functions retrieved", count=len(function_docs))
            return function_docs
            
        except Exception as e:
            logger.error("Similar function retrieval failed", error=str(e))
            return []

    async def retrieve_code_patterns(
        self,
        pattern_type: str,
        repository_id: str,
        max_patterns: int = 10
    ) -> List[RetrievedDocument]:
        """Retrieve code patterns for analysis"""
        try:
            logger.debug("Retrieving code patterns", pattern_type=pattern_type, repository_id=repository_id)
            
            # Generate embedding for pattern type
            pattern_embedding = await self.embedding_generator.generate_embedding(
                text=f"code pattern: {pattern_type}",
                metadata={"type": "pattern", "pattern_type": pattern_type}
            )
            
            # Retrieve pattern documents
            patterns = await self._retrieve_documents(
                query_embedding=pattern_embedding.vector,
                repository_id=repository_id,
                file_paths=[],
                max_documents=max_patterns,
                similarity_threshold=0.5
            )
            
            logger.debug("Code patterns retrieved", count=len(patterns))
            return patterns
            
        except Exception as e:
            logger.error("Code pattern retrieval failed", error=str(e))
            return []

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get retrieval statistics"""
        return {
            "cache_size": len(self.retrieval_cache),
            "embedding_model": self.embedding_generator.model,
            "embedding_dimension": self.embedding_generator.dimension
        }
