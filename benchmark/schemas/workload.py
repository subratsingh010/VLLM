from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PromptRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    prompt_class: Literal["short", "medium", "long", "quality"]
    messages: list[dict[Literal["role", "content"], str]]
    target_input_tokens: int = Field(gt=0)
    allowed_token_deviation_fraction: float = Field(default=0.20, ge=0, le=1)


class BenchmarkProtocol(BaseModel):
    model_config = ConfigDict(extra="forbid")
    protocol_version: str
    seed: int
    concurrency_levels: list[int]
    warmups_per_cell: int = Field(ge=0)
    measurements_per_cell: int = Field(gt=0)
    request_timeout_seconds: float = Field(gt=0)
    max_tokens: int = Field(gt=0)
    temperature: float = Field(ge=0)
    top_p: float = Field(gt=0, le=1)
    stream: Literal[True]
    thinking_mode: Literal["disabled", "enabled"]
