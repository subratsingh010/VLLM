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
test -f "$RUN/metadata/artifact_inventory.json" || { echo "artifacts are not verified" >&2; exit 1; }
CONVERSION=$(jq -r --arg v "$VARIANT" '.variants[$v].conversion // empty' "$CONFIG")
PORT=$(jq -r --arg v "$VARIANT" '.variants[$v].port // empty' "$CONFIG")
PRECISION=$(jq -r --arg v "$VARIANT" '.variants[$v].precision // empty' "$CONFIG")
test -n "$CONVERSION" || { echo "unsupported variant: $VARIANT" >&2; exit 1; }
if [ "$CONVERSION" = "mlx_lm" ]; then
  MODEL="$ROOT/pipeline_b/converted_models/$VARIANT/$RUN_ID"
  DTYPE=auto
else
  MODEL="$ROOT/models/pipeline_a"
  DTYPE=$PRECISION
fi
test -d "$MODEL" || { echo "model path is missing: $MODEL" >&2; exit 1; }
ARGV="$RUN/serving/command.txt"
printf '%s\n' "VLLM_METAL_MEMORY_FRACTION=0.70 vllm serve $MODEL --host 127.0.0.1 --port $PORT --served-model-name Qwen/Qwen3-1.7B --dtype $DTYPE --max-model-len 4096 --max-num-seqs 4 --generation-config vllm --no-enable-prefix-caching" > "$ARGV"
cd "$ROOT"
.venv/bin/python -m pipeline_b.scripts.mark_state --variant "$VARIANT" --run-id "$RUN_ID" --target serving_started >/dev/null
echo "Recorded command in $ARGV"
echo "This script now starts a model server. Press Ctrl-C to stop it."
VLLM_METAL_MEMORY_FRACTION=0.70 exec /Users/subrat/.venv-vllm-metal/bin/vllm serve "$MODEL" \
  --host 127.0.0.1 --port "$PORT" --served-model-name Qwen/Qwen3-1.7B \
  --dtype "$DTYPE" --max-model-len 4096 --max-num-seqs 4 \
  --generation-config vllm --no-enable-prefix-caching
