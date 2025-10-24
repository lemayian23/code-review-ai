"""
Integration tests for API endpoints
"""
import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from api.main import app
from db.models import User, CodeReview


class TestAPIEndpoints:
    """Test cases for API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Mock user for authentication"""
        return User(
            id="test-user-id",
            email="test@example.com",
            username="testuser",
            is_active=True
        )
    
    @pytest.fixture
    def auth_headers(self):
        """Mock authentication headers"""
        return {"Authorization": "Bearer mock-token"}

    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_ready(self, client):
        """Test readiness check endpoint"""
        with patch("api.routers.health.get_db") as mock_get_db:
            mock_session = AsyncMock()
            mock_get_db.return_value = mock_session
            
            response = client.get("/health/ready")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "ready"
            assert data["database"] == "connected"

    def test_health_live(self, client):
        """Test liveness check endpoint"""
        response = client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "alive"

    def test_analyze_code_success(self, client, auth_headers):
        """Test successful code analysis"""
        with patch("api.routers.analyze.get_current_user") as mock_get_user:
            with patch("api.routers.analyze.get_db") as mock_get_db:
                with patch("workers.tasks.analyze_code.analyze_code_task.delay") as mock_task:
                    mock_get_user.return_value = User(id="test-user")
                    mock_get_db.return_value = AsyncMock()
                    mock_task.return_value.id = "task-123"
                    
                    payload = {
                        "repository_url": "https://github.com/test/repo",
                        "pull_request_id": 123,
                        "diff_content": "diff --git a/test.py b/test.py\n+def test():\n+    pass",
                        "base_commit": "abc123",
                        "head_commit": "def456",
                        "file_paths": ["test.py"]
                    }
                    
                    response = client.post(
                        "/api/v1/analyze/",
                        headers=auth_headers,
                        json=payload
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "processing"
                    assert "review_id" in data

    def test_analyze_code_unauthorized(self, client):
        """Test code analysis without authentication"""
        payload = {
            "repository_url": "https://github.com/test/repo",
            "pull_request_id": 123,
            "diff_content": "diff --git a/test.py b/test.py\n+def test():\n+    pass",
            "base_commit": "abc123",
            "head_commit": "def456"
        }
        
        response = client.post("/api/v1/analyze/", json=payload)
        assert response.status_code == 401

    def test_get_analysis_result(self, client, auth_headers):
        """Test getting analysis result"""
        with patch("api.routers.analyze.get_current_user") as mock_get_user:
            with patch("api.routers.analyze.get_db") as mock_get_db:
                mock_get_user.return_value = User(id="test-user")
                mock_session = AsyncMock()
                mock_get_db.return_value = mock_session
                
                # Mock review data
                mock_review = CodeReview(
                    id="review-123",
                    user_id="test-user",
                    status="completed",
                    suggestions=[{"type": "bug", "title": "Test issue"}],
                    confidence_scores=[0.8],
                    processing_time=2.5,
                    cost_estimate=0.05
                )
                mock_session.get.return_value = mock_review
                
                response = client.get(
                    "/api/v1/analyze/review-123",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert len(data["suggestions"]) == 1

    def test_get_analysis_result_not_found(self, client, auth_headers):
        """Test getting non-existent analysis result"""
        with patch("api.routers.analyze.get_current_user") as mock_get_user:
            with patch("api.routers.analyze.get_db") as mock_get_db:
                mock_get_user.return_value = User(id="test-user")
                mock_session = AsyncMock()
                mock_get_db.return_value = mock_session
                mock_session.get.return_value = None
                
                response = client.get(
                    "/api/v1/analyze/non-existent",
                    headers=auth_headers
                )
                
                assert response.status_code == 404

    def test_submit_feedback_success(self, client, auth_headers):
        """Test successful feedback submission"""
        with patch("api.routers.feedback.get_current_user") as mock_get_user:
            with patch("api.routers.feedback.get_db") as mock_get_db:
                with patch("core.feedback.learner.FeedbackLearner.process_feedback") as mock_learner:
                    mock_get_user.return_value = User(id="test-user")
                    mock_session = AsyncMock()
                    mock_get_db.return_value = mock_session
                    mock_learner.return_value = AsyncMock()
                    
                    # Mock review data
                    mock_review = CodeReview(id="review-123", user_id="test-user")
                    mock_session.get.return_value = mock_review
                    
                    payload = {
                        "review_id": "review-123",
                        "suggestion_id": "suggestion-1",
                        "helpful": True,
                        "correction": "Great catch!",
                        "category": "security"
                    }
                    
                    response = client.post(
                        "/api/v1/feedback/",
                        headers=auth_headers,
                        json=payload
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "processed"

    def test_submit_feedback_review_not_found(self, client, auth_headers):
        """Test feedback submission for non-existent review"""
        with patch("api.routers.feedback.get_current_user") as mock_get_user:
            with patch("api.routers.feedback.get_db") as mock_get_db:
                mock_get_user.return_value = User(id="test-user")
                mock_session = AsyncMock()
                mock_get_db.return_value = mock_session
                mock_session.get.return_value = None
                
                payload = {
                    "review_id": "non-existent",
                    "suggestion_id": "suggestion-1",
                    "helpful": True
                }
                
                response = client.post(
                    "/api/v1/feedback/",
                    headers=auth_headers,
                    json=payload
                )
                
                assert response.status_code == 404

    def test_get_learning_metrics(self, client, auth_headers):
        """Test getting learning metrics"""
        with patch("api.routers.feedback.get_current_user") as mock_get_user:
            with patch("core.feedback.learner.FeedbackLearner.get_metrics") as mock_metrics:
                mock_get_user.return_value = User(id="test-user")
                mock_metrics.return_value = AsyncMock()
                mock_metrics.return_value = {
                    "precision": 0.8,
                    "recall": 0.7,
                    "f1_score": 0.75,
                    "confidence_calibration": 0.85,
                    "learning_velocity": 0.1,
                    "total_feedback": 100,
                    "helpful_feedback": 80
                }
                
                response = client.get(
                    "/api/v1/feedback/metrics",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["precision_score"] == 0.8
                assert data["recall_score"] == 0.7

    def test_get_feedback_history(self, client, auth_headers):
        """Test getting feedback history"""
        with patch("api.routers.feedback.get_current_user") as mock_get_user:
            with patch("api.routers.feedback.get_db") as mock_get_db:
                mock_get_user.return_value = User(id="test-user")
                mock_session = AsyncMock()
                mock_get_db.return_value = mock_session
                
                # Mock feedback query
                mock_feedback = [
                    {
                        "id": "feedback-1",
                        "review_id": "review-1",
                        "suggestion_id": "suggestion-1",
                        "helpful": True,
                        "correction": "Good catch",
                        "category": "security",
                        "created_at": "2024-01-01T00:00:00Z"
                    }
                ]
                mock_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_feedback
                
                response = client.get(
                    "/api/v1/feedback/history",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["helpful"] is True

    def test_delete_feedback(self, client, auth_headers):
        """Test deleting feedback"""
        with patch("api.routers.feedback.get_current_user") as mock_get_user:
            with patch("api.routers.feedback.get_db") as mock_get_db:
                mock_get_user.return_value = User(id="test-user")
                mock_session = AsyncMock()
                mock_get_db.return_value = mock_session
                
                # Mock feedback data
                mock_feedback = {"id": "feedback-1", "user_id": "test-user"}
                mock_session.get.return_value = mock_feedback
                
                response = client.delete(
                    "/api/v1/feedback/feedback-1",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "deleted successfully" in data["message"]

    def test_batch_feedback_submission(self, client, auth_headers):
        """Test batch feedback submission"""
        with patch("api.routers.feedback.get_current_user") as mock_get_user:
            with patch("api.routers.feedback.get_db") as mock_get_db:
                with patch("core.feedback.learner.FeedbackLearner.process_batch_feedback") as mock_batch:
                    mock_get_user.return_value = User(id="test-user")
                    mock_session = AsyncMock()
                    mock_get_db.return_value = mock_session
                    mock_batch.return_value = AsyncMock()
                    
                    # Mock review data
                    mock_review = CodeReview(id="review-123", user_id="test-user")
                    mock_session.get.return_value = mock_review
                    
                    payload = {
                        "review_id": "review-123",
                        "feedback_list": [
                            {
                                "suggestion_id": "suggestion-1",
                                "helpful": True,
                                "category": "security"
                            },
                            {
                                "suggestion_id": "suggestion-2",
                                "helpful": False,
                                "category": "style"
                            }
                        ]
                    }
                    
                    response = client.post(
                        "/api/v1/feedback/review-123/batch",
                        headers=auth_headers,
                        json=payload
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["count"] == 2
