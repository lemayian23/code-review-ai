"""
Feedback learning system for Code Review AI
"""
import time
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

import structlog
from core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


@dataclass
class LearningMetrics:
    """Learning metrics data structure"""
    precision: float
    recall: float
    f1_score: float
    confidence_calibration: float
    learning_velocity: float
    total_feedback: int
    helpful_feedback: int


class FeedbackLearner:
    """Learning system that improves from user feedback"""
    
    def __init__(self):
        self.learning_rate = 0.1
        self.feedback_weights = {}
        self.pattern_confidence = {}
        self.learning_history = []

    async def process_feedback(self, feedback_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process individual feedback and update learning
        """
        try:
            logger.debug("Processing feedback", feedback_id=feedback_data.get("id"))
            
            # Extract feedback information
            helpful = feedback_data.get("helpful", False)
            suggestion_id = feedback_data.get("suggestion_id", "")
            category = feedback_data.get("category", "general")
            correction = feedback_data.get("correction", "")
            
            # Update learning weights
            self._update_weights(suggestion_id, helpful, category)
            
            # Update pattern confidence
            if correction:
                self._update_pattern_confidence(correction, helpful)
            
            # Record learning event
            learning_event = {
                "timestamp": datetime.utcnow(),
                "feedback_id": feedback_data.get("id"),
                "helpful": helpful,
                "category": category,
                "learning_impact": self._calculate_learning_impact(helpful, category)
            }
            self.learning_history.append(learning_event)
            
            # Calculate learning metrics
            metrics = self._calculate_metrics()
            
            logger.info(
                "Feedback processed",
                feedback_id=feedback_data.get("id"),
                helpful=helpful,
                learning_impact=learning_event["learning_impact"]
            )
            
            return {
                "status": "processed",
                "learning_impact": learning_event["learning_impact"],
                "metrics": metrics
            }
            
        except Exception as e:
            logger.error("Feedback processing failed", error=str(e))
            raise

    async def process_batch_feedback(self, feedback_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process multiple feedback items in batch
        """
        try:
            logger.info("Processing batch feedback", count=len(feedback_list))
            
            batch_results = []
            total_impact = 0.0
            
            for feedback in feedback_list:
                result = await self.process_feedback(feedback)
                batch_results.append(result)
                total_impact += result.get("learning_impact", 0.0)
            
            # Calculate batch learning metrics
            batch_metrics = self._calculate_batch_metrics(feedback_list)
            
            logger.info(
                "Batch feedback processed",
                count=len(feedback_list),
                total_impact=total_impact
            )
            
            return {
                "status": "batch_processed",
                "processed_count": len(feedback_list),
                "total_impact": total_impact,
                "batch_metrics": batch_metrics
            }
            
        except Exception as e:
            logger.error("Batch feedback processing failed", error=str(e))
            raise

    def _update_weights(self, suggestion_id: str, helpful: bool, category: str):
        """Update learning weights based on feedback"""
        if suggestion_id not in self.feedback_weights:
            self.feedback_weights[suggestion_id] = {
                "total_feedback": 0,
                "helpful_feedback": 0,
                "categories": {}
            }
        
        weight_data = self.feedback_weights[suggestion_id]
        weight_data["total_feedback"] += 1
        
        if helpful:
            weight_data["helpful_feedback"] += 1
        
        if category not in weight_data["categories"]:
            weight_data["categories"][category] = {"total": 0, "helpful": 0}
        
        weight_data["categories"][category]["total"] += 1
        if helpful:
            weight_data["categories"][category]["helpful"] += 1

    def _update_pattern_confidence(self, correction: str, helpful: bool):
        """Update pattern confidence based on corrections"""
        # Extract patterns from correction
        patterns = self._extract_patterns_from_correction(correction)
        
        for pattern in patterns:
            if pattern not in self.pattern_confidence:
                self.pattern_confidence[pattern] = {"total": 0, "correct": 0}
            
            self.pattern_confidence[pattern]["total"] += 1
            if helpful:
                self.pattern_confidence[pattern]["correct"] += 1

    def _extract_patterns_from_correction(self, correction: str) -> List[str]:
        """Extract patterns from correction text"""
        # Simple pattern extraction - this would be more sophisticated
        patterns = []
        
        # Look for common patterns
        if "null" in correction.lower():
            patterns.append("null_check")
        if "error" in correction.lower():
            patterns.append("error_handling")
        if "security" in correction.lower():
            patterns.append("security")
        if "performance" in correction.lower():
            patterns.append("performance")
        
        return patterns

    def _calculate_learning_impact(self, helpful: bool, category: str) -> float:
        """Calculate learning impact score"""
        base_impact = 0.1 if helpful else -0.05
        
        # Category-specific adjustments
        category_weights = {
            "security": 0.3,
            "performance": 0.2,
            "bug": 0.25,
            "style": 0.1,
            "maintainability": 0.15
        }
        
        category_weight = category_weights.get(category, 0.1)
        return base_impact * category_weight

    def _calculate_metrics(self) -> LearningMetrics:
        """Calculate current learning metrics"""
        total_feedback = len(self.learning_history)
        helpful_feedback = sum(1 for event in self.learning_history if event["helpful"])
        
        # Calculate precision and recall
        precision = self._calculate_precision()
        recall = self._calculate_recall()
        f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        
        # Calculate confidence calibration
        confidence_calibration = self._calculate_confidence_calibration()
        
        # Calculate learning velocity
        learning_velocity = self._calculate_learning_velocity()
        
        return LearningMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            confidence_calibration=confidence_calibration,
            learning_velocity=learning_velocity,
            total_feedback=total_feedback,
            helpful_feedback=helpful_feedback
        )

    def _calculate_precision(self) -> float:
        """Calculate precision from feedback weights"""
        if not self.feedback_weights:
            return 0.0
        
        total_precision = 0.0
        count = 0
        
        for suggestion_id, weights in self.feedback_weights.items():
            if weights["total_feedback"] > 0:
                precision = weights["helpful_feedback"] / weights["total_feedback"]
                total_precision += precision
                count += 1
        
        return total_precision / count if count > 0 else 0.0

    def _calculate_recall(self) -> float:
        """Calculate recall from feedback weights"""
        # Simplified recall calculation
        if not self.feedback_weights:
            return 0.0
        
        total_recall = 0.0
        count = 0
        
        for suggestion_id, weights in self.feedback_weights.items():
            if weights["total_feedback"] > 0:
                # Recall based on helpful feedback rate
                recall = weights["helpful_feedback"] / weights["total_feedback"]
                total_recall += recall
                count += 1
        
        return total_recall / count if count > 0 else 0.0

    def _calculate_confidence_calibration(self) -> float:
        """Calculate confidence calibration score"""
        if not self.pattern_confidence:
            return 0.0
        
        total_calibration = 0.0
        count = 0
        
        for pattern, conf_data in self.pattern_confidence.items():
            if conf_data["total"] > 0:
                calibration = conf_data["correct"] / conf_data["total"]
                total_calibration += calibration
                count += 1
        
        return total_calibration / count if count > 0 else 0.0

    def _calculate_learning_velocity(self) -> float:
        """Calculate learning velocity over time"""
        if len(self.learning_history) < 2:
            return 0.0
        
        # Calculate improvement over time
        recent_events = self.learning_history[-10:]  # Last 10 events
        older_events = self.learning_history[-20:-10] if len(self.learning_history) >= 20 else []
        
        if not older_events:
            return 0.0
        
        recent_helpful_rate = sum(1 for e in recent_events if e["helpful"]) / len(recent_events)
        older_helpful_rate = sum(1 for e in older_events if e["helpful"]) / len(older_events)
        
        return recent_helpful_rate - older_helpful_rate

    def _calculate_batch_metrics(self, feedback_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics for batch processing"""
        helpful_count = sum(1 for f in feedback_list if f.get("helpful", False))
        total_count = len(feedback_list)
        
        categories = {}
        for feedback in feedback_list:
            category = feedback.get("category", "general")
            if category not in categories:
                categories[category] = {"total": 0, "helpful": 0}
            categories[category]["total"] += 1
            if feedback.get("helpful", False):
                categories[category]["helpful"] += 1
        
        return {
            "helpful_rate": helpful_count / total_count if total_count > 0 else 0,
            "category_breakdown": categories,
            "total_feedback": total_count,
            "helpful_feedback": helpful_count
        }

    async def get_metrics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get learning metrics for user or global"""
        metrics = self._calculate_metrics()
        
        return {
            "precision": metrics.precision,
            "recall": metrics.recall,
            "f1_score": metrics.f1_score,
            "confidence_calibration": metrics.confidence_calibration,
            "learning_velocity": metrics.learning_velocity,
            "total_feedback": metrics.total_feedback,
            "helpful_feedback": metrics.helpful_feedback,
            "feedback_weights": len(self.feedback_weights),
            "pattern_confidence": len(self.pattern_confidence)
        }

    def get_learning_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent learning history"""
        return self.learning_history[-limit:]

    def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for analysis"""
        return {
            "feedback_weights": self.feedback_weights,
            "pattern_confidence": self.pattern_confidence,
            "learning_history": self.learning_history,
            "metrics": self._calculate_metrics()
        }

    def reset_learning(self):
        """Reset learning data"""
        self.feedback_weights.clear()
        self.pattern_confidence.clear()
        self.learning_history.clear()
        logger.info("Learning data reset")
