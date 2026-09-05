import pytest
from pydantic import ValidationError

from gateway.app.models import ChatCompletionRequest


def test_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(
            {"messages": [{"role": "user", "content": "hello"}], "unsupported": True}
        )


def test_requires_user_message_and_streaming() -> None:
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(
            {"messages": [{"role": "system", "content": "hello"}], "stream": True}
        )
    with pytest.raises(ValidationError):
        ChatCompletionRequest.model_validate(
            {"messages": [{"role": "user", "content": "hello"}], "stream": False}
        )
