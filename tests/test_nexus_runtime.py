"""Behavioral & integration tests for Nexus runtime (GatewayClient end-to-end).

All external I/O is eliminated via ``unittest.mock.patch`` on ``urlopen``,
so the suite runs offline and deterministically.
"""

import json
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, call, patch

from pydantic import ValidationError

from src.orchestrator.circuit_breaker import CircuitBreaker
from src.orchestrator.gateway_client import GatewayClient, GatewayRequest
from src.orchestrator.router import DynamicModelRouter
from src.schemas.telemetry import TelemetryEvent

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

VALID_HEADERS = {"X-EY-WBS-Element": "WBS-CORP-998877"}

PRIMARY_URL = "https://api.example.invalid/v1/chat/completions"
FALLBACK_URL = "http://localhost:8080/mock-gateway"


def _mock_response(payload: dict) -> MagicMock:
    """Build a context-manager mock that returns *payload* as JSON bytes."""
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def _gateway_payload(model: str = "gpt-4o-mini") -> dict:
    return {
        "model": model,
        "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


class TestNexusRuntime(unittest.TestCase):
    """End-to-end behavioral tests — gateway I/O mocked via urlopen patches."""

    # ── Routing Classification ────────────────────────────────────────────────

    def test_low_complexity_routes_to_fast_model(self):
        """Task type ``syntax`` classifies to ``gpt-4o-mini`` (Tier 1)."""
        router = DynamicModelRouter()
        tier = router.classify_task("syntax", "Fix a syntax error in this script")
        self.assertEqual(tier.deployment_name, "gpt-4o-mini")
        self.assertEqual(tier.tier_level, 1)

    def test_high_complexity_routes_to_advanced_model(self):
        """Task type ``architecture`` classifies to ``gpt-4o`` (Tier 2)."""
        router = DynamicModelRouter()
        tier = router.classify_task(None, "Design multi-region architecture for the platform")
        self.assertEqual(tier.deployment_name, "gpt-4o")
        self.assertEqual(tier.tier_level, 2)

    def test_tier3_task_routes_to_frontier_model(self):
        """Task type ``statutory-audit`` classifies to ``o1-preview`` (Tier 3)."""
        router = DynamicModelRouter()
        tier = router.classify_task("statutory-audit", "")
        self.assertEqual(tier.deployment_name, "o1-preview")
        self.assertEqual(tier.tier_level, 3)

    # ── WBS Perimeter Defense ─────────────────────────────────────────────────

    def test_missing_wbs_is_rejected_before_gateway_contact(self):
        """Request with no billing header raises ``ValueError`` before any network I/O."""
        router = DynamicModelRouter()
        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Extract data",
            headers={},  # No WBS header
        )
        with self.assertRaises(ValueError) as ctx:
            router.prepare_request(request)
        self.assertIn("WBS", str(ctx.exception))

    def test_invalid_wbs_format_is_rejected(self):
        """Header value not matching ``^WBS-[A-Z0-9_-]+$`` is rejected immediately."""
        router = DynamicModelRouter()
        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Extract data",
            headers={"X-EY-WBS-Element": "invalid-format"},
        )
        with self.assertRaises(ValueError) as ctx:
            router.prepare_request(request)
        self.assertIn("WBS", str(ctx.exception))

    def test_prepare_request_valid_wbs_enriches_headers(self):
        """Valid WBS produces a ``PreparedRequest`` with ``X-Routed-Deployment`` injected."""
        router = DynamicModelRouter()
        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Parse invoices",
            headers={"X-EY-WBS-Element": "WBS-AUDIT-2026-Q3"},
        )
        prepared = router.prepare_request(request)
        self.assertIn("X-Routed-Deployment", prepared.headers)
        self.assertEqual(prepared.headers["X-EY-WBS-Element"], "WBS-AUDIT-2026-Q3")
        self.assertEqual(prepared.headers["X-Routed-Deployment"], "gpt-4o-mini")

    # ── Telemetry Schema Contract ─────────────────────────────────────────────

    def test_telemetry_schema_accepts_required_fields(self):
        """Valid ``TelemetryEvent`` validates and exposes all four mandatory fields."""
        event = TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            wbsElement="WBS-CORP-998877",
            promptComplexity="low",
            tokenCount=42,
        )
        self.assertEqual(event.wbsElement, "WBS-CORP-998877")
        self.assertEqual(event.promptComplexity, "low")
        self.assertEqual(event.tokenCount, 42)
        self.assertIsInstance(event.timestamp, datetime)

    def test_telemetry_schema_rejects_unknown_fields(self):
        """``extra="forbid"`` causes ``ValidationError`` on any unrecognised field."""
        with self.assertRaises(ValidationError):
            TelemetryEvent.model_validate(
                {
                    "timestamp": datetime.now(timezone.utc),
                    "wbsElement": "WBS-CORP-998877",
                    "promptComplexity": "low",
                    "tokenCount": 10,
                    "unknownField": "should-fail",  # Extra field — Pydantic rejects this
                }
            )

    def test_telemetry_schema_rejects_zero_token_count(self):
        """``tokenCount`` must be ``>= 1``; a value of ``0`` is a schema violation."""
        with self.assertRaises(ValidationError):
            TelemetryEvent(
                timestamp=datetime.now(timezone.utc),
                wbsElement="WBS-CORP-998877",
                promptComplexity="low",
                tokenCount=0,  # Must be ge=1
            )

    # ── Gateway — Primary Path ────────────────────────────────────────────────

    @patch("src.orchestrator.gateway_client.urlopen")
    def test_gateway_primary_success(self, mock_urlopen):
        """Primary gateway success records WBS on telemetry and returns ``gateway='primary'``."""
        mock_urlopen.return_value = _mock_response(_gateway_payload("gpt-4o-mini"))
        client = GatewayClient(primary_url=PRIMARY_URL, fallback_url=FALLBACK_URL)
        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Extract invoice data",
            headers=VALID_HEADERS,
        )
        response = client.send(request)
        self.assertEqual(response.gateway, "primary")
        self.assertEqual(response.model, "gpt-4o-mini")
        self.assertEqual(response.telemetry.wbsElement, "WBS-CORP-998877")

    @patch("src.orchestrator.gateway_client.urlopen")
    def test_gateway_tier3_request_routed_to_o1_preview(self, mock_urlopen):
        """Statutory-audit task sends ``model=o1-preview`` in the request body to the gateway."""
        mock_urlopen.return_value = _mock_response(_gateway_payload("o1-preview"))
        client = GatewayClient(primary_url=PRIMARY_URL, fallback_url=FALLBACK_URL)
        request = GatewayRequest(
            task_type="statutory-audit",
            prompt="Perform a full statutory audit review",
            headers=VALID_HEADERS,
        )
        response = client.send(request)
        # Inspect the body sent to urlopen
        actual_body = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        self.assertEqual(actual_body["model"], "o1-preview")
        self.assertEqual(response.gateway, "primary")

    @patch("src.orchestrator.gateway_client.urlopen")
    def test_gateway_response_payload_is_preserved(self, mock_urlopen):
        """Full gateway JSON payload (including ``usage``) is stored verbatim on ``GatewayResponse.payload``."""
        payload = _gateway_payload("gpt-4o")
        mock_urlopen.return_value = _mock_response(payload)
        client = GatewayClient(primary_url=PRIMARY_URL, fallback_url=FALLBACK_URL)
        request = GatewayRequest(
            task_type="standard-dialogue",
            prompt="Explain the architecture",
            headers=VALID_HEADERS,
        )
        response = client.send(request)
        self.assertEqual(response.payload["usage"]["total_tokens"], 15)
        self.assertEqual(response.payload["model"], "gpt-4o")

    # ── Gateway — Fallback & Retry ────────────────────────────────────────────

    @patch("src.orchestrator.gateway_client.urlopen")
    def test_gateway_falls_back_when_primary_is_unreachable(self, mock_urlopen):
        """Primary ``OSError`` triggers exactly one fallback call; ``gateway='local-fallback'``."""
        fallback_payload = _gateway_payload("gpt-4o-mini")
        mock_urlopen.side_effect = [
            OSError("Connection refused"),           # Primary attempt 1
            _mock_response(fallback_payload),        # Fallback
        ]
        client = GatewayClient(
            primary_url=PRIMARY_URL,
            fallback_url=FALLBACK_URL,
            max_retries=0,  # No retries — fail immediately and use fallback
        )
        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Parse data",
            headers=VALID_HEADERS,
        )
        response = client.send(request)
        self.assertEqual(response.gateway, "local-fallback")
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("src.orchestrator.gateway_client.time.sleep", return_value=None)
    @patch("src.orchestrator.gateway_client.urlopen")
    def test_gateway_retries_exhaust_then_fall_back(self, mock_urlopen, mock_sleep):
        """With ``max_retries=2``, three primary attempts are made before fallback (4 total calls)."""
        fallback_payload = _gateway_payload("gpt-4o-mini")
        mock_urlopen.side_effect = [
            OSError("Connection refused"),   # Primary attempt 1
            OSError("Connection refused"),   # Primary attempt 2 (retry 1)
            OSError("Connection refused"),   # Primary attempt 3 (retry 2)
            _mock_response(fallback_payload),  # Fallback
        ]
        client = GatewayClient(
            primary_url=PRIMARY_URL,
            fallback_url=FALLBACK_URL,
            max_retries=2,
        )
        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Extract records",
            headers=VALID_HEADERS,
        )
        response = client.send(request)
        self.assertEqual(response.gateway, "local-fallback")
        self.assertEqual(mock_urlopen.call_count, 4)

    # ── Circuit Breaker — Integration ─────────────────────────────────────────

    def test_gateway_raises_when_circuit_breaker_open(self):
        """Pre-opened breaker causes ``send()`` to raise ``RuntimeError`` without any network I/O."""
        client = GatewayClient(primary_url=PRIMARY_URL, fallback_url=FALLBACK_URL)
        # Force the circuit breaker open
        client.circuit_breaker._failures = client.circuit_breaker.failure_threshold
        client.circuit_breaker._opened_at = time.monotonic()

        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Extract data",
            headers=VALID_HEADERS,
        )
        with self.assertRaises(RuntimeError) as ctx:
            client.send(request)
        self.assertIn("circuit", str(ctx.exception).lower())

    @patch("src.orchestrator.gateway_client.urlopen")
    def test_circuit_breaker_opens_after_threshold(self, mock_urlopen):
        """Single failure with ``failure_threshold=1`` immediately trips the breaker."""
        mock_urlopen.side_effect = [
            OSError("Connection refused"),   # Primary fails
            OSError("Connection refused"),   # Fallback also fails
        ]
        client = GatewayClient(primary_url=PRIMARY_URL, fallback_url=FALLBACK_URL, max_retries=0)
        client.circuit_breaker = CircuitBreaker(failure_threshold=1)

        request = GatewayRequest(
            task_type="bulk-extraction",
            prompt="Extract data",
            headers=VALID_HEADERS,
        )
        # First call: primary fails → circuit breaker records failure → breaker opens
        with self.assertRaises(Exception):
            client.send(request)

        self.assertTrue(client.circuit_breaker.is_open())

    def test_circuit_breaker_recovers_after_timeout(self):
        """Breaker auto-resets to closed after ``recovery_timeout`` expires."""
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
        cb.record_failure()
        self.assertTrue(cb.is_open())

        time.sleep(0.1)  # Wait for the recovery timeout to expire
        self.assertFalse(cb.is_open())


if __name__ == "__main__":
    unittest.main()
