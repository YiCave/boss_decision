# Simulator Agent (LangGraph-first)

This project now follows a LangGraph-first architecture where:

- LangGraph is the main entrypoint and workflow runtime.
- Deep Agents is used only inside persona worker execution (subagent simulation).

## Structure

```text
simulator_agent/
├── src/
│   ├── agent.py          # graph construction + exported compiled graph
│   ├── nodes.py          # LangGraph node and routing functions
│   ├── state.py          # Typed state schemas and reducers
│   └── utils/
│       └── parsing.py    # JSON/text parsing helpers and fallback parsing
├── tests/
│   └── test_m1_parse.py  # flow and fallback tests
├── langgraph.json        # LangGraph app config
├── pyproject.toml        # Python dependencies
└── main.py               # local CLI runner for quick checks
```

## Plan Mapping

Implemented to match plan phases:

1. Phase 1: `parse_decision` -> `build_scenario` -> `select_personas`
2. Phase 2: `dispatch_subagents_route` -> `persona_worker` (parallel via `Send`)
3. Phase 3: `collect_results` -> `aggregate_impacts` -> `generate_recommendation`
4. Phase 4: `format_response`

## Install Dependencies

```bash
# Preferred (uv)
uv sync

# Fallback (pip)
pip install -r requirements.txt
```

## Run Locally

```bash
uv run python main.py "Should we increase price by 10% for student segment next quarter?"
# pip fallback: python main.py "Should we increase price by 10% for student segment next quarter?"
```

## LangGraph Entry

`langgraph.json` points to:

- graph name: `agent`
- graph object: `./src/agent.py:agent`

## Persona Filesystem Access (MCP)

Persona subagents now receive filesystem tools from the MCP filesystem server with runtime-scoped directory access:

- The main simulator node derives allowed folders from each persona role/focus.
- Each persona subagent gets its own tool set restricted to those directories.
- Access is limited to `backend/agent_docs/simulator/...`.
- Read-only tools are exposed to personas (`read_file`, `list_directory`, `search_files`, etc.).

Bootstrap folders:

- `backend/agent_docs/simulator/companies/default_company/core`
- `backend/agent_docs/simulator/companies/default_company/finance`
- `backend/agent_docs/simulator/companies/default_company/product`
- `backend/agent_docs/simulator/companies/default_company/sales`
- `backend/agent_docs/simulator/companies/default_company/ops`
- `backend/agent_docs/simulator/shared/benchmarks`
- `backend/agent_docs/simulator/shared/macro`

Optional env vars:

- `SIMULATOR_DISABLE_FS_MCP=1` to disable MCP filesystem tools
- `SIMULATOR_FS_MCP_COMMAND` (default: `npx`)
- `SIMULATOR_FS_MCP_PACKAGE` (default: `@modelcontextprotocol/server-filesystem`)
