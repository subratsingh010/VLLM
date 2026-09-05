# Phase 0 findings

Inspection date: 2026-09-05 Asia/Kolkata.

- Apple M2 MacBook Air, 8 CPU cores, 16 GB unified memory, macOS 26.3.1 ARM64.
- Native Python 3.12.9 and uv are available; vLLM, MLX, and MLX-LM are not installed.
- No local general-purpose LLM weights were present after cache cleanup.
- Existing Compose project `workflow` has 18 running services on `workflow_default`.
- Existing telemetry services: Prometheus 9090, Grafana 3000, Loki 3100, Tempo 3200/4317, Phoenix 6006/internal 4317, and Promtail Docker discovery.
- Current stack memory observed at roughly 4.3 GB across containers; the measurement is a Phase 0 snapshot, not a benchmark result.
- Host-native vLLM-Metal is the intended serving backend because Docker Desktop cannot expose the Mac Metal device to Linux containers.

See `observability/README.md` for the non-duplicating integration design.
