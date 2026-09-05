# Official vLLM benchmark and tuning utilities

This project uses the installed official vLLM CLI and does not duplicate its
metric calculations.

| Utility | Relevance | Project policy |
|---|---|---|
| `vllm bench serve` | Streaming online TTFT, TPOT, ITL, E2E, percentiles, throughput, completions and errors | Primary capacity source of truth |
| `vllm bench sweep serve` | Repeated serving sweeps and cache-reset isolation | Candidate orchestrator; use only if its saved schema remains compatible |
| `vllm bench startup` | Startup/load timing | Optional separately labelled measurement |
| `vllm bench latency` | Offline latency/static-batch behavior | Optional; never mix with online serving results |
| `vllm bench throughput` | Offline maximum-throughput behavior | Optional; never present as online capacity |
| Official timeline plots | Visualize arrivals, scheduling and inter-token gaps | Diagnostic supplement, not source metrics |
| Official dataset helpers | Construct supported deterministic workloads | Use when they preserve the controlled matrix |

vLLM sweep or auto-tuning facilities are appropriate only after the fixed baseline
matrix. They search an objective and may choose different settings per variant,
which makes them unsuitable as the primary controlled comparison. Any future tuned
run must use a separate run ID and must record its search space, objective,
constraints, cache policy, winning configuration, and official raw results.

No tuning utility has been run for this project.
