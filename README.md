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
