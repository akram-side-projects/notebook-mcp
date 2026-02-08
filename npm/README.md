# notebook-mcp (NPM)

This is an NPM wrapper for the **Python** package `notebook-mcp`.

## Install

```bash
npm i -g @akram1110/notebook-mcp
```

## Run

```bash
notebook-mcp
```

## Configuration

- `NOTEBOOK_MCP_PYTHON`: path to the Python executable to use
- `NOTEBOOK_MCP_PIP_SPEC`: pip spec to install (default: `notebook-mcp`)
- `NOTEBOOK_MCP_PIP_ARGS`: extra args passed to `pip install` (space-separated)

Environment variables used by the server:

- `MCP_TRANSPORT`: `stdio` (default) or `streamable-http`
- `MCP_HOST`, `MCP_PORT`
- `JUPYTER_BASE_URL`, `JUPYTER_TOKEN`
