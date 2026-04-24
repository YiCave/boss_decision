# Simulator Filesystem Data

This directory is the root boundary for simulator sub-agent filesystem MCP access.

Sub-agents are granted access dynamically at runtime by the main simulator agent.
Each persona receives only a subset of folders based on persona role/focus.

Current bootstrap layout:

- `companies/default_company/core`
- `companies/default_company/finance`
- `companies/default_company/product`
- `companies/default_company/sales`
- `companies/default_company/ops`
- `shared/benchmarks`
- `shared/macro`

## Seed Mock Data

The folders now include synthetic mock datasets (CSV/JSON/Markdown) to support realistic tool-based reasoning by persona subagents during simulation runs.

All files in this tree are test data only.
