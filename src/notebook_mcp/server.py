from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .analyzer import analyze_notebook, export_notebook_to_script, get_focused_context
from .execution_manager import ExecutionManager
from .jupyter_server import JupyterServerClient
from .kernel_channels import inspect_variable
from .state_engine import build_rerun_plan, compute_notebook_state

mcp = FastMCP("Notebook MCP")


@mcp.tool()
def notebook_analyze(
    path: str,
    strip_outputs: bool = True,
    include_markdown: bool = True,
) -> dict:
    """Analyze a notebook and return structured cell info and dependency edges."""
    analysis = analyze_notebook(path, strip_outputs=strip_outputs, include_markdown=include_markdown)
    return analysis.model_dump()


@mcp.tool()
def notebook_context(
    path: str,
    focus_cell_id: str,
    max_cells: int = 25,
    include_markdown: bool = True,
) -> dict:
    """Return a focused, dependency-aware context slice for a given cell."""
    ctx = get_focused_context(
        path,
        focus_cell_id=focus_cell_id,
        max_cells=max_cells,
        include_markdown=include_markdown,
    )
    return ctx.model_dump()


@mcp.tool()
def notebook_export_script(
    path: str,
    include_markdown_as_comments: bool = False,
) -> str:
    """Export notebook code to a best-effort deterministic Python script."""
    return export_notebook_to_script(path, include_markdown_as_comments=include_markdown_as_comments)


@mcp.tool()
def notebook_state(
    path: str,
    strip_outputs: bool = True,
    include_markdown: bool = True,
) -> dict:
    """Compute best-effort execution state for each cell using execution_count + dependency edges."""
    analysis = analyze_notebook(path, strip_outputs=strip_outputs, include_markdown=include_markdown)
    state = compute_notebook_state(analysis)
    return state.model_dump()


@mcp.tool()
def notebook_rerun_plan(
    path: str,
    focus_cell_id: str,
    strip_outputs: bool = True,
    include_markdown: bool = True,
) -> dict:
    """Recommend a rerun plan (best-effort offline) for a focus cell."""
    analysis = analyze_notebook(path, strip_outputs=strip_outputs, include_markdown=include_markdown)
    plan = build_rerun_plan(analysis, focus_cell_id=focus_cell_id)
    return plan.model_dump()


def _jupyter_client() -> JupyterServerClient:
    base_url = os.environ.get("JUPYTER_BASE_URL")
    if not base_url:
        raise ValueError("JUPYTER_BASE_URL is not set")
    token = os.environ.get("JUPYTER_TOKEN")
    return JupyterServerClient(base_url=base_url, token=token)


_execution_manager_singleton: ExecutionManager | None = None
_execution_manager_key: tuple[str, str | None] | None = None


def _execution_manager() -> ExecutionManager:
    global _execution_manager_singleton, _execution_manager_key  # noqa: PLW0603

    base_url = os.environ.get("JUPYTER_BASE_URL")
    if not base_url:
        raise ValueError("JUPYTER_BASE_URL is not set")
    token = os.environ.get("JUPYTER_TOKEN")
    key = (base_url, token)

    if _execution_manager_singleton is None or _execution_manager_key != key:
        _execution_manager_singleton = ExecutionManager(base_url=base_url, token=token)
        _execution_manager_key = key
    return _execution_manager_singleton


def _legacy_output_from_task(task) -> dict:
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    result = None
    err = None

    for o in task.outputs:
        if not isinstance(o, dict):
            continue
        if o.get("type") == "stream":
            if o.get("name") == "stdout":
                stdout_parts.append(o.get("text") or "")
            elif o.get("name") == "stderr":
                stderr_parts.append(o.get("text") or "")
        elif o.get("type") == "execute_result":
            c = o.get("content") or {}
            data = c.get("data") or {}
            if isinstance(data, dict) and "text/plain" in data:
                result = data["text/plain"]
            else:
                result = data
        elif o.get("type") == "error":
            c = o.get("content") or {}
            err = {
                "name": c.get("ename"),
                "value": c.get("evalue"),
                "traceback": c.get("traceback"),
            }

    if task.status == "failed" and err is None:
        err = {"name": "ExecutionFailed", "value": task.error, "traceback": None}

    return {
        "status": "ok" if task.status == "completed" else "error",
        "execution_count": None,
        "stdout": "".join(stdout_parts),
        "stderr": "".join(stderr_parts),
        "result": result,
        "error": err,
    }


@mcp.tool()
def jupyter_list_sessions() -> list[dict]:
    """List Jupyter Server sessions (requires JUPYTER_BASE_URL and optional JUPYTER_TOKEN)."""
    c = _jupyter_client()
    try:
        return [s.model_dump() for s in c.list_sessions()]
    finally:
        c.close()


@mcp.tool()
def jupyter_get_kernel(kernel_id: str) -> dict:
    """Get kernel metadata from Jupyter Server."""
    c = _jupyter_client()
    try:
        return c.get_kernel(kernel_id).model_dump()
    finally:
        c.close()


@mcp.tool()
async def jupyter_execute(
    kernel_id: str,
    code: str,
    timeout_s: float = 15.0,
) -> dict:
    """Execute code on a Jupyter kernel via Jupyter Server websocket channels.

    Requires:
    - JUPYTER_BASE_URL
    - JUPYTER_TOKEN (optional)
    """
    em = _execution_manager()
    execution_id = await em.submit_execution(kernel_id, code, timeout_s=timeout_s)
    task = await em.wait_for_completion(execution_id, timeout_s=timeout_s)
    return _legacy_output_from_task(task)


@mcp.tool()
async def jupyter_execution_submit(
    kernel_id: str,
    code: str,
    timeout_s: float = 15.0,
) -> dict:
    em = _execution_manager()
    execution_id = await em.submit_execution(kernel_id, code, timeout_s=timeout_s)
    return {"execution_id": execution_id, "status": em.get_execution_status(execution_id)}


@mcp.tool()
def jupyter_execution_status(execution_id: str) -> dict:
    em = _execution_manager()
    return {"execution_id": execution_id, "status": em.get_execution_status(execution_id)}


@mcp.tool()
def jupyter_execution_output(execution_id: str) -> dict:
    em = _execution_manager()
    return {"execution_id": execution_id, "outputs": em.get_execution_output(execution_id)}


@mcp.tool()
def jupyter_execution_cancel(execution_id: str) -> dict:
    em = _execution_manager()
    em.cancel_execution(execution_id)
    return {"execution_id": execution_id, "status": em.get_execution_status(execution_id)}


@mcp.tool()
async def jupyter_inspect(
    kernel_id: str,
    expression: str,
    timeout_s: float = 10.0,
) -> dict:
    """Inspect an expression on a kernel using user_expressions (repr + type).

    Requires:
    - JUPYTER_BASE_URL
    - JUPYTER_TOKEN (optional)
    """
    base_url = os.environ.get("JUPYTER_BASE_URL")
    if not base_url:
        raise ValueError("JUPYTER_BASE_URL is not set")
    token = os.environ.get("JUPYTER_TOKEN")
    return await inspect_variable(
        base_url=base_url,
        token=token,
        kernel_id=kernel_id,
        expression=expression,
        timeout_s=timeout_s,
    )


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "streamable-http":
        host = os.environ.get("MCP_HOST", "127.0.0.1")
        port = int(os.environ.get("MCP_PORT", "8000"))
        mcp.run(transport="streamable-http", host=host, port=port, json_response=True)
        return

    # Default to stdio.
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
