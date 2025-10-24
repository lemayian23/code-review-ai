"""
Code analysis tasks for Celery workers
"""
import time
from typing import List, Dict, Any
from uuid import UUID

import structlog
from celery import current_task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from workers.celery_app import celery_app
from core.llm.client import LLMClient
from core.rag.retriever import ContextRetriever
from core.patterns.rules import PatternMatcher
from core.llm.cache import LLMCache
from db.models import CodeReview, User, Repository
from observability.metrics import record_analysis_metrics

logger = structlog.get_logger(__name__)

# Database setup
from core.config import get_settings
settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True, name="workers.tasks.analyze_code.analyze_code_task")
def analyze_code_task(
    self,
    review_id: str,
    diff_content: str,
    file_paths: List[str],
    context_files: List[str],
    repository_url: str
) -> Dict[str, Any]:
    """
    Analyze code changes and generate review suggestions
    """
    start_time = time.time()
    review_uuid = UUID(review_id)
    
    try:
        logger.info(
            "Starting code analysis task",
            task_id=self.request.id,
            review_id=review_id,
            repository_url=repository_url
        )

        # Update task status
        self.update_state(state="PROGRESS", meta={"status": "Initializing analysis"})

        # Initialize components
        llm_client = LLMClient()
        context_retriever = ContextRetriever()
        pattern_matcher = PatternMatcher()
        cache = LLMCache()

        # Get or create repository
        repository = get_or_create_repository(repository_url)

        # Update progress
        self.update_state(state="PROGRESS", meta={"status": "Retrieving context"})

        # Retrieve relevant context
        context_docs = context_retriever.retrieve_context(
            diff_content=diff_content,
            file_paths=file_paths,
            repository_id=repository.id
        )

        # Update progress
        self.update_state(state="PROGRESS", meta={"status": "Running pattern matching"})

        # Run pattern-based analysis
        pattern_suggestions = pattern_matcher.analyze_code(
            diff_content=diff_content,
            file_paths=file_paths
        )

        # Update progress
        self.update_state(state="PROGRESS", meta={"status": "Generating LLM analysis"})

        # Generate LLM-based analysis
        llm_suggestions = llm_client.analyze_code(
            diff_content=diff_content,
            context_docs=context_docs,
            file_paths=file_paths,
            repository_url=repository_url
        )

        # Combine and rank suggestions
        all_suggestions = pattern_suggestions + llm_suggestions
        ranked_suggestions = rank_suggestions(all_suggestions)

        # Calculate metrics
        processing_time = time.time() - start_time
        cost_estimate = calculate_cost_estimate(llm_suggestions)
        confidence_scores = [s.get("confidence", 0.5) for s in ranked_suggestions]

        # Update progress
        self.update_state(state="PROGRESS", meta={"status": "Saving results"})

        # Save results to database
        save_analysis_results(
            review_id=review_uuid,
            suggestions=ranked_suggestions,
            confidence_scores=confidence_scores,
            processing_time=processing_time,
            cost_estimate=cost_estimate,
            token_usage=llm_client.get_token_usage()
        )

        # Record metrics
        record_analysis_metrics(
            processing_time=processing_time,
            suggestion_count=len(ranked_suggestions),
            cost_estimate=cost_estimate,
            cache_hit_rate=cache.get_hit_rate()
        )

        logger.info(
            "Code analysis completed",
            task_id=self.request.id,
            review_id=review_id,
            processing_time=processing_time,
            suggestion_count=len(ranked_suggestions),
            cost_estimate=cost_estimate
        )

        return {
            "status": "completed",
            "suggestions": ranked_suggestions,
            "confidence_scores": confidence_scores,
            "processing_time": processing_time,
            "cost_estimate": cost_estimate,
            "suggestion_count": len(ranked_suggestions)
        }

    except Exception as e:
        logger.error(
            "Code analysis failed",
            task_id=self.request.id,
            review_id=review_id,
            error=str(e)
        )

        # Update review status to failed
        update_review_status(review_uuid, "failed", error=str(e))

        return {
            "status": "failed",
            "error": str(e),
            "processing_time": time.time() - start_time
        }


def get_or_create_repository(repository_url: str) -> Repository:
    """Get or create repository record"""
    # This would be implemented with proper async database operations
    # For now, return a mock repository
    return Repository(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        url=repository_url,
        name="test-repo",
        owner="test-owner"
    )


def rank_suggestions(suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank suggestions by confidence and importance"""
    # Sort by confidence score (descending)
    return sorted(suggestions, key=lambda x: x.get("confidence", 0), reverse=True)


def calculate_cost_estimate(suggestions: List[Dict[str, Any]]) -> float:
    """Calculate cost estimate for analysis"""
    # Simple cost calculation based on suggestion count
    base_cost = 0.01  # Base cost per analysis
    suggestion_cost = 0.001  # Cost per suggestion
    return base_cost + (len(suggestions) * suggestion_cost)


def save_analysis_results(
    review_id: UUID,
    suggestions: List[Dict[str, Any]],
    confidence_scores: List[float],
    processing_time: float,
    cost_estimate: float,
    token_usage: Dict[str, int]
) -> None:
    """Save analysis results to database"""
    # This would be implemented with proper async database operations
    logger.info(
        "Saving analysis results",
        review_id=review_id,
        suggestion_count=len(suggestions),
        processing_time=processing_time
    )


def update_review_status(review_id: UUID, status: str, error: str = None) -> None:
    """Update review status in database"""
    # This would be implemented with proper async database operations
    logger.info(
        "Updating review status",
        review_id=review_id,
        status=status,
        error=error
    )
