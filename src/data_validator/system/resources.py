from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import psutil


@dataclass(slots=True)
class ResourcePlan:
    available_memory_bytes: int
    memory_limit_mb: int
    threads: int
    temp_directory: Path
    free_temp_bytes: int


def choose_resource_plan(
    temp_directory: Path,
    memory_limit_mb: int | None = None,
    threads: int | None = None,
) -> ResourcePlan:
    temp_directory = Path(temp_directory).resolve()
    temp_directory.mkdir(parents=True, exist_ok=True)
    vm = psutil.virtual_memory()
    available = int(vm.available)
    memory_mb = memory_limit_mb or max(512, int((available * 0.55) / (1024 * 1024)))
    physical = psutil.cpu_count(logical=False) or psutil.cpu_count(logical=True) or 1
    memory_gb = max(1, memory_mb // 1024)
    suggested_threads = max(1, min(physical, max(1, memory_gb // 2)))
    thread_count = threads or suggested_threads
    free = shutil.disk_usage(temp_directory).free
    return ResourcePlan(
        available_memory_bytes=available,
        memory_limit_mb=int(memory_mb),
        threads=int(max(1, thread_count)),
        temp_directory=temp_directory,
        free_temp_bytes=int(free),
    )


def estimate_temp_bytes(input_bytes: int) -> int:
    return int(input_bytes * 2.5) + 512 * 1024 * 1024
