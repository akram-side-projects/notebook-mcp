from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import websockets

from .errors import JupyterServerError
from .models import ExecutionTask

import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecuteResult:
    status: str
    execution_count: int | None
    stdout: str
    stderr: str
    result: Any | None
    error_name: str | None
    error_value: str | None
    traceback: list[str] | None


def _ws_url(base_url: str, kernel_id: str, token: str | None) -> str:
    b = base_url.rstrip("/")
    if b.startswith("https://"):
        ws_base = "wss://" + b.removeprefix("https://")
    elif b.startswith("http://"):
        ws_base = "ws://" + b.removeprefix("http://")
    else:
        ws_base = "ws://" + b

    url = f"{ws_base}/api/kernels/{kernel_id}/channels"
    if token:
        url = f"{url}?token={token}"
    return url


def _now_iso() -> str:
    # Good enough for protocol; server does not require strict formatting.
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())


def _make_header(msg_type: str, session: str) -> dict[str, Any]:
    return {
        "msg_id": uuid.uuid4().hex,
        "username": "notebook-mcp",
        "session": session,
        "date": _now_iso(),
        "msg_type": msg_type,
        "version": "5.3",
    }


async def _execute_via_ws(
    *,
    base_url: str,
    token: str | None,
    kernel_id: str,
    code: str,
    timeout_s: float,
    user_expressions: dict[str, str] | None,
) -> ExecuteResult:
    ws = _ws_url(base_url, kernel_id, token)
    session = uuid.uuid4().hex

    request = {
        "header": _make_header("execute_request", session),
        "parent_header": {},
        "metadata": {},
        "content": {
            "code": code,
            "silent": False,
            "store_history": False,
            "user_expressions": user_expressions or {},
            "allow_stdin": False,
            "stop_on_error": True,
        },
        "channel": "shell",
        "buffers": [],
    }

    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    result: Any | None = None
    error_name: str | None = None
    error_value: str | None = None
    traceback: list[str] | None = None
    execution_count: int | None = None

    deadline = time.time() + timeout_s

    try:
        async with websockets.connect(ws, max_size=16 * 1024 * 1024, open_timeout=10) as sock:
            await sock.send(json.dumps(request))

            got_execute_reply = False
            got_idle = False

            while time.time() < deadline:
                remaining = max(0.1, deadline - time.time())
                raw = await asyncio.wait_for(sock.recv(), timeout=remaining)
                if not isinstance(raw, str):
                    # Jupyter typically sends text frames.
                    continue

                msg = json.loads(raw)
                msg_type = (msg.get("header") or {}).get("msg_type")
                channel = msg.get("channel")
                content = msg.get("content") or {}

                if msg_type == "stream" and channel == "iopub":
                    name = content.get("name")
                    text = content.get("text") or ""
                    if name == "stdout":
                        stdout_parts.append(text)
                    elif name == "stderr":
                        stderr_parts.append(text)

                elif msg_type == "execute_result" and channel == "iopub":
                    execution_count = content.get("execution_count")
                    data = content.get("data") or {}
                    # Prefer text/plain.
                    if "text/plain" in data:
                        result = data["text/plain"]
                    else:
                        result = data

                elif msg_type == "error" and channel == "iopub":
                    error_name = content.get("ename")
                    error_value = content.get("evalue")
                    tb = content.get("traceback")
                    if isinstance(tb, list):
                        traceback = tb

                elif msg_type == "execute_reply" and channel == "shell":
                    got_execute_reply = True
                    execution_count = content.get("execution_count")
                    if content.get("status") == "error":
                        error_name = error_name or content.get("ename")
                        error_value = error_value or content.get("evalue")
                        tb = content.get("traceback")
                        if isinstance(tb, list):
                            traceback = tb

                    # user_expressions results come back here too.
                    ue = content.get("user_expressions") or {}
                    if isinstance(ue, dict) and ue:
                        result = ue

                elif msg_type == "status" and channel == "iopub":
                    if content.get("execution_state") == "idle":
                        got_idle = True

                if got_execute_reply and got_idle:
                    break

    except Exception as e:  # noqa: BLE001
        raise JupyterServerError(f"Kernel websocket execution failed for kernel_id={kernel_id}") from e

    status = "error" if error_name else "ok"
    return ExecuteResult(
        status=status,
        execution_count=execution_count,
        stdout="".join(stdout_parts),
        stderr="".join(stderr_parts),
        result=result,
        error_name=error_name,
        error_value=error_value,
        traceback=traceback,
    )


