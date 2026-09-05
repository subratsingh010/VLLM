from __future__ import annotations

from dataclasses import asdict, dataclass

import psutil


@dataclass(frozen=True)
class ProcessSample:
    timestamp_ns: int
    rss_bytes: int
    cpu_percent: float
    system_available_bytes: int
    swap_used_bytes: int

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


def sample_process(pid: int, timestamp_ns: int) -> ProcessSample:
    process = psutil.Process(pid)
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return ProcessSample(
        timestamp_ns=timestamp_ns,
        rss_bytes=process.memory_info().rss,
        cpu_percent=process.cpu_percent(interval=None),
        system_available_bytes=memory.available,
        swap_used_bytes=swap.used,
    )
