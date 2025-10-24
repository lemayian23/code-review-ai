"""
Configuration management for Code Review AI
"""
import os
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    API_PORT: int = Field(default=8000, description="API port")
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    SECRET_KEY: str = Field(..., description="Secret key for JWT")
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000"],
        description="CORS allowed origins"
    )

    # Database Configuration
    DATABASE_URL: str = Field(..., description="Database connection URL")
    REDIS_URL: str = Field(..., description="Redis connection URL")

    # LLM Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    ANTHROPIC_API_KEY: str = Field(..., description="Anthropic API key")
    LLM_MODEL_PRIMARY: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Primary LLM model"
    )
    LLM_MODEL_EMBEDDINGS: str = Field(
        default="text-embedding-3-small",
        description="Embeddings model"
    )
    LLM_MAX_TOKENS: int = Field(default=4000, description="Max tokens for LLM")
    LLM_TEMPERATURE: float = Field(default=0.1, description="LLM temperature")

    # Vector Database
    WEAVIATE_URL: str = Field(..., description="Weaviate URL")
    WEAVIATE_API_KEY: str = Field(default="", description="Weaviate API key")
    WEAVIATE_CLASS_NAME: str = Field(
        default="CodeEmbeddings",
        description="Weaviate class name"
    )

    # GitHub Integration
    GITHUB_APP_ID: str = Field(default="", description="GitHub App ID")
    GITHUB_PRIVATE_KEY_PATH: str = Field(
        default="",
        description="GitHub private key path"
    )
    GITHUB_WEBHOOK_SECRET: str = Field(
        default="",
        description="GitHub webhook secret"
    )
    GITHUB_BASE_URL: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL"
    )

    # Observability
    DATADOG_API_KEY: str = Field(default="", description="Datadog API key")
    SENTRY_DSN: str = Field(default="", description="Sentry DSN")
    LOG_LEVEL: str = Field(default="INFO", description="Log level")

    # Cost Controls
    MONTHLY_BUDGET_USD: float = Field(
        default=2000.0,
        description="Monthly budget in USD"
    )
    ALERT_THRESHOLD_USD: float = Field(
        default=1500.0,
        description="Alert threshold in USD"
    )
    CACHE_TTL_DAYS: int = Field(default=90, description="Cache TTL in days")

    # Security
    JWT_SECRET_KEY: str = Field(..., description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="JWT access token expiry in minutes"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        description="JWT refresh token expiry in days"
    )

    # Rate Limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = Field(
        default=100,
        description="Rate limit requests per minute"
    )
    RATE_LIMIT_BURST: int = Field(
        default=20,
        description="Rate limit burst capacity"
    )

    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment")
    DEBUG: bool = Field(default=False, description="Debug mode")

    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.ENVIRONMENT.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
