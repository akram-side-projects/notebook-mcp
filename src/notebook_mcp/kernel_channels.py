from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

import websockets

from .errors import JupyterServerError


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
        async with websockets.connect(ws, max_size=16 * 1024 * 1024) as sock:
            await sock.send(json.dumps(request))

            got_execute_reply = False
            got_idle = False

            while time.time() < deadline:
                remaining = max(0.1, deadline - time.time())
                raw = await asyncio_wait_for(sock.recv(), timeout=remaining)
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


def execute_code(
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

    import asyncio

    res = asyncio.run(
        _execute_via_ws(
            base_url=base_url,
            token=token,
            kernel_id=kernel_id,
            code=code,
            timeout_s=timeout_s,
            user_expressions=user_expressions,
        )
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


def inspect_variable(
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

    return execute_code(
        base_url=base_url,
        token=token,
        kernel_id=kernel_id,
        code="",  # no-op; we only use user_expressions
        timeout_s=timeout_s,
        user_expressions=ue,
    )


async def asyncio_wait_for(awaitable, timeout: float):
    import asyncio

    return await asyncio.wait_for(awaitable, timeout=timeout)
