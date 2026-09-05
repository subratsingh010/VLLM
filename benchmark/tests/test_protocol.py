from pathlib import Path

import pytest

from benchmark.harness.protocol import load_prompts, load_protocol

ROOT = Path(__file__).parents[2]


def test_protocol_is_valid() -> None:
    protocol = load_protocol(ROOT / "benchmark" / "protocol.json")
    assert protocol.concurrency_levels == [1, 2, 4]
    assert protocol.stream is True


def test_fixed_prompt_set_is_valid_and_unique() -> None:
    prompts = load_prompts(sorted((ROOT / "prompts").glob("*.jsonl")))
    assert {prompt.prompt_class for prompt in prompts} == {"short", "medium", "long"}
    assert len(prompts) == 9


def test_duplicate_prompt_ids_are_rejected(tmp_path: Path) -> None:
    line = (
        '{"id":"x","prompt_class":"short","messages":'
        '[{"role":"user","content":"x"}],"target_input_tokens":64}'
    )
    path = tmp_path / "duplicate.jsonl"
    path.write_text(f"{line}\n{line}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_prompts([path])
