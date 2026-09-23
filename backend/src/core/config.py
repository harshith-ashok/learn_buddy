from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://learn_buddy:change-me@localhost:5432/learn_buddy"
    db_pool_size: int = 5
    db_max_overflow: int = 10

    redis_url: str = "redis://localhost:6379/0"

    chroma_host: str = "localhost"
    chroma_port: int = 8001
    chroma_collection_prefix: str = "learn_buddy"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    ollama_api_key: str = ""
    ollama_base_url: str = "https://ollama.com"
    ollama_model: str = "gpt-oss:120b-cloud"
    ollama_embed_model: str = ""
    ollama_timeout_seconds: float = 60.0
    ollama_max_retries: int = 3

    log_level: str = "INFO"

    storage_dir: str = "./storage"
    max_upload_size_mb: int = 25

    chunk_target_tokens: int = 400
    chunk_overlap_tokens: int = 50
    embedding_batch_size: int = 32

    retrieval_candidate_pool: int = 24
    retrieval_similarity_threshold: float = 0.55
    retrieval_rerank_top_n: int = 5

    mastery_ema_alpha: float = 0.4
    mastery_ready_threshold: float = 0.6
    mastery_target_threshold: float = 0.8
    quiz_pass_threshold: float = 0.6
    remediation_consecutive_failures: int = 2
    remediation_mastery_drop: float = 0.2
    exam_urgency_window_days: int = 14

    study_kit_generation_rate_limit: int = 10
    study_kit_generation_rate_limit_window_seconds: int = 3600

    chat_ask_rate_limit: int = 30
    chat_ask_rate_limit_window_seconds: int = 3600

    feynman_grade_rate_limit: int = 20
    feynman_grade_rate_limit_window_seconds: int = 3600

    worked_answer_grade_rate_limit: int = 20
    worked_answer_grade_rate_limit_window_seconds: int = 3600

    # Comma-separated allowed origins for the frontend's cross-origin
    # requests (browser SPA on a different port/host than the API). Split
    # in main.py rather than typed as list[str] here — pydantic-settings
    # would otherwise expect JSON in the env var, which is an awkward
    # thing to hand-edit in a .env file.
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001"


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached settings instance."""
    return Settings()
