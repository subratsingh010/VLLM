# Pipeline B precision experiment framework

Pipeline B is a manual, variant-isolated framework. Merely preparing or validating
a run never converts, loads, serves, downloads, or benchmarks a model.

## Supported configuration surface

| Variant | Kind | Conversion | Validation state |
|---|---|---|---|
| `bf16` | floating point | none; reuses pinned source | confirmed by Pipeline A |
| `fp16` | floating point | runtime dtype selection | requires a manual preflight |
| `int8_mlx` | integer weight quantization | MLX-LM, 8-bit/group 64 | requires conversion and load validation |
| `int4_mlx` | integer weight quantization | MLX-LM, 4-bit/group 64 | artifact format known; local conversion requires validation |

FP16/BF16 are reduced floating-point precision, not integer quantization. INT8 and
INT4 are group-wise integer weight quantization; runtime compute and KV-cache dtype
remain separately recorded properties.

AWQ, GPTQ, bitsandbytes, FP8, GGUF, KV-cache quantization, and unvalidated MLX bit
widths are deliberately excluded. See `config/variants.json` for machine-readable
reasons.

## Manual workflow

All commands are run from the repository root. Choose a unique run ID.

```bash
.venv/bin/python -m pipeline_b.scripts.validate_variant --variant int4_mlx
.venv/bin/python -m pipeline_b.scripts.prepare_variant \
  --variant int4_mlx --run-id 20260905-int4-g64

# Plan only: this does not convert anything.
.venv/bin/python -m pipeline_b.scripts.quantize \
  --variant int4_mlx --run-id 20260905-int4-g64

# Explicitly authorized conversion.
.venv/bin/python -m pipeline_b.scripts.quantize \
  --variant int4_mlx --run-id 20260905-int4-g64 \
  --execute --confirm 20260905-int4-g64

# Required after conversion; also required for BF16/FP16 before serving.
.venv/bin/python -m pipeline_b.scripts.verify_artifacts \
  --variant int4_mlx --run-id 20260905-int4-g64

pipeline_b/scripts/serve_variant.sh int4_mlx 20260905-int4-g64
pipeline_b/scripts/benchmark_variant.sh int4_mlx 20260905-int4-g64
pipeline_b/scripts/analyze_variant.sh int4_mlx 20260905-int4-g64
.venv/bin/python -m pipeline_b.scripts.finalize_variant \
  --variant int4_mlx --run-id 20260905-int4-g64

.venv/bin/python -m comparison.compare \
  --baseline pipeline_a/results/NEW_PIPELINE_A_RUN \
  --variants-root pipeline_b/results \
  --tuning-root pipeline_3/results \
  --output-dir comparison/results/COMPARE_ID
```

The serving and benchmark commands are intentionally not chained. Each run records
its variant, source revision, matrix hash, environment, commands, logs, official
outputs, resource samples, analysis, model hashes, and optional quality results.

If a server exits before benchmarking, record that explicitly before retrying:

```bash
.venv/bin/python -m pipeline_b.scripts.mark_state \
  --variant int4_mlx --run-id 20260905-int4-g64 --target serving_stopped
```

`finalize_variant` refuses runs without all 12 structurally valid official points,
required analysis files, and a verified model artifact. Failed requests remain
valid saturation evidence and are preserved rather than blocking completion. The comparison ignores
anything not explicitly marked `complete` and rejects matrix mismatches.

## Optional one-command sequential workflow

The batch wrapper remains user-controlled: it does nothing until invoked with
`--execute` and an exact confirmation. It runs FP16, INT8, and INT4 one at a time,
never concurrently. A failure stops the batch before the next variant.

```sh
pipeline_b/scripts/run_all_variants.sh \
  --batch-id 20260906 \
  --execute \
  --confirm 20260906
```

Each variant receives an isolated directory at
`pipeline_b/results/<variant>/<variant>-<batch-id>/`.
