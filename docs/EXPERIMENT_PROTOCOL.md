# Experiment protocol

This document is the experiment contract. Any change after Pipeline A begins requires a protocol version bump and invalidates comparisons with earlier runs.

## Shared conditions

- Model family and parameter count: Qwen3-1.7B for both pipelines.
- Prompt files and evaluation dataset: byte-identical.
- Streaming: enabled.
- Generation: temperature 0, top-p 1, maximum 128 new tokens.
- Context cap: 4,096 tokens for the initial experiment.
- Thinking mode: fixed by `generation.json` and identical across both pipelines.
- Concurrency levels: 1, 2, 4.
- Concurrency 8: admitted only if both pipelines independently pass the same safety gate.
- Warm-up: two requests per prompt class and concurrency level; never saved as measurements.
- Measurements: ten requests per prompt/concurrency cell.
- Timeout: 120 seconds per request.
- Workload order: deterministic using seed 20260905.
- Run pipelines sequentially with the same nonessential applications closed.

## Prompt classes

Prompt classes target approximately 64, 512, and 2,048 tokenizer input tokens. Exact counts are recorded by the serving model's tokenizer. Phase 2 validates the files and pads/revises prompts if they miss their declared bands.

## Safety gate

Before measurement, load the model and run one long-prompt request at concurrency 1, then 2, then 4. Stop on allocation failure, timeout, sustained memory pressure, swap growth, thermal warning, or more than 5% request failures. Concurrency 8 is included only when both pipelines pass through 4 without those signals.

## Source-of-truth implementation

Performance measurements are produced by the pinned official `vllm bench serve` implementation. Project code may orchestrate identical runs, sample host resources, validate metadata, and transform saved results into reports, but must not reimplement official TTFT, TPOT, ITL, latency percentile, or token-throughput calculations. See `OFFICIAL_VLLM_BENCHMARK_AUDIT.md`.

## Metric definitions

- TTFT: first response-byte/token event time minus request dispatch time.
- End-to-end latency: final event time minus dispatch time.
- TPOT: `(end_to_end - ttft) / (output_tokens - 1)`; unavailable for fewer than two output tokens.
- Inter-token latency: differences between valid token timestamps. If an SSE event contains multiple tokens without individual timestamps, per-token ITL is unavailable rather than guessed.
- Request throughput: successful requests divided by measured wall-clock interval.
- Output throughput: successful output tokens divided by measured wall-clock interval.
- Aggregate token throughput: successful input plus output tokens divided by measured wall-clock interval.
- Error rate and timeout rate use all measured requests as denominator.
- Percentiles use linear interpolation over successful finite samples.

Grafana and server-side histogram buckets are not used to populate benchmark reports.

## Resource measurements

Record model file bytes, load duration, process RSS, host memory pressure, swap counters, CPU use, and backend-reported cache metrics. Metal/GPU utilization is recorded only if a reliable sampler works without changing benchmark conditions; otherwise its value is explicitly `unavailable` with a reason.

## Quality evaluation

Objective cases are scored by exact, numeric, set, substring, or JSON-schema rules. Objective and judge-based scores are stored and reported separately. No LLM judge is enabled by default.