@dataclass
class _QueueItem:
    task: ExecutionTask
    timeout_s: float


class KernelWorker:
    def __init__(self, *, base_url: str, token: str | None, kernel_id: str) -> None:
        self._base_url = base_url
        self._token = token
        self._kernel_id = kernel_id

        self._queue: asyncio.Queue[_QueueItem] = asyncio.Queue()
        self._runner: asyncio.Task[None] | None = None
        self._closed = False

        self._cancelled: set[str] = set()
        self._current: str | None = None
        self._sock: websockets.WebSocketClientProtocol | None = None

    @property
    def is_closed(self) -> bool:
        return self._closed

    def enqueue(self, task: ExecutionTask, *, timeout_s: float) -> None:
        if self._closed:
            raise JupyterServerError(f"Kernel worker is closed for kernel_id={self._kernel_id}")
        self._queue.put_nowait(_QueueItem(task=task, timeout_s=timeout_s))
        if self._runner is None or self._runner.done():
            self._runner = asyncio.create_task(self._run(), name=f"kernel-worker:{self._kernel_id}")

    def cancel(self, execution_id: str) -> None:
        self._cancelled.add(execution_id)
        # Best-effort: we only mark the execution as cancelled; we do not send
        # an interrupt request (requires additional Jupyter REST calls) and we do
        # not tear down the worker connection.

    def close(self) -> None:
        self._closed = True
        if self._sock is not None:
            asyncio.create_task(self._sock.close())
        if self._runner is not None:
            self._runner.cancel()

    def _mark_failed(self, task: ExecutionTask, msg: str) -> None:
        task.status = "failed"
        task.error = msg
        task.updated_at = datetime.now(UTC)

    async def _run(self) -> None:
        ws = _ws_url(self._base_url, self._kernel_id, self._token)
        try:
            async with websockets.connect(ws, max_size=16 * 1024 * 1024, open_timeout=10) as sock:
                self._sock = sock
                while not self._closed:
                    item = await self._queue.get()
                    task = item.task

                    if task.execution_id in self._cancelled:
                        self._cancelled.discard(task.execution_id)
                        self._mark_failed(task, "cancelled")
                        self._queue.task_done()
                        continue

                    self._current = task.execution_id
                    task.status = "running"
                    task.updated_at = datetime.now(UTC)
                    logger.info(
                        "execution_started",
                        extra={"execution_id": task.execution_id, "kernel_id": self._kernel_id},
                    )

                    try:
                        await self._execute_one(sock, task, timeout_s=item.timeout_s)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:  # noqa: BLE001
                        self._mark_failed(task, "websocket_execution_failed")
                        logger.info(
                            "execution_failed",
                            extra={
                                "execution_id": task.execution_id,
                                "kernel_id": self._kernel_id,
                                "error": str(e),
                            },
                        )

                    self._current = None
                    self._queue.task_done()

        except Exception as e:  # noqa: BLE001
            # Mark anything currently queued as failed; worker will be recreated lazily.
            try:
                while True:
                    item = self._queue.get_nowait()
                    self._mark_failed(item.task, "kernel_worker_disconnected")
                    self._queue.task_done()
            except asyncio.QueueEmpty:
                pass
            logger.info(
                "execution_failed",
                extra={"kernel_id": self._kernel_id, "error": f"kernel_worker_disconnected:{e}"},
            )
            return
        finally:
            self._sock = None
            self._closed = True

    async def _execute_one(
        self,
        sock: websockets.WebSocketClientProtocol,
        task: ExecutionTask,
        *,
        timeout_s: float,
    ) -> None:
        session = uuid.uuid4().hex
        header = _make_header("execute_request", session)
        request_msg_id = header["msg_id"]
        request = {
            "header": header,
            "parent_header": {},
            "metadata": {},
            "content": {
                "code": task.code,
                "silent": False,
                "store_history": False,
                "user_expressions": {},
                "allow_stdin": False,
                "stop_on_error": True,
            },
            "channel": "shell",
            "buffers": [],
        }

        await sock.send(json.dumps(request))
        deadline = time.time() + timeout_s

        got_execute_reply = False
        got_idle = False
        saw_error = False

        while time.time() < deadline and not self._closed:
            if task.execution_id in self._cancelled:
                self._cancelled.discard(task.execution_id)
                self._mark_failed(task, "cancelled")
                return

            remaining = max(0.1, deadline - time.time())
            raw = await asyncio.wait_for(sock.recv(), timeout=remaining)
            if not isinstance(raw, str):
                continue

            msg = json.loads(raw)
            msg_type = (msg.get("header") or {}).get("msg_type")
            channel = msg.get("channel")
            content = msg.get("content") or {}
            parent = msg.get("parent_header") or {}
            parent_id = parent.get("msg_id")

            # Filter to messages for this execute_request where possible.
            if parent_id and parent_id != request_msg_id:
                continue

            if msg_type == "stream" and channel == "iopub":
                name = content.get("name")
                text = content.get("text") or ""
                task.outputs.append({"type": "stream", "name": name, "text": text})
                task.updated_at = datetime.now(UTC)

            elif msg_type == "execute_result" and channel == "iopub":
                task.outputs.append({"type": "execute_result", "content": content})
                task.updated_at = datetime.now(UTC)

            elif msg_type == "display_data" and channel == "iopub":
                task.outputs.append({"type": "display_data", "content": content})
                task.updated_at = datetime.now(UTC)

            elif msg_type == "error" and channel == "iopub":
                saw_error = True
                task.outputs.append({"type": "error", "content": content})
                task.updated_at = datetime.now(UTC)

            elif msg_type == "execute_reply" and channel == "shell":
                got_execute_reply = True
                if content.get("status") == "error":
                    saw_error = True

            elif msg_type == "status" and channel == "iopub":
                if content.get("execution_state") == "idle":
                    got_idle = True

            if got_execute_reply and got_idle:
                break

        if not (got_execute_reply and got_idle):
            self._mark_failed(task, "timeout")
            logger.info(
                "execution_failed",
                extra={"execution_id": task.execution_id, "kernel_id": self._kernel_id, "error": "timeout"},
            )
            return

        if saw_error:
            self._mark_failed(task, "error")
            logger.info(
                "execution_failed",
                extra={"execution_id": task.execution_id, "kernel_id": self._kernel_id, "error": "error"},
            )
            return

        task.status = "completed"
        task.updated_at = datetime.now(UTC)
        logger.info(
            "execution_completed",
            extra={"execution_id": task.execution_id, "kernel_id": self._kernel_id},
        )


