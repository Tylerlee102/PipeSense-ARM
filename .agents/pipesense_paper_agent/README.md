# PipeSense Paper Agent

This is a local Paper2Agent-style wrapper for the PipeSense-ARM repository.
It turns the paper artifact into an MCP server with tools for:

- explaining the paper contribution and claim boundaries
- searching and reading repository evidence
- auditing the research package for evidence and claim discipline
- assessing whether the known research limits are mitigated or still externally open
- running no-simulator artifact checks
- validating generated result CSVs
- running the full HDL simulation when Icarus Verilog is available
- running a bounded safety fuzz smoke test
- regenerating paper preview and hardware-cost evidence

The core research files are unchanged. The agent package lives under
`.agents/pipesense_paper_agent` so it can be installed or removed without
touching the RTL, manuscript, or result scripts.

## Install

From the repository root:

```powershell
python -m pip install -r .agents\pipesense_paper_agent\requirements.txt
python .agents\pipesense_paper_agent\src\pipesense_arm_mcp.py --self-test
```

In this Codex desktop session, `python` may point to the Windows Store alias.
If so, use the bundled interpreter:

```powershell
C:\Users\tyboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pip install -r .agents\pipesense_paper_agent\requirements.txt
C:\Users\tyboy\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe .agents\pipesense_paper_agent\src\pipesense_arm_mcp.py --self-test
```

## Run As MCP

Start the server from the repository root:

```powershell
python .agents\pipesense_paper_agent\src\pipesense_arm_mcp.py
```

For clients that accept MCP JSON config, adapt `mcp_config.example.json`.
The server uses `PIPESENSE_ROOT` if set; otherwise it resolves the repository
root from this file location.

## Useful Agent Requests

- "Summarize the PipeSense paper and list the evidence files."
- "Run the no-simulator artifact checks."
- "Audit the research package."
- "Check whether the research limits are fixed for this paper."
- "Search the project for oracle comparison."
- "Summarize the generated result CSVs."
- "Run a five-seed safety smoke test."
- "Build and verify the paper preview."

## Paper2Agent Mapping

Paper2Agent represents a paper as tools, resources, and prompts exposed over
MCP. This package maps PipeSense as follows:

- Tools: artifact checks, paper checks, simulation, safety smoke, result
  summary, research audit, limit-closure audit, project search, and file
  readback.
- Resources: README, manuscript source, documentation, and generated CSVs.
- Prompt: `SESSION_PROMPT.md`, which tells an assistant how to treat evidence
  and claim boundaries.
