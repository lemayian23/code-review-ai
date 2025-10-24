#!/usr/bin/env python3
"""
Seed database with sample data for Code Review AI
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any

import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from core.config import get_settings
from db.models import User, Repository, CodeReview, Feedback, CodeEmbedding, PatternRule

logger = structlog.get_logger(__name__)
settings = get_settings()

# Create database connection
engine = create_async_engine(settings.DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_sample_users(session: AsyncSession) -> List[User]:
    """Create sample users"""
    users = [
        User(
            id=uuid.uuid4(),
            email="alice@example.com",
            username="alice",
            github_id="alice123",
            full_name="Alice Johnson",
            avatar_url="https://github.com/alice.png",
            is_active=True,
            is_admin=True
        ),
        User(
            id=uuid.uuid4(),
            email="bob@example.com",
            username="bob",
            github_id="bob456",
            full_name="Bob Smith",
            avatar_url="https://github.com/bob.png",
            is_active=True,
            is_admin=False
        ),
        User(
            id=uuid.uuid4(),
            email="charlie@example.com",
            username="charlie",
            github_id="charlie789",
            full_name="Charlie Brown",
            avatar_url="https://github.com/charlie.png",
            is_active=True,
            is_admin=False
        )
    ]
    
    for user in users:
        session.add(user)
    
    await session.commit()
    logger.info("Created sample users", count=len(users))
    return users


async def create_sample_repositories(session: AsyncSession) -> List[Repository]:
    """Create sample repositories"""
    repositories = [
        Repository(
            id=uuid.uuid4(),
            url="https://github.com/example/web-app",
            name="web-app",
            owner="example",
            description="A modern web application",
            language="python",
            is_active=True
        ),
        Repository(
            id=uuid.uuid4(),
            url="https://github.com/example/api-service",
            name="api-service",
            owner="example",
            description="REST API service",
            language="python",
            is_active=True
        ),
        Repository(
            id=uuid.uuid4(),
            url="https://github.com/example/frontend",
            name="frontend",
            owner="example",
            description="React frontend application",
            language="typescript",
            is_active=True
        )
    ]
    
    for repo in repositories:
        session.add(repo)
    
    await session.commit()
    logger.info("Created sample repositories", count=len(repositories))
    return repositories


async def create_sample_reviews(session: AsyncSession, users: List[User], repositories: List[Repository]) -> List[CodeReview]:
    """Create sample code reviews"""
    reviews = []
    
    sample_diffs = [
        {
            "content": """diff --git a/src/auth.py b/src/auth.py
index 1234567..abcdefg 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -10,6 +10,7 @@ def authenticate_user(username, password):
     user = get_user_by_username(username)
     if user and user.password == password:
+        # TODO: Add password hashing
         return user
     return None""",
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
            ]
        },
        {
            "content": """diff --git a/src/utils.py b/src/utils.py
index 1111111..2222222 100644
--- a/src/utils.py
+++ b/src/utils.py
@@ -5,6 +5,8 @@ def calculate_total(items):
     total = 0
     for item in items:
