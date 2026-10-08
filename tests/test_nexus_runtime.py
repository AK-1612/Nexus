"""Behavioral tests for NEXUS routing, governance, and gateway resilience."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pydantic import ValidationError

from src.orchestrator.circuit_breaker import CircuitBreaker
from src.orchestrator.gateway_client import GatewayClient, GatewayRequest
from src.orchestrator.router import DynamicModelRouter
from src.schemas.telemetry import TelemetryEvent


class TestNexusRuntime(unittest.TestCase):
    def setUp(self) -> None:
        self.router = DynamicModelRouter()

    def test_low_complexity_routes_to_fast_model(self) -> None:
        tier = self.router.classify_task("syntax", "Fix this Python syntax error")
        self.assertEqual(tier.deployment_name, "gpt-4o-mini")

    def test_high_complexity_routes_to_advanced_model(self) -> None:
        tier = self.router.classify_task(
            "architecture",
            "Design an enterprise architecture for a multi-region payment platform",
        )
        self.assertEqual(tier.deployment_name, "gpt-4o")

    def test_missing_wbs_is_rejected_before_gateway_contact(self) -> None:
        router = DynamicModelRouter()
        with self.assertRaisesRegex(ValueError, "X-EY-WBS-Element"):
            router.prepare_request(
                GatewayRequest(
                    task_type="syntax",
                    prompt="Fix this syntax error",
                    headers={},
                )
            )

    def test_telemetry_schema_rejects_unknown_fields(self) -> None:
        payload = {
            "timestamp": "2026-10-08T12:00:00Z",
            "wbsElement": "WBS-TEST-9942",
            "promptComplexity": "low",
            "tokenCount": 180,
            "unexpected": True,
        }
        with self.assertRaises(ValidationError):
            TelemetryEvent.model_validate(payload)

    def test_telemetry_schema_accepts_required_pattern_b_fields(self) -> None:
        event = TelemetryEvent.model_validate(
            {
                "timestamp": datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc),
                "wbsElement": "WBS-TEST-9942",
                "promptComplexity": "high",
                "tokenCount": 180,
            }
        )
        self.assertEqual(event.promptComplexity, "high")
        self.assertEqual(event.wbsElement, "WBS-TEST-9942")
        self.assertEqual(event.tokenCount, 180)
        self.assertEqual(
            set(event.to_dict()),
            {"timestamp", "wbsElement", "promptComplexity", "tokenCount"},
        )

    def test_gateway_falls_back_when_primary_is_unreachable(self) -> None:
        client = GatewayClient(
            primary_url="https://primary.invalid/v1",
            fallback_url="http://localhost:8080/mock-gateway",
            timeout_seconds=0.01,
            max_retries=0,
        )
        request = GatewayRequest(
            task_type="syntax",
            prompt="Fix this syntax error",
            headers={"X-EY-WBS-Element": "WBS-CORP-998877"},
        )

        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {"model": "gpt-4o-mini", "choices": []}
                ).encode("utf-8")

        with patch(
            "src.orchestrator.gateway_client.urlopen",
            side_effect=[OSError("primary unavailable"), Response()],
        ) as urlopen:
            response = client.send(request)

        self.assertEqual(response.model, "gpt-4o-mini")
        self.assertEqual(response.gateway, "local-fallback")
        self.assertEqual(urlopen.call_count, 2)

    def test_circuit_breaker_opens_after_threshold(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=30)
        breaker.record_failure()
        self.assertTrue(breaker.is_open())


if __name__ == "__main__":
    unittest.main()
