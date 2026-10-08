#!/usr/bin/env python3
"""
Local Enterprise Gateway Simulator.
Emulates Azure APIM policy evaluation, dynamic model routing, and ERP WBS header injection.
"""

import argparse
import json
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from src.orchestrator.router import DynamicModelRouter
from src.schemas.telemetry import TelemetryEvent


router = DynamicModelRouter()


class MockAPIMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
        
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        task_type = (
            self.headers.get("X-Task-Type")
            or self.headers.get("X-Enterprise-Task-Type")
            or "standard"
        )
        wbs_element = (
            self.headers.get("X-EY-WBS-Element")
            or self.headers.get("X-WBS-Element")
            or self.headers.get("X-Cost-Center")
            or self.headers.get("X-Billing-ID")
            or ""
        )
        if not wbs_element.startswith("WBS-"):
            response = {"error": "Missing or invalid X-EY-WBS-Element billing identifier"}
            response_bytes = json.dumps(response).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_bytes)))
            self.end_headers()
            self.wfile.write(response_bytes)
            return

        # Evaluate routing
        first_message = ""
        messages = payload.get("messages", [])
        if messages and isinstance(messages, list):
            first_message = messages[0].get("content", "")

        tier_config = router.classify_task(task_type, first_message)
        est_cost = router.compute_estimated_cost(tier_config.deployment_name, 1500, 300)

        response_payload = {
            "id": "chatcmpl-mock-gateway-001",
            "object": "chat.completion",
            "model": tier_config.deployment_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": f"[GATEWAY SIMULATION] Request successfully routed to {tier_config.deployment_name} (Tier {tier_config.tier_level}).",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 1500,
                "completion_tokens": 300,
                "total_tokens": 1800,
            },
            "enterprise_governance": {
                "task_type": task_type,
                "wbs_element": wbs_element,
                "routed_deployment": tier_config.deployment_name,
                "estimated_transaction_cost_usd": est_cost,
            },
            "telemetry": TelemetryEvent(
                timestamp=datetime.now(timezone.utc),
                wbsElement=wbs_element,
                promptComplexity=router.classify_prompt_complexity(first_message),
                tokenCount=1800,
            ).to_dict(),
        }

        response_bytes = json.dumps(response_payload, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Routed-Deployment", tier_config.deployment_name)
        self.send_header("X-WBS-Element", wbs_element)
        self.send_header("Content-Length", str(len(response_bytes)))
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format, *args):
        # Clean formatted logging
        print(f"[APIM-GATEWAY-MOCK] {self.address_string()} - {format % args}")


def main():
    parser = argparse.ArgumentParser(description="Run local APIM gateway mock server")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), MockAPIMHandler)
    print(f"Enterprise Gateway Mock Server listening on http://127.0.0.1:{args.port}/chat/completions")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down gateway mock server.")
        server.server_close()


if __name__ == "__main__":
    main()
