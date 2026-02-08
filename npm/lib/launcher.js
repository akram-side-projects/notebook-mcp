const { spawnSync, spawn } = require("node:child_process");
const process = require("node:process");
const which = require("which");

function findPython() {
  const explicit = process.env.NOTEBOOK_MCP_PYTHON;
  if (explicit) return explicit;

  const candidates = ["python", "python3", "py"]; // py is Windows launcher
  for (const c of candidates) {
    try {
      const p = which.sync(c);
      if (p) return p;
    } catch {
      // ignore
    }
  }
  return null;
}

function runChecked(cmd, args, opts = {}) {
  const res = spawnSync(cmd, args, { stdio: "inherit", ...opts });
  if (res.error) throw res.error;
  if (typeof res.status === "number" && res.status !== 0) {
    const e = new Error(`${cmd} ${args.join(" ")} exited with code ${res.status}`);
    e.exitCode = res.status;
    throw e;
  }
}

function canImportNotebookMcp(python) {
  const res = spawnSync(python, ["-c", "import notebook_mcp"], { stdio: "ignore" });
  return res.status === 0;
}

function ensureInstalled(python) {
  if (canImportNotebookMcp(python)) return;

  const spec = process.env.NOTEBOOK_MCP_PIP_SPEC || "notebook-mcp";
  const extraArgs = (process.env.NOTEBOOK_MCP_PIP_ARGS || "").split(" ").filter(Boolean);

  // Use module invocation so we don't rely on pip.exe being on PATH.
  runChecked(python, ["-m", "pip", "install", "-U", spec, ...extraArgs]);

  if (!canImportNotebookMcp(python)) {
    throw new Error(
      "Installed notebook-mcp but it is still not importable. " +
        "Check that your Python environment is the one you expect (NOTEBOOK_MCP_PYTHON)."
    );
  }
}

async function launch(argv) {
  const python = findPython();
  if (!python) {
    throw new Error(
      "Python was not found on PATH. Install Python 3.11+ and ensure `python` is available, " +
        "or set NOTEBOOK_MCP_PYTHON to the full path of your python executable."
    );
  }

  ensureInstalled(python);

  // Run as module so this works even if Scripts/ is not on PATH.
  const child = spawn(python, ["-m", "notebook_mcp.server", ...argv], {
    stdio: "inherit",
    env: process.env,
  });

  return new Promise((resolve, reject) => {
    child.on("error", reject);
    child.on("exit", (code, signal) => {
      if (signal) {
        const e = new Error(`notebook-mcp exited due to signal ${signal}`);
        e.exitCode = 1;
        reject(e);
        return;
      }
      resolve(code || 0);
    });
  });
}

module.exports = { launch };
