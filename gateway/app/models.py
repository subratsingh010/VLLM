from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1)


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model: str | None = None
    messages: list[Message] = Field(min_length=1)
    max_tokens: int = Field(default=128, ge=1)
    temperature: float = Field(default=0, ge=0, le=2)
    top_p: float = Field(default=1, gt=0, le=1)
    stream: Literal[True] = True
    seed: int | None = None

    @model_validator(mode="after")
    def user_message_required(self) -> ChatCompletionRequest:
        if not any(message.role == "user" for message in self.messages):
            raise ValueError("at least one user message is required")
        return self
