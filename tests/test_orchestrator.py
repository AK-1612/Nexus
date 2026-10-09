"""Unit tests for Nexus Orchestrator (Router and Circuit Breaker)."""

import unittest
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from src.orchestrator.router import DynamicModelRouter, MODEL_TIERS
from src.orchestrator.circuit_breaker import CircuitBreaker
from src.schemas.telemetry import TelemetryEvent


class MockAuditedPayload(BaseModel):
    audit_id: str = Field(pattern=r"^AUD-\d+$")
    risk_level: str


class TestOrchestrator(unittest.TestCase):
    """Verifies dynamic classification, cost estimation, perimeter defense, and circuit breaker."""

    def setUp(self):
        self.router = DynamicModelRouter()
        self.circuit_breaker = CircuitBreaker(confidence_threshold=0.85)

    # ── Header-based routing ──────────────────────────────────────────────────

    def test_router_header_classification(self):
        """Explicit task_type header maps deterministically to the correct tier."""
        t1 = self.router.classify_task("bulk-extraction")
        self.assertEqual(t1.deployment_name, "gpt-4o-mini")
        self.assertEqual(t1.tier_level, 1)

        t3 = self.router.classify_task("statutory-audit")
        self.assertEqual(t3.deployment_name, "o1-preview")
        self.assertEqual(t3.tier_level, 3)

        t2 = self.router.classify_task("standard-dialogue")
        self.assertEqual(t2.deployment_name, "gpt-4o")
        self.assertEqual(t2.tier_level, 2)

    # ── Prompt-based routing ──────────────────────────────────────────────────

    def test_router_prompt_classification(self):
        """When task_type is absent, prompt semantics drive tier selection."""
        # Tier 1: bulk extraction keyword
        t1 = self.router.classify_task(None, "Perform bulk extraction of invoice records")
        self.assertEqual(t1.deployment_name, "gpt-4o-mini")
        self.assertEqual(t1.tier_level, 1)

        # Tier 3: statutory audit keyword
        t3 = self.router.classify_task(None, "Execute statutory audit compliance verification")
        self.assertEqual(t3.deployment_name, "o1-preview")
        self.assertEqual(t3.tier_level, 3)

        # Tier 2: high-complexity architecture keyword
        t2 = self.router.classify_task(None, "Design multi-region architecture system")
        self.assertEqual(t2.deployment_name, "gpt-4o")
        self.assertEqual(t2.tier_level, 2)

    def test_router_unknown_task_defaults_to_tier2(self):
        """An unrecognised task type with a generic prompt falls back to Tier 2 (gpt-4o)."""
        tier = self.router.classify_task("unknown-task-xyz", "Help me with something")
        self.assertEqual(tier.deployment_name, "gpt-4o")
        self.assertEqual(tier.tier_level, 2)

    def test_router_tier3_overrides_tier1_task_keyword(self):
        """Tier-3 task_type pattern takes precedence over any Tier-1 prompt keyword."""
        tier = self.router.classify_task(
            "statutory-audit",
            "Perform bulk extraction of revenue recognition items",
        )
        self.assertEqual(tier.deployment_name, "o1-preview")

    # ── Cost estimation ───────────────────────────────────────────────────────

    def test_router_cost_calculation(self):
        """Blended cost is correctly computed for Tier-1 and Tier-2 models."""
        # 1M input + 500k output on gpt-4o-mini ($0.15 + $0.30 = $0.45)
        cost_mini = self.router.compute_estimated_cost("gpt-4o-mini", 1_000_000, 500_000)
        self.assertEqual(cost_mini, 0.45)

        # 1M input + 1M output on gpt-4o ($2.50 + $10.00 = $12.50)
        cost_4o = self.router.compute_estimated_cost("gpt-4o", 1_000_000, 1_000_000)
        self.assertEqual(cost_4o, 12.50)

        # Unknown model returns 0.0
        cost_unknown = self.router.compute_estimated_cost("non-existent-model", 1000, 1000)
        self.assertEqual(cost_unknown, 0.0)

    def test_router_cost_calculation_o1_preview(self):
        """Tier-3 o1-preview cost reflects frontier pricing ($15/$60 per 1M tokens)."""
        # 500k input + 200k output: (0.5 * 15.0) + (0.2 * 60.0) = 7.5 + 12.0 = 19.5
        cost = self.router.compute_estimated_cost("o1-preview", 500_000, 200_000)
        self.assertAlmostEqual(cost, 19.5, places=4)

    def test_router_cost_zero_tokens(self):
        """Zero token counts produce $0.00 cost without errors."""
        cost = self.router.compute_estimated_cost("gpt-4o-mini", 0, 0)
        self.assertEqual(cost, 0.0)

    # ── Prompt complexity classification ─────────────────────────────────────

    def test_router_complexity_classification(self):
        """Low-signal prompts are 'low'; architecture/design signals are 'high'."""
        self.assertEqual(self.router.classify_prompt_complexity("Fix syntax in Python script"), "low")
        self.assertEqual(self.router.classify_prompt_complexity("Design multi-region resilient architecture"), "high")

    # ── Circuit breaker: evaluate_extraction ─────────────────────────────────

    def test_circuit_breaker_confidence_degraded(self):
        """Model confidence below the SLA threshold triggers CONFIDENCE_DEGRADED escalation."""
        raw = {"audit_id": "AUD-1001", "risk_level": "HIGH"}
        healthy, action, instance = self.circuit_breaker.evaluate_extraction(
            MockAuditedPayload,
            raw,
            model_confidence=0.72,  # Below 0.85 threshold
        )
        self.assertFalse(healthy)
        self.assertIn("CONFIDENCE_DEGRADED", action)
        self.assertIsNone(instance)

    def test_circuit_breaker_schema_violation(self):
        """A Pydantic validation failure triggers SCHEMA_VIOLATION escalation."""
        raw = {"audit_id": "INVALID-FORMAT", "risk_level": "HIGH"}
        healthy, action, instance = self.circuit_breaker.evaluate_extraction(
            MockAuditedPayload,
            raw,
            model_confidence=0.95,
        )
        self.assertFalse(healthy)
        self.assertIn("SCHEMA_VIOLATION", action)
        self.assertIsNone(instance)

    def test_circuit_breaker_healthy_pass(self):
        """Valid payload with sufficient confidence returns the validated instance."""
        raw = {"audit_id": "AUD-1001", "risk_level": "HIGH"}
        healthy, action, instance = self.circuit_breaker.evaluate_extraction(
            MockAuditedPayload,
            raw,
            model_confidence=0.95,
        )
        self.assertTrue(healthy)
        self.assertIsNone(action)
        self.assertIsNotNone(instance)
        self.assertEqual(instance.audit_id, "AUD-1001")

    def test_circuit_breaker_confidence_at_exact_threshold(self):
        """Confidence exactly equal to the threshold is accepted (boundary condition)."""
        raw = {"audit_id": "AUD-5555", "risk_level": "LOW"}
        healthy, action, instance = self.circuit_breaker.evaluate_extraction(
            MockAuditedPayload,
            raw,
            model_confidence=0.85,  # Exactly at threshold
        )
        self.assertTrue(healthy)
        self.assertIsNone(action)
        self.assertIsNotNone(instance)

    # ── Circuit breaker: state machine ───────────────────────────────────────

    def test_circuit_breaker_state_transitions(self):
        """Failure count increments correctly; breaker opens at threshold; success resets."""
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05)
        self.assertFalse(cb.is_open())

        cb.record_failure()
        self.assertFalse(cb.is_open())  # One failure, threshold is 2

        cb.record_failure()
        self.assertTrue(cb.is_open())  # Threshold reached

        # Record success resets failure count and closes breaker
        cb.record_success()
        self.assertFalse(cb.is_open())

    def test_circuit_breaker_success_resets_partial_failure_count(self):
        """A success before the threshold is reached resets the failure counter to zero."""
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
        cb.record_failure()
        cb.record_failure()
        self.assertFalse(cb.is_open())  # Not yet at threshold

        cb.record_success()
        # After reset, two more failures should not trip it (threshold=3, count restarted)
        cb.record_failure()
        cb.record_failure()
        self.assertFalse(cb.is_open())


if __name__ == "__main__":
    unittest.main()
