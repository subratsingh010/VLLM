from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class OverloadedError(RuntimeError):
    pass


class AdmissionController:
    def __init__(self, active_limit: int, queue_limit: int, queue_timeout: float) -> None:
        self._slots = asyncio.Semaphore(active_limit)
        self._waiting_slots = asyncio.Semaphore(queue_limit)
        self._queue_timeout = queue_timeout
        self._accepting = True

    @asynccontextmanager
    async def admit(self) -> AsyncIterator[float]:
        if not self._accepting or self._waiting_slots.locked():
            raise OverloadedError("gateway capacity exhausted")
        loop = asyncio.get_running_loop()
        started = loop.time()
        await self._waiting_slots.acquire()
        try:
            try:
                await asyncio.wait_for(self._slots.acquire(), timeout=self._queue_timeout)
            except TimeoutError as exc:
                raise OverloadedError("queue wait timeout") from exc
        finally:
            self._waiting_slots.release()
        try:
            yield loop.time() - started
        finally:
            self._slots.release()

    def stop_accepting(self) -> None:
        self._accepting = False
