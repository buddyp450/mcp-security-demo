# Trust is earned, not given

This repo hosts the MCP Security Demo showcased in the `mcp-security-demo/` subdirectory.  
It simulates hostile MCP servers (tool providers) and progressively hardened clients to
illustrate how registry checks, runtime monitoring, and sandboxing can contain covert data
leakage, prompt chaining, and undeclared side effects.

## Overview
- **Backend**: FastAPI service (`mcp-security-demo/backend`) that spins up test sessions,
  streams structured events over WebSockets, inspects manifests, and records policy
  outcomes.
- **Clients**: Multiple reference hosts (v1–v4 ~~plus registry guard~~) that demonstrate
  escalating defenses such as manifest validation, syscall/network inspection, latency
  anomaly detection, and sandbox remediation flows.
- **Servers**: Synthetic MCP providers that return deterministic payloads, syscalls, and
  covert markers to showcase specific classes of exploit (covert slice, version shift,
  prompt chainer, side-effect cascade).
- **Frontend**: Vite/React dashboard (`mcp-security-demo/frontend`) for orchestrating test
  cases, visualizing telemetry, and issuing remediation commands.

## Running the Demo
1. Install dependencies at the repo root:
   ```
   npm i
   ```
2. Start the workspace scripts (spawns backend + frontend dev servers):
   ```
   npm run start
   ```
3. Open the printed URLs to access the dashboard, launch sample cases, and inspect the
   resulting decision ledger and telemetry stream.

## Repository Layout
- `mcp-security-demo/backend/` – FastAPI app, registry, monitoring utilities, and server/client catalogs.
- `mcp-security-demo/frontend/` – React UI for storyboards, tail logs, and remediation flows.

Trust in MCP integrations is earned through transparent manifests, enforceable policies,
and observable telemetry. This demo provides a safe harness to explore those guarantees.