"""
Database models for Code Review AI
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import Column, String, Text, DateTime, Boolean, Float, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    github_id = Column(String(50), unique=True, nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    reviews = relationship("CodeReview", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")


class Repository(Base):
    """Repository model"""
    __tablename__ = "repositories"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(String(500), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    language = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    reviews = relationship("CodeReview", back_populates="repository", cascade="all, delete-orphan")
    embeddings = relationship("CodeEmbedding", back_populates="repository", cascade="all, delete-orphan")


class CodeReview(Base):
    """Code review model"""
    __tablename__ = "code_reviews"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    repository_id = Column(PostgresUUID(as_uuid=True), ForeignKey("repositories.id"), nullable=True, index=True)
    repository_url = Column(String(500), nullable=False)
    pull_request_id = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)  # pending, processing, completed, failed
    task_id = Column(String(255), nullable=True, index=True)  # Celery task ID
    
    # Git information
    base_commit = Column(String(40), nullable=False)
    head_commit = Column(String(40), nullable=False)
    diff_content = Column(Text, nullable=False)
    
    # Analysis results
    suggestions = Column(JSON, nullable=True)  # List of suggestion objects
    confidence_scores = Column(JSON, nullable=True)  # List of confidence scores
    processing_time = Column(Float, nullable=True)  # Processing time in seconds
    cost_estimate = Column(Float, nullable=True)  # Cost estimate in USD
    token_usage = Column(JSON, nullable=True)  # Token usage breakdown
    
    # Metadata
    file_paths = Column(JSON, nullable=True)  # List of changed file paths
    context_files = Column(JSON, nullable=True)  # List of context files used
    model_version = Column(String(100), nullable=True)  # LLM model version used
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="reviews")
    repository = relationship("Repository", back_populates="reviews")
    feedback = relationship("Feedback", back_populates="review", cascade="all, delete-orphan")


class Feedback(Base):
    """Feedback model for learning system"""
    __tablename__ = "feedback"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    review_id = Column(PostgresUUID(as_uuid=True), ForeignKey("code_reviews.id"), nullable=False, index=True)
    suggestion_id = Column(String(255), nullable=False, index=True)
    helpful = Column(Boolean, nullable=False, index=True)
    correction = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)  # bug, style, performance, security, etc.
    
    # Learning metadata
    confidence_score = Column(Float, nullable=True)  # Original confidence score
    learning_weight = Column(Float, default=1.0, nullable=False)  # Weight for learning algorithm
    processed = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="feedback")
    review = relationship("CodeReview", back_populates="feedback")


class CodeEmbedding(Base):
    """Code embedding model for RAG system"""
    __tablename__ = "code_embeddings"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id = Column(PostgresUUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False, index=True)
    file_path = Column(String(500), nullable=False, index=True)
    function_name = Column(String(255), nullable=True, index=True)
    class_name = Column(String(255), nullable=True, index=True)
    
    # Code content
    code_content = Column(Text, nullable=False)
    code_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of code content
    
    # Embedding data
    embedding_vector = Column(JSON, nullable=False)  # Vector embedding as JSON array
    embedding_model = Column(String(100), nullable=False)  # Model used for embedding
    embedding_dimension = Column(Integer, nullable=False)  # Dimension of embedding vector
    
    # Metadata
    line_start = Column(Integer, nullable=True)
    line_end = Column(Integer, nullable=True)
    language = Column(String(50), nullable=True)
    complexity_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="embeddings")


class PatternRule(Base):
    """Pattern rule model for custom rules"""
    __tablename__ = "pattern_rules"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    pattern_type = Column(String(50), nullable=False, index=True)  # regex, ast, semantic
    pattern_content = Column(Text, nullable=False)
    severity = Column(String(20), default="warning", nullable=False)  # info, warning, error
    category = Column(String(100), nullable=True, index=True)
    language = Column(String(50), nullable=True, index=True)
    
    # Rule configuration
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    confidence_threshold = Column(Float, default=0.7, nullable=False)
    learning_enabled = Column(Boolean, default=True, nullable=False)
    
    # Usage statistics
    usage_count = Column(Integer, default=0, nullable=False)
    success_count = Column(Integer, default=0, nullable=False)
    precision_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LearningMetrics(Base):
    """Learning metrics model for tracking AI performance"""
    __tablename__ = "learning_metrics"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PostgresUUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)  # Null for global metrics
    repository_id = Column(PostgresUUID(as_uuid=True), ForeignKey("repositories.id"), nullable=True, index=True)
    
    # Metrics
    precision_score = Column(Float, nullable=False)
    recall_score = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    confidence_calibration = Column(Float, nullable=False)
    learning_velocity = Column(Float, nullable=False)
    
    # Sample counts
    total_feedback = Column(Integer, nullable=False)
    helpful_feedback = Column(Integer, nullable=False)
    false_positives = Column(Integer, nullable=False)
    false_negatives = Column(Integer, nullable=False)
    
    # Time period
    period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    repository = relationship("Repository")
