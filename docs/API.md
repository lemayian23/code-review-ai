# Code Review AI - API Documentation

## Overview

The Code Review AI API provides intelligent code analysis capabilities through RESTful endpoints and WebSocket connections. All endpoints require authentication via JWT tokens.

## Base URL

```
http://localhost:8000
```

## Authentication

All API endpoints (except health checks) require authentication via JWT tokens:

```bash
Authorization: Bearer <your-jwt-token>
```

## Endpoints

### Health Checks

#### GET /health/

Basic health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "0.1.0",
  "environment": "development"
}
```

#### GET /health/ready

Readiness check with database connectivity.

**Response:**

```json
{
  "status": "ready",
  "timestamp": "2024-01-15T10:30:00Z",
  "database": "connected"
}
```

#### GET /health/live

Liveness check for Kubernetes.

**Response:**

```json
{
  "status": "alive",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Code Analysis

#### POST /api/v1/analyze/

Analyze code changes and generate review suggestions.

**Request Body:**

```json
{
  "repository_url": "https://github.com/example/repo",
  "pull_request_id": 123,
  "diff_content": "diff --git a/src/main.py b/src/main.py...",
  "base_commit": "abc123",
  "head_commit": "def456",
  "file_paths": ["src/main.py"],
  "context_files": ["src/utils.py"]
}
```

**Response:**

```json
{
  "review_id": "uuid",
  "status": "processing",
  "suggestions": [],
  "confidence_scores": [],
  "processing_time": 0.0,
  "cost_estimate": 0.0
}
```

#### GET /api/v1/analyze/{review_id}

Get analysis result by review ID.

**Response:**

```json
{
  "review_id": "uuid",
  "status": "completed",
  "suggestions": [
    {
      "type": "security",
      "title": "Password hashing missing",
      "description": "Passwords should be hashed before storage",
      "severity": "high",
      "line_number": 13,
      "suggestion": "Use bcrypt or similar to hash passwords",
      "confidence": 0.9
    }
  ],
  "confidence_scores": [0.9],
  "processing_time": 2.5,
  "cost_estimate": 0.05
}
```

#### WebSocket /api/v1/analyze/{review_id}/stream

Stream analysis results in real-time.

**Connection:**

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/api/v1/analyze/{review_id}/stream"
);
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Analysis update:", data);
};
```

**Message Types:**

- `progress`: Analysis in progress
- `complete`: Analysis completed with results

#### POST /api/v1/analyze/{review_id}/regenerate

Regenerate analysis with updated parameters.

**Response:**

```json
{
  "review_id": "uuid",
  "status": "processing",
  "suggestions": [],
  "confidence_scores": [],
  "processing_time": 0.0,
  "cost_estimate": 0.0
}
```

### Feedback System

#### POST /api/v1/feedback/

Submit feedback for a code review suggestion.

**Request Body:**

```json
{
  "review_id": "uuid",
  "suggestion_id": "suggestion_1",
  "helpful": true,
  "correction": "Great catch on the security issue",
  "category": "security"
}
```

**Response:**

```json
{
  "feedback_id": "uuid",
  "status": "processed",
  "message": "Feedback recorded and learning process triggered"
}
```

#### GET /api/v1/feedback/metrics

Get learning metrics for the current user.

**Response:**

```json
{
  "total_feedback": 100,
  "helpful_feedback": 80,
  "precision_score": 0.8,
  "recall_score": 0.7,
  "confidence_calibration": 0.85,
  "learning_velocity": 0.1
}
```

#### GET /api/v1/feedback/history

Get feedback history for the current user.

**Query Parameters:**

- `limit` (int): Number of results (default: 50)
- `offset` (int): Number of results to skip (default: 0)

**Response:**

```json
[
  {
    "id": "feedback-1",
    "review_id": "review-1",
    "suggestion_id": "suggestion-1",
    "helpful": true,
    "correction": "Good catch",
    "category": "security",
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

#### DELETE /api/v1/feedback/{feedback_id}

Delete feedback (for corrections).

**Response:**

```json
{
  "message": "Feedback deleted successfully"
}
```

#### POST /api/v1/feedback/{review_id}/batch

Submit multiple feedback items at once.

**Request Body:**

```json
{
  "feedback_list": [
    {
      "suggestion_id": "suggestion-1",
      "helpful": true,
      "category": "security"
    },
    {
      "suggestion_id": "suggestion-2",
      "helpful": false,
      "category": "style"
    }
  ]
}
```

**Response:**

```json
{
  "message": "Successfully submitted 2 feedback items",
  "count": 2
}
```

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

### 400 Bad Request

```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid token"
}
```

### 403 Forbidden

```json
{
  "detail": "Access denied"
}
```

### 404 Not Found

```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests

```json
{
  "error": "Rate limit exceeded",
  "message": "Maximum 100 requests per minute",
  "retry_after": 60
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

- **Default**: 100 requests per minute
- **Burst**: 20 requests
- **Headers**: Rate limit information in response headers

## WebSocket Events

### Connection

```javascript
const ws = new WebSocket(
  "ws://localhost:8000/api/v1/analyze/{review_id}/stream"
);
```

### Message Types

#### Progress Update

```json
{
  "type": "progress",
  "status": "processing",
  "message": "Analyzing code changes..."
}
```

#### Completion

```json
{
  "type": "complete",
  "status": "completed",
  "suggestions": [...],
  "confidence_scores": [...],
  "processing_time": 2.5,
  "cost_estimate": 0.05
}
```

## SDK Examples

### Python

```python
import requests

# Analyze code
response = requests.post(
    'http://localhost:8000/api/v1/analyze/',
    headers={'Authorization': 'Bearer your-token'},
    json={
        'repository_url': 'https://github.com/example/repo',
        'pull_request_id': 123,
        'diff_content': 'diff --git a/src/main.py...',
        'base_commit': 'abc123',
        'head_commit': 'def456'
    }
)
```

### JavaScript

```javascript
// Analyze code
const response = await fetch("http://localhost:8000/api/v1/analyze/", {
  method: "POST",
  headers: {
    Authorization: "Bearer your-token",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    repository_url: "https://github.com/example/repo",
    pull_request_id: 123,
    diff_content: "diff --git a/src/main.py...",
    base_commit: "abc123",
    head_commit: "def456",
  }),
});
```

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/analyze/ \
  -H "Authorization: Bearer your-token" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/example/repo",
    "pull_request_id": 123,
    "diff_content": "diff --git a/src/main.py...",
    "base_commit": "abc123",
    "head_commit": "def456"
  }'
```