async def execute_code(
    *,
    base_url: str,
    token: str | None,
    kernel_id: str,
    code: str,
    timeout_s: float = 15.0,
    user_expressions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Execute code on a Jupyter kernel via the Jupyter Server websocket channels endpoint.

    This is best-effort: it collects stdout/stderr and returns execute_result/error when available.
    """

    res = await _execute_via_ws(
        base_url=base_url,
        token=token,
        kernel_id=kernel_id,
        code=code,
        timeout_s=timeout_s,
        user_expressions=user_expressions,
    )

    return {
        "status": res.status,
        "execution_count": res.execution_count,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "result": res.result,
        "error": {
            "name": res.error_name,
            "value": res.error_value,
            "traceback": res.traceback,
        }
        if res.error_name
        else None,
    }


async def inspect_variable(
    *,
    base_url: str,
    token: str | None,
    kernel_id: str,
    expression: str,
    timeout_s: float = 10.0,
) -> dict[str, Any]:
    """Inspect an expression by evaluating it via user_expressions.

    Returns a structured dict of text/plain representations when available.
    """

    ue = {
        "type": f"type({expression}).__name__",
        "repr": f"repr({expression})",
    }

    return await execute_code(
        base_url=base_url,
        token=token,
        kernel_id=kernel_id,
        code="",  # no-op; we only use user_expressions
        timeout_s=timeout_s,
        user_expressions=ue,
    )


async def asyncio_wait_for(awaitable, timeout: float):
    return await asyncio.wait_for(awaitable, timeout=timeout)
