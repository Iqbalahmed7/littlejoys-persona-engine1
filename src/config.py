"""
Application configuration loaded from environment variables.

Uses Pydantic Settings for validation. See .env.example for all available variables.
"""

from enum import StrEnum
from typing import Literal

from pydantic_settings import BaseSettings


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Config(BaseSettings):
    """Application configuration — loaded from .env.local or environment variables."""

    # Environment
    environment: Environment = Environment.DEVELOPMENT

    # LLM
    anthropic_api_key: str = ""
    llm_model_reasoning: str = "claude-opus-4-6"
    llm_model_bulk: str = "claude-sonnet-4-6"
    llm_cache_enabled: bool = True
    llm_mock_enabled: bool = True
    llm_max_concurrency: int = 5

    # Population
    population_seed: int = 42
    population_size: int = 300
    deep_persona_count: int = 30

    # Logging
    log_level: str = "DEBUG"
    log_format: Literal["json", "console"] = "json"

    # Simulatte Persona Generator API
    simulatte_api_url: str = "https://simulatte-persona-generator.onrender.com"
    simulatte_cohort_id: str = "littlejoys-v1"

    # Streamlit
    streamlit_server_port: int = 8502

    model_config = {"env_file": ".env.local", "env_file_encoding": "utf-8"}

    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT

    @property
    def is_staging(self) -> bool:
        return self.environment == Environment.STAGING

    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION


def get_config() -> Config:
    """Get application configuration singleton."""
    return Config()
