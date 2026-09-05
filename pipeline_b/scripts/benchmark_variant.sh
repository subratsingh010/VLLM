#!/bin/sh
set -eu
if [ "$#" -ne 2 ]; then
  echo "usage: $0 VARIANT RUN_ID" >&2
  exit 2
fi
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VARIANT=$1
RUN_ID=$2
RUN="$ROOT/pipeline_b/results/$VARIANT/$RUN_ID"
CONFIG="$ROOT/pipeline_b/config/variants.json"
test -f "$RUN/RUN_STATUS.json" || { echo "run is not prepared: $RUN" >&2; exit 1; }
STATE=$(jq -r '.status' "$RUN/RUN_STATUS.json")
test "$STATE" = "serving_started" || { echo "run state must be serving_started, got: $STATE" >&2; exit 1; }
PORT=$(jq -r --arg v "$VARIANT" '.variants[$v].port // empty' "$CONFIG")
CONVERSION=$(jq -r --arg v "$VARIANT" '.variants[$v].conversion // empty' "$CONFIG")
if [ "$CONVERSION" = "mlx_lm" ]; then
  MODEL="$ROOT/pipeline_b/converted_models/$VARIANT/$RUN_ID"
else
  MODEL="$ROOT/models/pipeline_a"
fi
cd "$ROOT"
curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null || { echo "model server is not healthy" >&2; exit 1; }
.venv/bin/python -m benchmark.official_runner \
  --pipeline "pipeline_b/$VARIANT/$RUN_ID" \
  --base-url "http://127.0.0.1:$PORT" \
  --served-model Qwen/Qwen3-1.7B \
  --model-path "$MODEL" \
  --output-dir "$RUN/benchmark" \
  --metrics-url "http://127.0.0.1:$PORT/metrics" \
  --matrix-path "$RUN/metadata/benchmark_matrix.json"
.venv/bin/python -m pipeline_b.scripts.validate_benchmark --run "$RUN" >/dev/null
.venv/bin/python -m pipeline_b.scripts.mark_state --variant "$VARIANT" --run-id "$RUN_ID" --target benchmarked >/dev/null