+        if item is None:
+            continue
         total += item.price
     return total""",
            "suggestions": [
                {
                    "type": "bug",
                    "title": "Null check added",
                    "description": "Good addition of null check",
                    "severity": "low",
                    "line_number": 8,
                    "suggestion": "Consider using filter() for cleaner code",
                    "confidence": 0.7
                }
            ]
        }
    ]
    
    for i, (user, repo) in enumerate(zip(users, repositories)):
        diff_data = sample_diffs[i % len(sample_diffs)]
        
        review = CodeReview(
            id=uuid.uuid4(),
            user_id=user.id,
            repository_id=repo.id,
            repository_url=repo.url,
            pull_request_id=100 + i,
            status="completed",
            base_commit="abc123",
            head_commit="def456",
            diff_content=diff_data["content"],
            suggestions=diff_data["suggestions"],
            confidence_scores=[s["confidence"] for s in diff_data["suggestions"]],
            processing_time=2.5 + i * 0.5,
            cost_estimate=0.05 + i * 0.01,
            token_usage={"input_tokens": 100, "output_tokens": 50},
            file_paths=["src/auth.py", "src/utils.py"],
            model_version="claude-3-5-sonnet-20241022",
            completed_at=datetime.utcnow() - timedelta(hours=i)
        )
        
        session.add(review)
        reviews.append(review)
    
    await session.commit()
    logger.info("Created sample reviews", count=len(reviews))
    return reviews


async def create_sample_feedback(session: AsyncSession, reviews: List[CodeReview], users: List[User]) -> List[Feedback]:
    """Create sample feedback"""
    feedback_list = []
    
    feedback_data = [
        {"helpful": True, "category": "security", "correction": "Good catch on password hashing"},
        {"helpful": False, "category": "style", "correction": "This is not a real issue"},
        {"helpful": True, "category": "bug", "correction": "Null check is important"},
        {"helpful": True, "category": "performance", "correction": "Good optimization suggestion"}
    ]
    
    for i, review in enumerate(reviews):
        for j, suggestion in enumerate(review.suggestions or []):
            feedback_data_item = feedback_data[(i + j) % len(feedback_data)]
            
            feedback = Feedback(
                id=uuid.uuid4(),
                user_id=review.user_id,
                review_id=review.id,
                suggestion_id=f"suggestion_{i}_{j}",
                helpful=feedback_data_item["helpful"],
                correction=feedback_data_item["correction"],
                category=feedback_data_item["category"],
                confidence_score=suggestion.get("confidence", 0.5),
                learning_weight=1.0,
                processed=True
            )
            
            session.add(feedback)
            feedback_list.append(feedback)
    
    await session.commit()
    logger.info("Created sample feedback", count=len(feedback_list))
    return feedback_list


async def create_sample_embeddings(session: AsyncSession, repositories: List[Repository]) -> List[CodeEmbedding]:
    """Create sample embeddings"""
    embeddings = []
    
    sample_code = [
        {
            "content": "def authenticate_user(username, password):\n    user = get_user_by_username(username)\n    if user and user.password == password:\n        return user\n    return None",
            "file_path": "src/auth.py",
            "function_name": "authenticate_user",
            "class_name": None,
            "line_start": 1,
            "line_end": 6
        },
        {
            "content": "def calculate_total(items):\n    total = 0\n    for item in items:\n        if item is not None:\n            total += item.price\n    return total",
            "file_path": "src/utils.py",
            "function_name": "calculate_total",
            "class_name": None,
            "line_start": 1,
            "line_end": 6
        }
    ]
    
    for repo in repositories:
        for i, code_data in enumerate(sample_code):
            # Generate mock embedding vector
            embedding_vector = [0.1 + i * 0.1 for _ in range(1536)]
            
            embedding = CodeEmbedding(
                id=uuid.uuid4(),
                repository_id=repo.id,
                file_path=code_data["file_path"],
                function_name=code_data["function_name"],
                class_name=code_data["class_name"],
                code_content=code_data["content"],
                code_hash=f"hash_{i}",
                embedding_vector=embedding_vector,
                embedding_model="text-embedding-3-small",
                embedding_dimension=1536,
                line_start=code_data["line_start"],
                line_end=code_data["line_end"],
                language="python",
                complexity_score=0.3 + i * 0.1
            )
            
            session.add(embedding)
            embeddings.append(embedding)
    
    await session.commit()
    logger.info("Created sample embeddings", count=len(embeddings))
    return embeddings


async def create_sample_pattern_rules(session: AsyncSession) -> List[PatternRule]:
    """Create sample pattern rules"""
    rules = [
        PatternRule(
            id=uuid.uuid4(),
            name="null_check_missing",
            description="Check for missing null checks",
            pattern_type="regex",
            pattern_content=r"\.(\w+)\s*=\s*[^=].*[^=]",
            severity="medium",
            category="bug",
            language="python",
            is_active=True,
            confidence_threshold=0.7,
            learning_enabled=True,
            usage_count=10,
            success_count=8,
            precision_score=0.8
        ),
        PatternRule(
            id=uuid.uuid4(),
            name="hardcoded_password",
            description="Detect hardcoded passwords",
            pattern_type="regex",
            pattern_content=r"password\s*=\s*['\"][^'\"]+['\"]",
            severity="high",
            category="security",
            language="python",
            is_active=True,
            confidence_threshold=0.9,
            learning_enabled=True,
            usage_count=5,
            success_count=5,
            precision_score=1.0
        )
    ]
    
    for rule in rules:
        session.add(rule)
    
    await session.commit()
    logger.info("Created sample pattern rules", count=len(rules))
    return rules


async def main():
    """Main seeding function"""
    logger.info("Starting database seeding...")
    
    async with AsyncSessionLocal() as session:
        try:
            # Create sample data
            users = await create_sample_users(session)
            repositories = await create_sample_repositories(session)
            reviews = await create_sample_reviews(session, users, repositories)
            feedback = await create_sample_feedback(session, reviews, users)
            embeddings = await create_sample_embeddings(session, repositories)
            rules = await create_sample_pattern_rules(session)
            
            logger.info("Database seeding completed successfully")
            logger.info(
                "Seeded data",
                users=len(users),
                repositories=len(repositories),
                reviews=len(reviews),
                feedback=len(feedback),
                embeddings=len(embeddings),
                rules=len(rules)
            )
            
        except Exception as e:
            logger.error("Database seeding failed", error=str(e))
            raise


if __name__ == "__main__":
    asyncio.run(main())
