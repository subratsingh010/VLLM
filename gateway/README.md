# Gateway

The gateway is backend-neutral and forwards the OpenAI-compatible streaming chat endpoint. It provides schema validation, bounded admission, queue timeout, upstream timeout, cancellation on client disconnect, health endpoints, structured completion logs, and bounded-cardinality Prometheus metrics.

`Dockerfile.template` is deliberately non-buildable in Phase 1. Phase 2 resolves and pins a real ARM64 base-image digest and creates the final Dockerfile before any build; an unpinned image must never be used for a measured run.

Token-budget validation requires the pinned Qwen tokenizer and is added in Pipeline A before exposure. The Phase 1 character limit is only a defensive ceiling and is not represented as token validation.
