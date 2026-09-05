from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import ORJSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from gateway.app.admission import AdmissionController, OverloadedError
from gateway.app.config import get_settings
from gateway.app.metrics import ACTIVE, LATENCY, QUEUE_WAIT, QUEUED, REQUESTS
from gateway.app.models import ChatCompletionRequest

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.settings = settings
    app.state.admission = AdmissionController(
        settings.max_active_requests, settings.max_queued_requests, settings.queue_timeout_seconds
    )
    app.state.client = httpx.AsyncClient(
        base_url=settings.upstream_base_url,
        timeout=httpx.Timeout(settings.upstream_timeout_seconds),
    )
    app.state.ready = True
    yield
    app.state.ready = False
    app.state.admission.stop_accepting()
    await app.state.client.aclose()


app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)


@app.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/ready")
async def ready(request: Request) -> dict[str, str]:
    if not request.app.state.ready:
        raise HTTPException(status_code=503, detail="draining")
    return {"status": "ready"}


@app.get("/metrics")
async def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/v1/chat/completions")
async def chat(payload: ChatCompletionRequest, request: Request) -> StreamingResponse:
    settings = request.app.state.settings
    if len(payload.messages) > settings.max_messages:
        raise HTTPException(status_code=422, detail="too many messages")
    if sum(len(message.content) for message in payload.messages) > settings.max_characters:
        raise HTTPException(status_code=413, detail="request exceeds character safety limit")
    if payload.max_tokens > settings.max_tokens:
        raise HTTPException(status_code=422, detail="max_tokens exceeds configured limit")

    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    body: dict[str, Any] = payload.model_dump(exclude_none=True)
    body["model"] = settings.upstream_model
    body["stream_options"] = {"include_usage": True}
    body["chat_template_kwargs"] = {"enable_thinking": False}
    headers = {"x-request-id": request_id}

    async def stream() -> AsyncIterator[bytes]:
        started = time.perf_counter()
        outcome = "success"
        QUEUED.labels(settings.pipeline).inc()
        try:
            async with request.app.state.admission.admit() as queue_wait:
                QUEUED.labels(settings.pipeline).dec()
                QUEUE_WAIT.labels(settings.pipeline).observe(queue_wait)
                ACTIVE.labels(settings.pipeline).inc()
                try:
                    async with request.app.state.client.stream(
                        "POST", "/v1/chat/completions", json=body, headers=headers
                    ) as upstream:
                        if upstream.status_code >= 400:
                            outcome = "upstream_error"
                            raise HTTPException(upstream.status_code, await upstream.aread())
                        async for chunk in upstream.aiter_bytes():
                            if await request.is_disconnected():
                                outcome = "cancelled"
                                raise asyncio.CancelledError
                            yield chunk
                except httpx.TimeoutException:
                    outcome = "timeout"
                    yield b'event: error\ndata: {"error":"upstream_timeout"}\n\n'
                finally:
                    ACTIVE.labels(settings.pipeline).dec()
        except OverloadedError:
            QUEUED.labels(settings.pipeline).dec()
            outcome = "overloaded"
            yield b'event: error\ndata: {"error":"overloaded"}\n\n'
        except asyncio.CancelledError:
            outcome = "cancelled"
            raise
        finally:
            duration = time.perf_counter() - started
            REQUESTS.labels(settings.pipeline, outcome).inc()
            LATENCY.labels(settings.pipeline, outcome).observe(duration)
            log.info(
                "request_finished",
                request_id=request_id,
                pipeline=settings.pipeline,
                outcome=outcome,
                duration_seconds=duration,
            )

    return StreamingResponse(
        stream(), media_type="text/event-stream", headers={"x-request-id": request_id}
    )
