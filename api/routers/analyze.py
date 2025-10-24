"""
Code analysis endpoints
"""
import asyncio
from typing import Dict, Any, List
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, get_db
from core.llm.client import LLMClient
from core.rag.retriever import ContextRetriever
from core.patterns.rules import PatternMatcher
from workers.tasks.analyze_code import analyze_code_task
from db.models import User, CodeReview

logger = structlog.get_logger(__name__)
router = APIRouter()


class AnalysisRequest(BaseModel):
    """Request model for code analysis"""
    repository_url: str = Field(..., description="Repository URL")
    pull_request_id: int = Field(..., description="Pull request ID")
    diff_content: str = Field(..., description="Git diff content")
    base_commit: str = Field(..., description="Base commit hash")
    head_commit: str = Field(..., description="Head commit hash")
    file_paths: List[str] = Field(default=[], description="List of changed file paths")
    context_files: List[str] = Field(default=[], description="Additional context files")


class AnalysisResponse(BaseModel):
    """Response model for code analysis"""
    review_id: UUID = Field(..., description="Unique review ID")
    status: str = Field(..., description="Analysis status")
    suggestions: List[Dict[str, Any]] = Field(..., description="Code review suggestions")
    confidence_scores: List[float] = Field(..., description="Confidence scores for suggestions")
    processing_time: float = Field(..., description="Processing time in seconds")
    cost_estimate: float = Field(..., description="Estimated cost in USD")


@router.post("/", response_model=AnalysisResponse)
async def analyze_code(
    request: AnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AnalysisResponse:
    """
    Analyze code changes and generate review suggestions
    """
    try:
        logger.info(
            "Starting code analysis",
            user_id=current_user.id,
            repository_url=request.repository_url,
            pr_id=request.pull_request_id
        )

        # Create review record
        review = CodeReview(
            user_id=current_user.id,
            repository_url=request.repository_url,
            pull_request_id=request.pull_request_id,
            status="processing",
            diff_content=request.diff_content,
            base_commit=request.base_commit,
            head_commit=request.head_commit,
        )
        db.add(review)
        await db.commit()
        await db.refresh(review)

        # Queue analysis task
        task = analyze_code_task.delay(
            review_id=str(review.id),
            diff_content=request.diff_content,
            file_paths=request.file_paths,
            context_files=request.context_files,
            repository_url=request.repository_url
        )

        # Update review with task ID
        review.task_id = task.id
        await db.commit()

        return AnalysisResponse(
            review_id=review.id,
            status="processing",
            suggestions=[],
            confidence_scores=[],
            processing_time=0.0,
            cost_estimate=0.0
        )

    except Exception as e:
        logger.error("Code analysis failed", error=str(e))
        raise HTTPException(status_code=500, detail="Analysis failed")


@router.get("/{review_id}")
async def get_analysis_result(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AnalysisResponse:
    """
    Get analysis result by review ID
    """
    review = await db.get(CodeReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return AnalysisResponse(
        review_id=review.id,
        status=review.status,
        suggestions=review.suggestions or [],
        confidence_scores=review.confidence_scores or [],
        processing_time=review.processing_time or 0.0,
        cost_estimate=review.cost_estimate or 0.0
    )


@router.websocket("/{review_id}/stream")
async def stream_analysis(
    websocket: WebSocket,
    review_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Stream analysis results in real-time
    """
    await websocket.accept()
    
    try:
        # Get review from database
        db = next(get_db())
        review = await db.get(CodeReview, review_id)
        if not review or review.user_id != current_user.id:
            await websocket.close(code=403, reason="Access denied")
            return

        # Stream analysis progress
        while review.status == "processing":
            await websocket.send_json({
                "type": "progress",
                "status": review.status,
                "message": "Analyzing code changes..."
            })
            
            # Check for updates
            await db.refresh(review)
            await asyncio.sleep(1)

        # Send final results
        await websocket.send_json({
            "type": "complete",
            "status": review.status,
            "suggestions": review.suggestions or [],
            "confidence_scores": review.confidence_scores or [],
            "processing_time": review.processing_time or 0.0,
            "cost_estimate": review.cost_estimate or 0.0
        })

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", review_id=review_id)
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        await websocket.close(code=500, reason="Internal error")


@router.post("/{review_id}/regenerate")
async def regenerate_analysis(
    review_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> AnalysisResponse:
    """
    Regenerate analysis with updated parameters
    """
    review = await db.get(CodeReview, review_id)
    if not review or review.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Review not found")

    # Reset review status
    review.status = "processing"
    review.suggestions = None
    review.confidence_scores = None
    await db.commit()

    # Queue new analysis
    task = analyze_code_task.delay(
        review_id=str(review.id),
        diff_content=review.diff_content,
        file_paths=[],
        context_files=[],
        repository_url=review.repository_url
    )

    review.task_id = task.id
    await db.commit()

    return AnalysisResponse(
        review_id=review.id,
        status="processing",
        suggestions=[],
        confidence_scores=[],
        processing_time=0.0,
        cost_estimate=0.0
    )
