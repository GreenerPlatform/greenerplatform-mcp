<div align="center">
  <img src="docs/banner.svg" alt="greenerplatform-mcp" width="100%"/>
</div>

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

## Version guard

A stale CLI silently emits fewer checks — for example, `kubectl-sentinel` 1.1.0
returns 10 of the 15 health dimensions. To keep an agent from reasoning over an
incomplete snapshot, the server checks each CLI's `--version` and, if it is below the
expected minimum, adds a non-destructive `warnings` array to the tool's JSON output:

```json
{ "warnings": ["kubectl-sentinel 1.1.0 is older than the expected 1.2.1; output may be missing checks — update kubectl-sentinel"] }
```

The findings are still returned; the warning just flags that they may be partial. Set
`MIN_SENTINEL_VERSION` / `MIN_TRIAGE_VERSION` to change the expected minimums.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_BIN` | `kubectl-sentinel` on PATH | path to the sentinel binary |
| `TRIAGE_BIN` | `incident-triage` on PATH | path to the triage binary |
| `GP_MCP_TIMEOUT` | `90` | per-command timeout (seconds) |
| `MIN_SENTINEL_VERSION` | `1.2.1` | warn if the installed sentinel is older |
| `MIN_TRIAGE_VERSION` | `1.2.1` | warn if the installed triage is older |

## Releasing

Releases publish to PyPI automatically via GitHub Actions using **Trusted Publishing**
(OIDC) — no API tokens are stored anywhere.

One-time setup (on [pypi.org](https://pypi.org)):

1. Sign in → *Your projects* → *Publishing* → *Add a pending publisher*.
2. Project name `greenerplatform-mcp`, owner `GreenerPlatform`, repo `greenerplatform-mcp`,
   workflow `publish.yml`, environment `pypi`.

To cut a release:

```bash
# bump version in pyproject.toml, commit, then:
git tag v0.1.0 && git push origin v0.1.0
gh release create v0.1.0 --generate-notes
```

The `Publish to PyPI` workflow builds, runs `twine check`, and publishes. After the first
release, `pipx install greenerplatform-mcp` works for anyone.

## License

Apache-2.0. See `LICENSE`, `NOTICE`, and the project
[trademark policy](https://github.com/GreenerPlatform/kubectl-sentinel/blob/main/TRADEMARKS.md).
