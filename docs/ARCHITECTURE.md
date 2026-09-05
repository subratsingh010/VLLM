# Architecture

```text
benchmark client
    -> FastAPI gateway (Docker, workflow_default)
    -> host.docker.internal
    -> host-native vLLM-Metal
    -> pinned Qwen3 artifact
```

The model server must run natively on macOS because Docker Desktop's Linux VM cannot access Metal. The gateway remains containerized to demonstrate a replaceable model backend, request validation, bounded concurrency, backpressure, streaming, timeouts, cancellation, health checks, and graceful shutdown.

Only one pipeline runs at a time. Pipeline A and B use the same gateway and benchmark code but separate configuration, ports, logs, raw data, processed data, and reports.

## Production concepts and local status

| Concept | Status in this lab |
|---|---|
| Tokenization, prefill, decoding | Exercised by the local Qwen3 server |
| Streaming and cancellation | Exercised end-to-end |
| Gateway queuing/backpressure | Exercised with a bounded semaphore |
| Timeouts and graceful shutdown | Exercised in the gateway |
| Continuous batching | Exercised if exposed by the pinned vLLM-Metal build; verified by metrics |
| Paged KV cache | Exercised by vLLM-Metal's paged backend |
| Prefix caching | Exercised in a dedicated controlled workload, not mixed into baseline results |
| Distributed serving/parallelism | Production-only; not meaningful on one M2 |
| CUDA graphs, tensor parallel GPUs | Production-only and unavailable on Metal |

Claims are finalized only after the Phase A/B capability probes record backend evidence.
