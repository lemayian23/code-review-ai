"""
Embedding generation tasks for Celery workers
"""
import time
from typing import List, Dict, Any, Optional
from uuid import UUID

import structlog
from celery import current_task
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from workers.celery_app import celery_app
from core.rag.embeddings import EmbeddingGenerator
from core.rag.chunking import CodeChunker
from db.models import CodeEmbedding, Repository
from observability.metrics import record_embedding_metrics

logger = structlog.get_logger(__name__)

# Database setup
from core.config import get_settings
settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True, name="workers.tasks.generate_embeddings.generate_repository_embeddings")
def generate_repository_embeddings(
    self,
    repository_id: str,
    repository_url: str,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Generate embeddings for a repository
    """
    start_time = time.time()
    repo_uuid = UUID(repository_id)
    
    try:
        logger.info(
            "Starting embedding generation",
            task_id=self.request.id,
            repository_id=repository_id,
            repository_url=repository_url
        )

        # Update task status
        self.update_state(state="PROGRESS", meta={"status": "Initializing embedding generation"})

        # Initialize components
        embedding_generator = EmbeddingGenerator()
        code_chunker = CodeChunker()

        # Get repository
        repository = get_repository(repo_uuid)
        if not repository:
            raise ValueError(f"Repository {repository_id} not found")

        # Update progress
        self.update_state(state="PROGRESS", meta={"status": "Fetching repository code"})

        # Fetch repository code (this would integrate with Git API)
        code_files = fetch_repository_code(repository_url)
        
        total_files = len(code_files)
        processed_files = 0
        total_embeddings = 0

        # Update progress
        self.update_state(state="PROGRESS", meta={"status": "Processing code files"})

        for file_path, code_content in code_files:
            try:
                # Chunk the code
                chunks = code_chunker.chunk_code(code_content, file_path)
                
                for chunk in chunks:
                    # Generate embedding
                    embedding = embedding_generator.generate_embedding(
                        text=chunk["content"],
                        metadata={
                            "file_path": file_path,
                            "function_name": chunk.get("function_name"),
                            "class_name": chunk.get("class_name"),
                            "line_start": chunk.get("line_start"),
                            "line_end": chunk.get("line_end"),
                            "language": chunk.get("language")
                        }
                    )

                    # Save embedding to database
                    save_embedding(
                        repository_id=repo_uuid,
                        file_path=file_path,
                        function_name=chunk.get("function_name"),
                        class_name=chunk.get("class_name"),
                        code_content=chunk["content"],
                        code_hash=chunk["hash"],
                        embedding_vector=embedding["vector"],
                        embedding_model=embedding["model"],
                        embedding_dimension=embedding["dimension"],
                        line_start=chunk.get("line_start"),
                        line_end=chunk.get("line_end"),
                        language=chunk.get("language"),
                        complexity_score=chunk.get("complexity_score")
                    )

                    total_embeddings += 1

                processed_files += 1
                
                # Update progress
                progress = (processed_files / total_files) * 100
                self.update_state(
                    state="PROGRESS", 
                    meta={
                        "status": f"Processing files ({processed_files}/{total_files})",
                        "progress": progress,
                        "processed_files": processed_files,
                        "total_files": total_files,
                        "total_embeddings": total_embeddings
                    }
                )

            except Exception as e:
                logger.warning(
                    "Failed to process file",
                    file_path=file_path,
                    error=str(e)
                )
                continue

        processing_time = time.time() - start_time

        # Record metrics
        record_embedding_metrics(
            processing_time=processing_time,
            files_processed=processed_files,
            embeddings_generated=total_embeddings,
            repository_id=repository_id
        )

        logger.info(
            "Embedding generation completed",
            task_id=self.request.id,
            repository_id=repository_id,
            processing_time=processing_time,
            files_processed=processed_files,
            embeddings_generated=total_embeddings
        )

        return {
            "status": "completed",
            "repository_id": repository_id,
            "files_processed": processed_files,
            "embeddings_generated": total_embeddings,
            "processing_time": processing_time
        }

    except Exception as e:
        logger.error(
            "Embedding generation failed",
            task_id=self.request.id,
            repository_id=repository_id,
            error=str(e)
        )

        return {
            "status": "failed",
            "error": str(e),
            "processing_time": time.time() - start_time
        }


@celery_app.task(bind=True, name="workers.tasks.generate_embeddings.update_file_embeddings")
def update_file_embeddings(
    self,
    repository_id: str,
    file_path: str,
    code_content: str
) -> Dict[str, Any]:
    """
    Update embeddings for a specific file
    """
    start_time = time.time()
    repo_uuid = UUID(repository_id)
    
    try:
        logger.info(
            "Updating file embeddings",
            task_id=self.request.id,
            repository_id=repository_id,
            file_path=file_path
        )

        # Initialize components
        embedding_generator = EmbeddingGenerator()
        code_chunker = CodeChunker()

        # Delete existing embeddings for this file
        delete_file_embeddings(repo_uuid, file_path)

        # Chunk the code
        chunks = code_chunker.chunk_code(code_content, file_path)
        
        total_embeddings = 0
        for chunk in chunks:
            # Generate embedding
            embedding = embedding_generator.generate_embedding(
                text=chunk["content"],
                metadata={
                    "file_path": file_path,
                    "function_name": chunk.get("function_name"),
                    "class_name": chunk.get("class_name"),
                    "line_start": chunk.get("line_start"),
                    "line_end": chunk.get("line_end"),
                    "language": chunk.get("language")
                }
            )

            # Save embedding
            save_embedding(
                repository_id=repo_uuid,
                file_path=file_path,
                function_name=chunk.get("function_name"),
                class_name=chunk.get("class_name"),
                code_content=chunk["content"],
                code_hash=chunk["hash"],
                embedding_vector=embedding["vector"],
                embedding_model=embedding["model"],
                embedding_dimension=embedding["dimension"],
                line_start=chunk.get("line_start"),
                line_end=chunk.get("line_end"),
                language=chunk.get("language"),
                complexity_score=chunk.get("complexity_score")
            )

            total_embeddings += 1

        processing_time = time.time() - start_time

        logger.info(
            "File embeddings updated",
            task_id=self.request.id,
            repository_id=repository_id,
            file_path=file_path,
            embeddings_generated=total_embeddings,
            processing_time=processing_time
        )

        return {
            "status": "completed",
            "file_path": file_path,
            "embeddings_generated": total_embeddings,
            "processing_time": processing_time
        }

    except Exception as e:
        logger.error(
            "File embedding update failed",
            task_id=self.request.id,
            repository_id=repository_id,
            file_path=file_path,
            error=str(e)
        )

        return {
            "status": "failed",
            "error": str(e),
            "processing_time": time.time() - start_time
        }


@celery_app.task(name="workers.tasks.generate_embeddings.cleanup_old_embeddings")
def cleanup_old_embeddings() -> Dict[str, Any]:
    """
    Clean up old embeddings based on TTL
    """
    try:
        logger.info("Starting embedding cleanup")

        # Get TTL from settings
        ttl_days = settings.CACHE_TTL_DAYS
        
        # Delete old embeddings
        deleted_count = delete_old_embeddings(ttl_days)

        logger.info(
            "Embedding cleanup completed",
            deleted_count=deleted_count,
            ttl_days=ttl_days
        )

        return {
            "status": "completed",
            "deleted_count": deleted_count,
            "ttl_days": ttl_days
        }

    except Exception as e:
        logger.error("Embedding cleanup failed", error=str(e))
        return {
            "status": "failed",
            "error": str(e)
        }


def get_repository(repository_id: UUID) -> Optional[Repository]:
    """Get repository by ID"""
    # This would be implemented with proper async database operations
    return None


def fetch_repository_code(repository_url: str) -> List[tuple]:
    """Fetch repository code files"""
    # This would integrate with Git API to fetch code files
    # For now, return mock data
    return [
        ("src/main.py", "def hello_world():\n    print('Hello, World!')"),
        ("src/utils.py", "def helper_function():\n    return True")
    ]


def save_embedding(
    repository_id: UUID,
    file_path: str,
    function_name: Optional[str],
    class_name: Optional[str],
    code_content: str,
    code_hash: str,
    embedding_vector: List[float],
    embedding_model: str,
    embedding_dimension: int,
    line_start: Optional[int],
    line_end: Optional[int],
    language: Optional[str],
    complexity_score: Optional[float]
) -> None:
    """Save embedding to database"""
    # This would be implemented with proper async database operations
    logger.info(
        "Saving embedding",
        repository_id=repository_id,
        file_path=file_path,
        function_name=function_name
    )


def delete_file_embeddings(repository_id: UUID, file_path: str) -> None:
    """Delete embeddings for a specific file"""
    # This would be implemented with proper async database operations
    logger.info(
        "Deleting file embeddings",
        repository_id=repository_id,
        file_path=file_path
    )


def delete_old_embeddings(ttl_days: int) -> int:
    """Delete old embeddings based on TTL"""
    # This would be implemented with proper async database operations
    logger.info("Deleting old embeddings", ttl_days=ttl_days)
    return 0
