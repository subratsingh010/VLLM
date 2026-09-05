from prometheus_client import Counter, Gauge, Histogram

REQUESTS = Counter(
    "llm_gateway_requests_total",
    "Gateway requests by bounded outcome",
    ["pipeline", "outcome"],
)
ACTIVE = Gauge("llm_gateway_active_requests", "Active upstream requests", ["pipeline"])
QUEUED = Gauge("llm_gateway_queued_requests", "Requests waiting for admission", ["pipeline"])
QUEUE_WAIT = Histogram(
    "llm_gateway_queue_wait_seconds",
    "Time waiting for upstream admission",
    ["pipeline"],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 2, 5),
)
LATENCY = Histogram(
    "llm_gateway_request_duration_seconds",
    "Gateway request duration",
    ["pipeline", "outcome"],
)
