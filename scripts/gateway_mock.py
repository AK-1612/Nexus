#!/usr/bin/env python3
"""Local enterprise gateway simulator.

Mimics the Azure APIM primary gateway so the GatewayClient fallback path
and end-to-end cURL smoke-tests can be exercised without real credentials.

Usage
-----
    python scripts/gateway_mock.py --port 8080
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Routing table — mirrors src/orchestrator/router.py MODEL_TIERS
# ---------------------------------------------------------------------------

_TIER_MAP: Dict[str, Dict[str, Any]] = {
    "bulk-extraction":   {"model": "gpt-4o-mini", "tier": 1, "input_rate": 0.15,  "output_rate": 0.60},
    "chunking":          {"model": "gpt-4o-mini", "tier": 1, "input_rate": 0.15,  "output_rate": 0.60},
    "json-parse":        {"model": "gpt-4o-mini", "tier": 1, "input_rate": 0.15,  "output_rate": 0.60},
    "table-extract":     {"model": "gpt-4o-mini", "tier": 1, "input_rate": 0.15,  "output_rate": 0.60},
    "syntax":            {"model": "gpt-4o-mini", "tier": 1, "input_rate": 0.15,  "output_rate": 0.60},
    "standard-dialogue": {"model": "gpt-4o",      "tier": 2, "input_rate": 2.50,  "output_rate": 10.00},
    "architecture":      {"model": "gpt-4o",      "tier": 2, "input_rate": 2.50,  "output_rate": 10.00},
    "statutory-audit":   {"model": "o1-preview",  "tier": 3, "input_rate": 15.00, "output_rate": 60.00},
    "revenue-recognition":{"model": "o1-preview", "tier": 3, "input_rate": 15.00, "output_rate": 60.00},
    "tax-controversy":   {"model": "o1-preview",  "tier": 3, "input_rate": 15.00, "output_rate": 60.00},
}
_DEFAULT_TIER = {"model": "gpt-4o", "tier": 2, "input_rate": 2.50, "output_rate": 10.00}

_MOCK_PROMPT_TOKENS    = 1500
_MOCK_COMPLETION_TOKENS = 300
_MOCK_TOTAL_TOKENS     = _MOCK_PROMPT_TOKENS + _MOCK_COMPLETION_TOKENS


def _estimate_cost(tier: Dict[str, Any]) -> float:
    return round(
        (_MOCK_PROMPT_TOKENS / 1_000_000) * tier["input_rate"]
        + (_MOCK_COMPLETION_TOKENS / 1_000_000) * tier["output_rate"],
        6,
    )


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class MockGatewayHandler(BaseHTTPRequestHandler):
    """Handles POST /chat/completions and POST /mock-gateway."""

    _ROUTES = {"/chat/completions", "/mock-gateway"}

    # silence default request-per-line logging; comment out to restore
    def log_message(self, fmt: str, *args: Any) -> None:  # type: ignore[override]
        print(f"  [{datetime.now(timezone.utc).isoformat()}] {fmt % args}", file=sys.stderr)

    def _send_json(self, status: int, body: Any) -> None:
        payload = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0]

        if path not in self._ROUTES:
            self._send_json(404, {"error": f"Unknown path: {path}"})
            return

        # --- read body ---
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON body"})
            return

        # --- WBS enforcement ---
        wbs = (
            self.headers.get("X-EY-WBS-Element")
            or self.headers.get("X-WBS-Element")
            or self.headers.get("X-Cost-Center")
            or self.headers.get("X-Billing-ID")
            or ""
        ).strip()
        if not wbs:
            self._send_json(400, {"error": "Missing mandatory X-EY-WBS-Element billing header"})
            return

        # --- tier selection ---
        task_type = (
            self.headers.get("X-Task-Type")
            or self.headers.get("X-Routed-Deployment")
            or body.get("task_type", "")
            or ""
        ).strip().lower()
        tier = _TIER_MAP.get(task_type, _DEFAULT_TIER)
        model = body.get("model", tier["model"])  # honour explicit model override from router

        # --- build response matching README contract ---
        response = {
            "id": "chatcmpl-mock-gateway-001",
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": (
                            f"[GATEWAY SIMULATION] Request successfully routed to "
                            f"{model} (Tier {tier['tier']})."
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens":     _MOCK_PROMPT_TOKENS,
                "completion_tokens": _MOCK_COMPLETION_TOKENS,
                "total_tokens":      _MOCK_TOTAL_TOKENS,
            },
            "enterprise_governance": {
                "task_type":                   task_type or "unspecified",
                "wbs_element":                 wbs,
                "routed_deployment":           model,
                "estimated_transaction_cost_usd": _estimate_cost(tier),
            },
            "telemetry": {
                "timestamp":       datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "wbsElement":      wbs,
                "promptComplexity": "low" if tier["tier"] == 1 else "high",
                "tokenCount":      _MOCK_TOTAL_TOKENS,
            },
        }
        self._send_json(200, response)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Nexus local enterprise gateway simulator")
    parser.add_argument("--port", type=int, default=8080, help="TCP port to listen on (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), MockGatewayHandler)
    print(f"✓ Nexus mock gateway running on http://{args.host}:{args.port}")
    print(f"  Endpoints: POST /chat/completions  |  POST /mock-gateway")
    print(f"  Press Ctrl-C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n✗ Mock gateway stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
