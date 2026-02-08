# Notebook MCP

AI-Native Intelligence for Jupyter Notebooks

Notebook MCP is a Model Context Protocol (MCP) server that gives AI assistants deep semantic and runtime understanding of `.ipynb` notebooks.

---

## 🚀 Motivation

AI coding assistants struggle with notebooks because notebooks rely heavily on execution order and hidden runtime state.

Notebook MCP bridges this gap by converting notebooks into structured, analyzable execution graphs.

---

## ✨ Features

### 📊 Static Notebook Intelligence

* Dependency graph generation
* Variable lineage tracking
* Focused context slicing for LLM reasoning
* Deterministic notebook-to-script export

### ⚡ Execution State Awareness

* Detects stale cells
* Detects unexecuted cells
* Generates rerun plans

### 🔬 Runtime Jupyter Integration

* Execute code inside kernels
* Inspect variables
* Access kernel metadata
* Stream execution results

---

## 🏗️ Architecture

```
Notebook → MCP Server → AI Assistant
```

Core Components:

* AST Analysis Engine
* Dependency Graph Builder
* Execution State Engine
* Jupyter Kernel WebSocket Client
* Context Builder for LLMs

---

## 📦 Installation

### npm (Recommended)

```
npm install -g @akram1110/notebook-mcp
```

---

### Python Backend

```
pip install notebook-mcp
```

---

## ⚙️ Running Server

```
notebook-mcp
```

---

## 🧹 Uninstallation

Notebook MCP installs components via both npm and pip.

Follow the steps below to fully remove the tool.

---

### Step 1 — Remove npm Wrapper

```
npm uninstall -g @akram1110/notebook-mcp
```

---

### Step 2 — Remove Python Backend

```
pip uninstall notebook-mcp
```

or

```
python -m pip uninstall notebook-mcp
```

---

### Step 3 — Confirm Removal

```
notebook-mcp
```

Expected output:

```
command not found
```

---

### Step 4 — Windows Only: Remove Leftover Executables

Python sometimes leaves launcher files behind.

Check:

```
where notebook-mcp
```

If found, delete from:

```
<python_install_dir>\Scripts\
```

Example:

```
C:\Users\<username>\AppData\Local\Programs\Python\Python311\Scripts\
```

---

### Step 5 — Clean Corrupted pip Distribution Warnings

If pip shows:

```
WARNING: Ignoring invalid distribution ~
```

Delete folders beginning with `~` inside:

```
<python_install_dir>\Lib\site-packages\
```

Then verify:

```
pip check
```

---

### Step 6 — Optional Cache Cleanup

```
pip cache purge
```

---

After completing these steps, Notebook MCP will be fully removed from your system.

## 🔌 Cursor Integration

```
{
  "mcpServers": {
    "notebook": {
      "command": "notebook-mcp"
    }
  }
}
```

---

## 🧪 Example MCP Tools

| Tool                | Description                |
| ------------------- | -------------------------- |
| notebook_analyze    | Builds dependency graph    |
| notebook_context    | Generates focused context  |
| notebook_state      | Detects execution state    |
| notebook_rerun_plan | Suggests rerun order       |
| jupyter_execute     | Executes kernel code       |
| jupyter_inspect     | Inspects runtime variables |

---

## 🔧 Jupyter Integration

Set environment variables:

```
JUPYTER_BASE_URL=http://localhost:8888
JUPYTER_TOKEN=<token>
```

---

## 📚 Tech Stack

* Python
* Model Context Protocol (MCP)
* AST Analysis
* NetworkX Graphs
* Jupyter Kernel Protocol
* Node.js CLI Distribution

---

## 🛣️ Roadmap

* Output semantic analysis
* Notebook replay engine
* Incremental notebook graph caching
* Binary distribution support

---

## 🤝 Contributing

Issues and PRs welcome.

---

## 📄 License

MIT License
