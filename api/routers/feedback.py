"""
Feedback endpoints for learning system
"""
from typing import Dict, Any, List
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, get_db
from core.feedback.learner import FeedbackLearner
from db.models import User, CodeReview, Feedback

logger = structlog.get_logger(__name__)
router = APIRouter()


class FeedbackRequest(BaseModel):
    """Request model for feedback submission"""
    review_id: UUID = Field(..., description="Review ID")
    suggestion_id: str = Field(..., description="Suggestion ID")
    helpful: bool = Field(..., description="Whether suggestion was helpful")
    correction: str = Field(default="", description="Correction or additional context")
    category: str = Field(default="", description="Feedback category")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    feedback_id: UUID = Field(..., description="Feedback ID")
    status: str = Field(..., description="Feedback status")
    message: str = Field(..., description="Response message")


class LearningMetrics(BaseModel):
    """Learning metrics response"""
    total_feedback: int = Field(..., description="Total feedback count")
    helpful_feedback: int = Field(..., description="Helpful feedback count")
    precision_score: float = Field(..., description="Current precision score")
    recall_score: float = Field(..., description="Current recall score")
    confidence_calibration: float = Field(..., description="Confidence calibration score")
    learning_velocity: float = Field(..., description="Learning velocity (improvement rate)")


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> FeedbackResponse:
    """
    Submit feedback for a code review suggestion
    """
    try:
        # Get the review
        review = await db.get(CodeReview, request.review_id)
        if not review or review.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Review not found")

        # Create feedback record
        feedback = Feedback(
            user_id=current_user.id,
            review_id=review.id,
            suggestion_id=request.suggestion_id,
            helpful=request.helpful,
            correction=request.correction,
            category=request.category
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        # Trigger learning process
        learner = FeedbackLearner()
        await learner.process_feedback(feedback)

        logger.info(
            "Feedback submitted",
            feedback_id=feedback.id,
            helpful=request.helpful,
            category=request.category
        )

        return FeedbackResponse(
            feedback_id=feedback.id,
            status="processed",
            message="Feedback recorded and learning process triggered"
        )

    except Exception as e:
        logger.error("Feedback submission failed", error=str(e))
        raise HTTPException(status_code=500, detail="Feedback submission failed")


@router.get("/metrics", response_model=LearningMetrics)
async def get_learning_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> LearningMetrics:
    """
    Get learning metrics for the current user
    """
    try:
        learner = FeedbackLearner()
        metrics = await learner.get_metrics(current_user.id)

        return LearningMetrics(
            total_feedback=metrics["total_feedback"],
            helpful_feedback=metrics["helpful_feedback"],
            precision_score=metrics["precision_score"],
            recall_score=metrics["recall_score"],
            confidence_calibration=metrics["confidence_calibration"],
            learning_velocity=metrics["learning_velocity"]
        )

    except Exception as e:
        logger.error("Failed to get learning metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.get("/history")
async def get_feedback_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[Dict[str, Any]]:
    """
    Get feedback history for the current user
    """
    try:
        # Query feedback history
        feedback_query = (
            db.query(Feedback)
            .filter(Feedback.user_id == current_user.id)
            .order_by(Feedback.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        feedback_list = await feedback_query.all()
        
        return [
            {
                "id": str(feedback.id),
                "review_id": str(feedback.review_id),
                "suggestion_id": feedback.suggestion_id,
                "helpful": feedback.helpful,
                "correction": feedback.correction,
                "category": feedback.category,
                "created_at": feedback.created_at.isoformat()
            }
            for feedback in feedback_list
        ]

    except Exception as e:
        logger.error("Failed to get feedback history", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve feedback history")


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Delete feedback (for corrections)
    """
    try:
        feedback = await db.get(Feedback, feedback_id)
        if not feedback or feedback.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Feedback not found")

        await db.delete(feedback)
        await db.commit()

        logger.info("Feedback deleted", feedback_id=feedback_id)

        return {"message": "Feedback deleted successfully"}

    except Exception as e:
        logger.error("Failed to delete feedback", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete feedback")


@router.post("/{review_id}/batch")
async def submit_batch_feedback(
    review_id: UUID,
    feedback_list: List[FeedbackRequest],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Submit multiple feedback items at once
    """
    try:
        # Get the review
        review = await db.get(CodeReview, review_id)
        if not review or review.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Review not found")

        # Create feedback records
        feedback_records = []
        for feedback_req in feedback_list:
            feedback = Feedback(
                user_id=current_user.id,
                review_id=review.id,
                suggestion_id=feedback_req.suggestion_id,
                helpful=feedback_req.helpful,
                correction=feedback_req.correction,
                category=feedback_req.category
            )
            feedback_records.append(feedback)
            db.add(feedback)

        await db.commit()

        # Trigger batch learning
        learner = FeedbackLearner()
        await learner.process_batch_feedback(feedback_records)

        logger.info(
            "Batch feedback submitted",
            review_id=review_id,
            count=len(feedback_records)
        )

        return {
            "message": f"Successfully submitted {len(feedback_records)} feedback items",
            "count": len(feedback_records)
        }

    except Exception as e:
        logger.error("Batch feedback submission failed", error=str(e))
        raise HTTPException(status_code=500, detail="Batch feedback submission failed")
