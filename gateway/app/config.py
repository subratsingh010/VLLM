from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LLM_GATEWAY_", extra="ignore")
    service_name: str = "llm-gateway"
    pipeline: str = Field(pattern=r"^pipeline_[ab]$")
    upstream_base_url: str
    upstream_model: str
    max_active_requests: int = Field(default=4, ge=1, le=64)
    max_queued_requests: int = Field(default=8, ge=0, le=256)
    queue_timeout_seconds: float = Field(default=5, gt=0)
    upstream_timeout_seconds: float = Field(default=120, gt=0)
    shutdown_grace_seconds: float = Field(default=30, gt=0)
    max_messages: int = Field(default=32, ge=1)
    max_characters: int = Field(default=100_000, ge=1)
    max_tokens: int = Field(default=128, ge=1, le=2048)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
