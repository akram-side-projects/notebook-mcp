# Notebook MCP

![Notebook MCP](docs/notebook-mcp-pproduct-img.png)

Notebook MCP is a Model Context Protocol (MCP) server that provides deep semantic understanding of Jupyter notebooks for AI assistants and automation workflows.

---

## 🧠 Why Notebook MCP?

Jupyter notebooks are difficult for AI assistants to reason about because they are:

* Stateful
* Non-linear
* Execution-order dependent
* Mixed with outputs and markdown

Notebook MCP solves this by building execution graphs and runtime awareness.

---

## ✨ Features

* Static notebook dependency analysis
* Execution state detection (stale / unexecuted cells)
* Rerun planning engine
* Focused notebook context generation
* Notebook to deterministic Python conversion
* Jupyter kernel runtime execution and inspection

---

## 📦 Installation

```
pip install notebook-mcp
```

---

## 🚀 Running Server

```
notebook-mcp-python
```

---

## 🔧 Environment Variables (Optional)

For Jupyter runtime integration:

```
JUPYTER_BASE_URL=http://localhost:8888
JUPYTER_TOKEN=<your_token>
```

---

## 🧪 Example Use Cases

* AI notebook debugging
* Automated notebook refactoring
* Execution dependency tracking
* Runtime variable inspection

---

## 🧩 Integration

Notebook MCP is designed to integrate with:

* AI coding assistants
* MCP clients
* Notebook automation workflows

---

## 📚 Source Code

GitHub:
[https://github.com/akram-side-projects/notebook-mcp](https://github.com/akram-side-projects/notebook-mcp)

---

## 🤝 Contributions

PRs and feedback welcome.
