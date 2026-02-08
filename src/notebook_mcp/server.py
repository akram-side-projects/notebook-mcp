from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from .analyzer import analyze_notebook, export_notebook_to_script, get_focused_context
from .jupyter_server import JupyterServerClient
from .kernel_channels import execute_code, inspect_variable
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
def jupyter_execute(
    kernel_id: str,
    code: str,
    timeout_s: float = 15.0,
) -> dict:
    """Execute code on a Jupyter kernel via Jupyter Server websocket channels.

    Requires:
    - JUPYTER_BASE_URL
    - JUPYTER_TOKEN (optional)
    """
    base_url = os.environ.get("JUPYTER_BASE_URL")
    if not base_url:
        raise ValueError("JUPYTER_BASE_URL is not set")
    token = os.environ.get("JUPYTER_TOKEN")
    return execute_code(base_url=base_url, token=token, kernel_id=kernel_id, code=code, timeout_s=timeout_s)


@mcp.tool()
def jupyter_inspect(
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
    return inspect_variable(
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
