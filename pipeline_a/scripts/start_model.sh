#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VENV=/Users/subrat/.venv-vllm-metal
LOG="$ROOT/pipeline_a/logs/model-server.log"
PID_FILE="$ROOT/pipeline_a/logs/model-server.pid"
"$ROOT/pipeline_a/scripts/verify_artifacts.sh"
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "Pipeline A model server is already running" >&2
  exit 1
fi
STARTED=$(date +%s)
VLLM_METAL_MEMORY_FRACTION=0.70 nohup "$VENV/bin/vllm" serve "$ROOT/models/pipeline_a" \
  --host 127.0.0.1 --port 8101 --served-model-name Qwen/Qwen3-1.7B \
  --dtype bfloat16 --max-model-len 4096 --max-num-seqs 4 \
  >"$LOG" 2>&1 &
PID=$!
echo "$PID" >"$PID_FILE"
echo "$STARTED" >"$ROOT/pipeline_a/logs/model-start-epoch.txt"
echo "Started Pipeline A model server with PID $PID"
