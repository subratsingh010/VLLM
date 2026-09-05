# Official vLLM benchmark audit

Audit target: installed vLLM `0.28.0+cpu` paired with vLLM-Metal `0.28.0`.

## Use directly from vLLM

| Requirement | Official implementation |
|---|---|
| Online serving workload | `vllm bench serve` |
| Exact synthetic input/output lengths | `--dataset-name random`, `--random-input-len`, `--random-output-len`, `--random-range-ratio 0` |
| Controlled concurrency | `--max-concurrency` |
| Controlled arrival rate | `--request-rate`; Poisson/gamma arrivals through `--burstiness` |
| Ramp testing | `--ramp-up-strategy`, start/end RPS |
| Warm-up | `--num-warmups` |
| Reproducibility | `--seed`, `--metadata`, explicit tokenizer/model paths |
| TTFT, TPOT, ITL, E2EL | Official client-side streaming measurements |
| P50/P95/P99 | `--percentile-metrics ttft,tpot,itl,e2el --metric-percentiles 50,95,99` |
| Request/output/total-token throughput | Built into saved result |
| Failures | `completed`, `failed`, and detailed error records |
| Machine-readable raw result | `--save-result --save-detailed` |
| Prefix-cache-safe sweeps | `vllm bench sweep serve` resets server cache between points when supported |
| Cold/warm startup | `vllm bench startup` |
| Offline throughput | `vllm bench throughput` |
| Single static batch latency | `vllm bench latency --batch-size`; different from online scheduling |
| Official plots | `vllm bench sweep plot` and timeline/dataset plots |

Official metric definitions are retained unchanged. In particular, TPOT is per-request decode time excluding the first token, while ITL measures gaps between streamed outputs and is not forced to one sample per generated token.

## Minimal project-owned coverage

Official tools do not provide all of the following, so small wrappers remain justified:

- Run the identical matrix for two pipeline configurations and enforce matching metadata.
- Sample host CPU, process RSS, available memory, compression/swap, and vLLM `/metrics` during each official run.
- Distinguish gateway timeout counters from general official benchmark failures. The official HTTP client uses a six-hour total timeout and has no per-request timeout CLI flag in this version.
- Record Metal utilization only if a stable permitted sampler exists; otherwise explicitly mark it unavailable.
- Extract KV-cache utilization from vLLM Prometheus metrics when the Metal plugin exposes it.
- Detect a practical saturation knee from saved sweep points.
- Produce the requested cross-pipeline tables/charts.
- Run the fixed objective quality dataset; this is not a serving benchmark feature.
- Record artifact hashes, exact model revision, host state, and dependency hashes.

The wrapper must never reimplement TTFT, TPOT, ITL, latency percentiles, or token throughput.

## Workloads

Capacity uses the official random-token dataset so requested input/output lengths are controlled exactly. Semantic fixed prompts and objective evaluation remain separate from capacity measurements. This prevents content variation from obscuring scheduler and KV-cache behavior.

## Static batching

`vllm bench latency --batch-size` is an offline single-batch test, not a static-batching mode of the OpenAI server. It uses a different request path and cannot be treated as an apples-to-apples serving baseline. It may be run as a separately labelled educational experiment after the online server stops; it will not be mixed into capacity results.

References:

- https://docs.vllm.ai/en/latest/cli/bench/serve/
- https://docs.vllm.ai/en/latest/benchmarking/cli/
- https://docs.vllm.ai/en/stable/api/vllm/benchmarks/
