# Production-Style LLM Serving on Apple Silicon

This repository is a measured, reproducible study of Qwen3 serving on a 16 GB Apple M2 Mac:

- Pipeline A: native BF16 weights.
- Pipeline B: configurable BF16, FP16, MLX INT8, and MLX INT4 variants derived from the same pinned source where technically applicable.

No benchmark value belongs in this repository unless it was produced by the pinned official `vllm bench` implementation on this machine. Project code only orchestrates runs, samples host resources, validates compatibility, and builds reports. Grafana is for operational visualization; saved official results are the benchmark source of truth.

## Current status

- Phase 0: environment and existing observability stack inspected.
- Phase 1: experiment contracts and project foundation implemented.
- Pipeline A: completed no-prefix-cache capacity baseline.
- Pipeline B: configuration framework only; no variant has been executed.

See [experiment protocol](docs/EXPERIMENT_PROTOCOL.md), [architecture](docs/ARCHITECTURE.md), and [observability integration](observability/README.md).

## Layout

```text
benchmark/       Official-vLLM wrappers, capacity matrix, samplers, tests
evaluation/      Fixed quality dataset and objective scorers
prompts/         Fixed short, medium, and long workload prompts
gateway/         Replaceable FastAPI serving gateway
pipeline_a/      BF16-only configuration, logs, results, and report
pipeline_b/      Isolated precision/quantization variants and manual workflow
pipeline_3/      Safety-bounded auto-tuning using official vLLM sweeps
comparison/      Offline result comparison; never starts a model
observability/   Additions for the existing workflow stack
shared/          Reproducibility metadata
```

## Development

Python 3.12 ARM64 is required.

```bash
uv sync --all-groups
uv run pytest
uv run ruff check .
```

Phase-specific run instructions will be added only when that phase is approved.
