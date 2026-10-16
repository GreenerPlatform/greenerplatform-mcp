<div align="center">
  <img src="https://raw.githubusercontent.com/GreenerPlatform/greenerplatform-mcp/main/docs/banner.svg" alt="greenerplatform-mcp" width="100%"/>

[![PyPI](https://img.shields.io/pypi/v/greenerplatform-mcp?color=1a9c3e)](https://pypi.org/project/greenerplatform-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/greenerplatform-mcp)](https://pypi.org/project/greenerplatform-mcp/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue)](LICENSE)

</div>

# greenerplatform-mcp

An [MCP](https://modelcontextprotocol.io) server that exposes the GreenerPlatform
command-line evidence tools to compatible MCP hosts. It is a thin adapter: it does not
contain a model, verify causal claims, or enforce how a host uses the returned evidence.

> **Available on PyPI:** `pipx install greenerplatform-mcp`

It wraps two CLIs:

- **`sentinel_snapshot`** — a 15-dimension Kubernetes health report
  ([kubectl-sentinel](https://github.com/GreenerPlatform/kubectl-sentinel)).
- **`triage_incident`** — correlate a normalized alert with cluster observations and
  return ranked evidence and candidate response steps
  ([incident-triage](https://github.com/GreenerPlatform/incident-triage)).

Neither tool carries an LLM. The schemas make observations, provenance, and evidence gaps
available to the host, but the adapter cannot guarantee correct model behavior.

## Prerequisites

- Python 3.10+
- Linux or a Linux environment such as WSL for the current `kubectl-sentinel` Bash CLI
- `kubectl-sentinel` 1.3.2 and `incident-triage` 1.3.2 on your `PATH`
  (or set `SENTINEL_BIN` / `TRIAGE_BIN`)
- `kubectl`, `jq`, cluster credentials, and the required Kubernetes RBAC for live reports

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

Other MCP hosts can run `greenerplatform-mcp` over stdio, but their configuration keys and
security models differ. The examples above are configuration examples, not a universal
compatibility guarantee.

## Tools

| Tool | Arguments | Returns |
|---|---|---|
| `sentinel_snapshot` | `namespace?`, `context?` | severity-ranked observations and collection status |
| `triage_incident` | `alert`, `sentinel_json?`, `namespace?`, `context?` | ranked evidence, gaps, and candidate response steps |

If `triage_incident` is called without `sentinel_json`, it collects a fresh snapshot
first (requires cluster access).

The `resource` argument remains reserved for API compatibility. Resource deep-dive modes
in kubectl-sentinel currently emit text, not JSON, so the server returns an explicit
`unsupported_resource` error instead of an incomplete tool result.

## Version guard

A stale CLI can emit fewer checks. The server checks each CLI's `--version` and, if it is
below the expected minimum, adds a non-destructive `warnings` array to the tool's JSON
output:

```json
{ "warnings": ["kubectl-sentinel 1.3.0 is older than the expected 1.3.2; output may be missing checks — install the current source version."] }
```

The findings are still returned; the warning just flags that they may be partial. Set
`MIN_SENTINEL_VERSION` / `MIN_TRIAGE_VERSION` to change the expected minimums.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `SENTINEL_BIN` | `kubectl-sentinel` on PATH | path to the sentinel binary |
| `TRIAGE_BIN` | `incident-triage` on PATH | path to the triage binary |
| `GP_MCP_TIMEOUT` | `90` | per-command timeout (seconds) |
| `MIN_SENTINEL_VERSION` | `1.3.2` | warn if the installed sentinel is older |
| `MIN_TRIAGE_VERSION` | `1.3.2` | warn if the installed triage is older |

## Operational boundaries

- The server executes the configured CLIs and returns their stdout. It does not execute
  commands included in recommendations.
- Live collection contacts the selected Kubernetes API and may invoke credential plugins.
- Sentinel reports can contain cluster, workload, image, Secret, event, and log details.
  Treat them as sensitive and redact them before sharing.
- Rule-based output can be reproducible without being complete, correct, or causal.
- The current W5 gate covers offline fixtures; broader live-cluster and historical-source
  validation remains in progress.

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
git tag v0.1.2 && git push origin v0.1.2
gh release create v0.1.2 --generate-notes
```

The `Publish to PyPI` workflow builds, runs `twine check`, and publishes. After the first
release, `pipx install greenerplatform-mcp` works for anyone.

## License

Apache-2.0. See `LICENSE`, `NOTICE`, and the project
[trademark policy](https://github.com/GreenerPlatform/kubectl-sentinel/blob/main/TRADEMARKS.md).
