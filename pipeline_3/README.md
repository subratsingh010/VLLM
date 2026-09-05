# Pipeline 3 — vLLM-Metal serving auto-tuning

Pipeline 3 is a thin, user-started controller around official
`vllm bench sweep serve`. It does not implement TTFT, TPOT, ITL, latency, or
throughput calculations.

## Scope

The first stage tunes only Metal-relevant server scheduling limits:

- `max_num_seqs`: 1, 2, 4
- `max_num_batched_tokens`: 1,024 or 2,048
- Fixed `VLLM_METAL_MEMORY_FRACTION=0.70`
- Prefix caching disabled
- Fixed 512-input/64-output workload
- One exploratory run per candidate

This produces six linked candidates. CUDA graphs, Triton kernels, FlashAttention,
tensor parallelism, AWQ/GPTQ kernels, and CUDA kernel-fusion settings are not
included because they are unavailable or irrelevant on this M2 Metal backend.
Native Metal kernel selection remains the responsibility of vLLM-Metal.

## Safety and scientific boundaries

- A complete, artifact-verified Pipeline B variant run is required as input.
- Preparing a tuning run writes files only.
- The sweep requires explicit `--execute`; `--dry-run` is available first.
- Official vLLM owns server lifecycle, cache clearing, resume checkpoints, and
  benchmark metrics.
- Candidate count is capped at six for the first stage.
- The winner must satisfy P95 TTFT <= 5 s, P95 E2E <= 20 s, and zero failures.
- The winner is provisional until repeated three times and validated with the full
  Pipeline A capacity matrix.
- Tuning results are not mixed with controlled Pipeline A/B baseline results.

## Manual workflow

```bash
# Requires a completed Pipeline B run.
.venv/bin/python -m pipeline_3.scripts.prepare_tuning \
  --variant-run pipeline_b/results/fp16/fp16-20260905 \
  --tuning-run-id fp16-tune-20260905

# Inspect official commands without running them.
pipeline_3/scripts/run_sweep.sh \
  pipeline_3/results/fp16/fp16-tune-20260905 --dry-run

# Long-running, explicitly user-started official sweep.
pipeline_3/scripts/run_sweep.sh \
  pipeline_3/results/fp16/fp16-tune-20260905 --execute

# Offline ranking from saved official JSON only.
.venv/bin/python -m pipeline_3.scripts.rank_results \
  --tuning-run pipeline_3/results/fp16/fp16-tune-20260905
```

Use `--execute --resume` only for an interrupted existing official sweep.
