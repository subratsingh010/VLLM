#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
PID_FILE="$ROOT/pipeline_a/logs/model-server.pid"
if [ ! -f "$PID_FILE" ]; then
  exit 0
fi
PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
  kill -TERM "$PID"
  COUNT=0
  while kill -0 "$PID" 2>/dev/null && [ "$COUNT" -lt 30 ]; do
    sleep 1
    COUNT=$((COUNT + 1))
  done
fi
rm -f "$PID_FILE"
