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

import json
import os
import shutil
import subprocess
import tempfile

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("greenerplatform")

SENTINEL_BIN = os.environ.get("SENTINEL_BIN") or shutil.which("kubectl-sentinel") or "kubectl-sentinel"
TRIAGE_BIN = os.environ.get("TRIAGE_BIN") or shutil.which("incident-triage") or "incident-triage"
DEFAULT_TIMEOUT = int(os.environ.get("GP_MCP_TIMEOUT", "90"))


def _run(cmd: list[str], timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


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
    if not p.stdout.strip():
        return json.dumps({
            "error": "kubectl-sentinel produced no output",
            "exit_code": p.returncode,
            "stderr": p.stderr[:2000],
            "hint": "Check kubectl access, the context, and that 'kubectl-sentinel' is installed.",
        })
    return p.stdout


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
    snap = sentinel_json.strip()
    if not snap:
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
        return p.stdout or json.dumps({
            "error": "incident-triage produced no output",
            "exit_code": p.returncode,
            "stderr": p.stderr[:2000],
        })
    finally:
        for path in (snap_path, alert_path):
            if path and os.path.exists(path):
                os.unlink(path)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
