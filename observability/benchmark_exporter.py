from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

DATA_ROOT = Path(os.environ.get("BENCHMARK_RESULTS_ROOT", "/data"))
PORT = int(os.environ.get("PORT", "9123"))


def escape(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def sample(name: str, labels: dict[str, object], value: object) -> str:
    rendered = ",".join(f'{key}="{escape(item)}"' for key, item in sorted(labels.items()))
    return f"{name}{{{rendered}}} {float(value)}"


def identity(path: Path, official: dict[str, Any]) -> dict[str, str]:
    relative = path.relative_to(DATA_ROOT)
    parts = relative.parts
    pipeline = str(official.get("pipeline") or (parts[0] if parts else "unknown"))
    point = path.parent.name
    run = "/".join(parts[:-2]) or pipeline
    return {"pipeline": pipeline, "run": run, "point": point}


def resource_maxima(path: Path) -> dict[str, float]:
    resource_path = path.parent / "resources.jsonl"
    values = {"memory_percent": 0.0, "swap_bytes": 0.0, "kv_cache_percent": 0.0}
    if not resource_path.is_file():
        return values
    for line in resource_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            resource = json.loads(line)
        except json.JSONDecodeError:
            continue
        values["memory_percent"] = max(values["memory_percent"], float(resource.get("system_memory_percent", 0)))
        values["swap_bytes"] = max(values["swap_bytes"], float(resource.get("swap_used_bytes", 0)))
        for metric in resource.get("vllm_metrics", []):
            if metric.get("name") == "vllm:kv_cache_usage_perc":
                values["kv_cache_percent"] = max(
                    values["kv_cache_percent"], float(metric.get("value", 0)) * 100
                )
    return values


def render_metrics() -> bytes:
    lines = [
        "# HELP llm_benchmark_latency_milliseconds Saved official vLLM latency percentile.",
        "# TYPE llm_benchmark_latency_milliseconds gauge",
        "# HELP llm_benchmark_throughput Saved official vLLM throughput.",
        "# TYPE llm_benchmark_throughput gauge",
        "# HELP llm_benchmark_requests Saved official vLLM request outcomes.",
        "# TYPE llm_benchmark_requests gauge",
        "# HELP llm_benchmark_resource Saved peak host or KV resource observation.",
        "# TYPE llm_benchmark_resource gauge",
    ]
    for path in sorted(DATA_ROOT.glob("**/official.json")):
        try:
            official = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        labels = identity(path, official)
        for metric in ("ttft", "tpot", "itl", "e2el"):
            for quantile in ("50", "95", "99"):
                key = f"p{quantile}_{metric}_ms"
                if key in official:
                    lines.append(
                        sample(
                            "llm_benchmark_latency_milliseconds",
                            {**labels, "metric": metric, "quantile": f"0.{quantile}"},
                            official[key],
                        )
                    )
        for key, kind in (
            ("request_throughput", "requests_per_second"),
            ("output_throughput", "output_tokens_per_second"),
            ("total_token_throughput", "total_tokens_per_second"),
        ):
            if key in official:
                lines.append(sample("llm_benchmark_throughput", {**labels, "kind": kind}, official[key]))
        for key in ("completed", "failed"):
            lines.append(sample("llm_benchmark_requests", {**labels, "outcome": key}, official.get(key, 0)))
        for kind, value in resource_maxima(path).items():
            lines.append(sample("llm_benchmark_resource", {**labels, "kind": kind}, value))
    return ("\n".join(lines) + "\n").encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            body, status, content_type = b"ok\n", 200, "text/plain"
        elif self.path == "/metrics":
            body, status, content_type = render_metrics(), 200, "text/plain; version=0.0.4"
        else:
            body, status, content_type = b"not found\n", 404, "text/plain"
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
