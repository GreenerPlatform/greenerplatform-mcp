# greenerplatform-mcp

An [MCP](https://modelcontextprotocol.io) server that exposes the GreenerPlatform
deterministic reliability tools to any MCP-capable agent — **Cursor, Claude Desktop,
VS Code, Windsurf, or your own client.** Install once; the tools work everywhere.

It wraps two CLIs:

- **`sentinel_snapshot`** — a deterministic 15-dimension cluster-health snapshot
  ([kubectl-sentinel](https://github.com/GreenerPlatform/kubectl-sentinel)).
- **`triage_incident`** — correlate an alert to cluster findings, build a causation
  chain, and return a P1/P2/P3 fix plan
  ([incident-triage](https://github.com/GreenerPlatform/incident-triage)).

Neither tool carries an LLM or any vendor coupling. This server is a thin, neutral
adapter. The agent reasons over the evidence the tools produce — it is bounded by the
evidence, it does not guess at cluster state.

## Prerequisites

- Python 3.10+
- `kubectl-sentinel` and `incident-triage` on your `PATH`
  (or set `SENTINEL_BIN` / `TRIAGE_BIN` to their locations)
- `kubectl` + `jq` for live cluster snapshots

## Install

```bash
pipx install greenerplatform-mcp
# or: pip install greenerplatform-mcp
```

## Configure your agent

**Cursor** — `~/.cursor/mcp.json` (or a project `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "greenerplatform": { "command": "greenerplatform-mcp" }
  }
}
```

**Claude Desktop** — `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "greenerplatform": { "command": "greenerplatform-mcp" }
  }
}
```

Any other MCP client uses the same pattern: run `greenerplatform-mcp` over stdio.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `sentinel_snapshot` | `namespace?`, `context?`, `resource?` | cluster-health JSON |
| `triage_incident` | `alert`, `sentinel_json?`, `namespace?`, `context?` | triage JSON (cause + fix plan) |

If `triage_incident` is called without `sentinel_json`, it collects a fresh snapshot
first (requires cluster access).

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_BIN` | `kubectl-sentinel` on PATH | path to the sentinel binary |
| `TRIAGE_BIN` | `incident-triage` on PATH | path to the triage binary |
| `GP_MCP_TIMEOUT` | `90` | per-command timeout (seconds) |

## License

Apache-2.0. See `LICENSE`, `NOTICE`, and the project
[trademark policy](https://github.com/GreenerPlatform/kubectl-sentinel/blob/main/TRADEMARKS.md).
