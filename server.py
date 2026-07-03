#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Olawale Ogundiran
"""GreenerPlatform MCP server.

Exposes the deterministic reliability tools — kubectl-sentinel and
incident-triage — to any MCP-capable agent (Cursor, Claude Desktop, VS Code,
Windsurf, or a custom client). The agent reasons over the evidence these tools
produce; it does not guess at cluster state.

The tools themselves carry no LLM and no vendor coupling. This server is a thin,
neutral adapter over their CLIs.
"""
from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
import tempfile

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("greenerplatform")

SENTINEL_BIN = os.environ.get("SENTINEL_BIN") or shutil.which("kubectl-sentinel") or "kubectl-sentinel"
TRIAGE_BIN = os.environ.get("TRIAGE_BIN") or shutil.which("incident-triage") or "incident-triage"
DEFAULT_TIMEOUT = int(os.environ.get("GP_MCP_TIMEOUT", "90"))

# Minimum CLI versions this server is validated against. A stale binary silently
# emits fewer checks (e.g. sentinel 1.1.0 returns 10 of 15 dimensions), so we
# surface a warning rather than let the agent reason over an incomplete snapshot.
MIN_SENTINEL_VERSION = os.environ.get("MIN_SENTINEL_VERSION", "1.2.1")
MIN_TRIAGE_VERSION = os.environ.get("MIN_TRIAGE_VERSION", "1.2.1")

_VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def _run(cmd: list[str], timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


@functools.lru_cache(maxsize=8)
def _tool_version(bin_path: str) -> tuple[int, int, int] | None:
    """Return the (major, minor, patch) of a CLI, or None if undeterminable."""
    try:
        p = _run([bin_path, "--version"], timeout=10)
    except Exception:
        return None
    m = _VERSION_RE.search(f"{p.stdout}\n{p.stderr}")
    return (int(m[1]), int(m[2]), int(m[3])) if m else None


def _version_warning(name: str, bin_path: str, minimum: str) -> str | None:
    """None if the installed CLI is at/above `minimum`, else a human warning."""
    installed = _tool_version(bin_path)
    if installed is None:
        return (f"{name}: could not determine version — ensure it is installed and on "
                f"PATH; results may be incomplete.")
    want = tuple(int(x) for x in minimum.split("."))
    if installed < want:
        got = ".".join(map(str, installed))
        return (f"{name} {got} is older than the expected {minimum}; output may be "
                f"missing checks — update {name} (e.g. 'kubectl krew upgrade sentinel').")
    return None


def _attach_warnings(raw_json: str, warnings: list[str]) -> str:
    """Non-destructively add a top-level `warnings` array to a tool's JSON output.

    Returns the raw string unchanged if there are no warnings or it does not parse.
    """
    warnings = [w for w in warnings if w]
    if not warnings:
        return raw_json
    try:
        obj = json.loads(raw_json)
    except (ValueError, TypeError):
        return raw_json
    if not isinstance(obj, dict):
        return raw_json
    obj.setdefault("warnings", [])
    obj["warnings"].extend(warnings)
    return json.dumps(obj)


def _collect_sentinel(namespace: str, context: str, resource: str) -> subprocess.CompletedProcess:
    cmd = [SENTINEL_BIN, "--json"]
    if namespace:
        cmd += ["-n", namespace]
    if context:
        cmd += ["--context", context]
    if resource:
        cmd += [resource]
    return _run(cmd)


@mcp.tool()
def sentinel_snapshot(namespace: str = "", context: str = "", resource: str = "") -> str:
    """Collect a deterministic Kubernetes cluster-health snapshot as JSON.

    Runs kubectl-sentinel across 15 health dimensions (pods, workloads, events,
    jobs, PDBs, quotas, DNS, certs, and more) and returns structured, severity-
    ranked findings. Same cluster state in, same findings out.

    Args:
        namespace: scope to a single namespace (optional; default all namespaces).
        context: kubeconfig context to target (optional).
        resource: a specific resource to focus on, e.g. "pod/api-gateway" (optional).
    """
    p = _collect_sentinel(namespace, context, resource)
    warn = _version_warning("kubectl-sentinel", SENTINEL_BIN, MIN_SENTINEL_VERSION)
    if not p.stdout.strip():
        return json.dumps({
            "error": "kubectl-sentinel produced no output",
            "exit_code": p.returncode,
            "stderr": p.stderr[:2000],
            "hint": "Check kubectl access, the context, and that 'kubectl-sentinel' is installed.",
            "warnings": [w for w in [warn] if w],
        })
    return _attach_warnings(p.stdout, [warn])


@mcp.tool()
def triage_incident(alert: str, sentinel_json: str = "", namespace: str = "", context: str = "") -> str:
    """Triage an incident deterministically and return a prioritised fix plan as JSON.

    Correlates an alert to cluster findings, builds a causation chain (root cause ->
    contributing -> symptom), infers the likely change that triggered it, and emits
    a P1/P2/P3 fix plan with concrete kubectl commands. No LLM, no guessing.

    Args:
        alert: the alert as free text (e.g. "payments API 503 since 14:30") or a
            JSON alert descriptor string.
        sentinel_json: an existing kubectl-sentinel JSON snapshot. If omitted, a
            fresh snapshot is collected first (requires cluster access).
        namespace: scope/override namespace (optional).
        context: kubeconfig context used only when collecting a fresh snapshot.
    """
    collected_fresh = not sentinel_json.strip()
    snap = sentinel_json.strip()
    if collected_fresh:
        p = _collect_sentinel(namespace, context, "")
        snap = p.stdout
        if not snap.strip():
            return json.dumps({
                "error": "could not collect cluster state for triage",
                "stderr": p.stderr[:2000],
            })

    snap_path = None
    alert_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write(snap)
            snap_path = f.name

        cmd = [TRIAGE_BIN, "--sentinel-json", snap_path]
        stripped = alert.strip()
        if stripped.startswith("{"):
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
                f.write(alert)
                alert_path = f.name
            cmd += ["--alert", alert_path]
        else:
            cmd += ["--alert", alert]
        if namespace:
            cmd += ["--namespace", namespace]

        p = _run(cmd)
        warnings = [_version_warning("incident-triage", TRIAGE_BIN, MIN_TRIAGE_VERSION)]
        if collected_fresh:
            warnings.append(_version_warning("kubectl-sentinel", SENTINEL_BIN, MIN_SENTINEL_VERSION))
        if not p.stdout:
            return json.dumps({
                "error": "incident-triage produced no output",
                "exit_code": p.returncode,
                "stderr": p.stderr[:2000],
                "warnings": [w for w in warnings if w],
            })
        return _attach_warnings(p.stdout, warnings)
    finally:
        for path in (snap_path, alert_path):
            if path and os.path.exists(path):
                os.unlink(path)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
