from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from .models import ExecutionTask
from .kernel_channels import KernelWorker

logger = logging.getLogger(__name__)


@dataclass
class _ExecutionMeta:
    timeout_s: float


class ExecutionManager:
    def __init__(self, *, base_url: str, token: str | None) -> None:
        self._base_url = base_url
        self._token = token
        self._tasks: dict[str, ExecutionTask] = {}
        self._task_meta: dict[str, _ExecutionMeta] = {}
        self._workers: dict[str, KernelWorker] = {}
        self._lock = asyncio.Lock()

    async def submit_execution(self, kernel_id: str, code: str, *, timeout_s: float = 15.0) -> str:
        execution_id = uuid.uuid4().hex
        now = datetime.now(UTC)
        task = ExecutionTask(
            execution_id=execution_id,
            kernel_id=kernel_id,
            code=code,
            status="pending",
            outputs=[],
            created_at=now,
            updated_at=now,
            error=None,
        )

        async with self._lock:
            self._tasks[execution_id] = task
            self._task_meta[execution_id] = _ExecutionMeta(timeout_s=timeout_s)
            worker = self._workers.get(kernel_id)
            if worker is None or worker.is_closed:
                worker = KernelWorker(base_url=self._base_url, token=self._token, kernel_id=kernel_id)
                self._workers[kernel_id] = worker
            worker.enqueue(task, timeout_s=timeout_s)

        logger.info(
            "execution_submitted",
            extra={"execution_id": execution_id, "kernel_id": kernel_id},
        )
        return execution_id

    def _task(self, execution_id: str) -> ExecutionTask:
        t = self._tasks.get(execution_id)
        if not t:
            raise KeyError(f"Unknown execution_id={execution_id}")
        return t

    def get_execution_status(self, execution_id: str) -> str:
        return self._task(execution_id).status

    def get_execution_output(self, execution_id: str) -> list:
        return list(self._task(execution_id).outputs)

    def cancel_execution(self, execution_id: str) -> None:
        t = self._task(execution_id)
        if t.status in ("completed", "failed"):
            return
        t.status = "failed"
        t.error = "cancelled"
        t.updated_at = datetime.now(UTC)
        worker = self._workers.get(t.kernel_id)
        if worker is not None:
            worker.cancel(execution_id)

    async def wait_for_completion(self, execution_id: str, *, timeout_s: float) -> ExecutionTask:
        start = time.time()
        while True:
            t = self._task(execution_id)
            if t.status in ("completed", "failed"):
                return t
            if time.time() - start > timeout_s:
                t.status = "failed"
                t.error = "timeout"
                t.updated_at = datetime.now(UTC)
                return t
            await asyncio.sleep(0.05)

    def drop_kernel_worker(self, kernel_id: str) -> None:
        w = self._workers.pop(kernel_id, None)
        if w is not None:
            w.close()
