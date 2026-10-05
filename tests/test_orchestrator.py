"""
Unit tests for Dynamic Router, Autonomous Handoff, and Circuit Breaker.
"""

import unittest
from src.orchestrator.router import DynamicModelRouter, MODEL_TIERS
from src.orchestrator.agentic_handoff import AutonomousHandoffOrchestrator, HANDOFF_TOOL_DEFINITION
from src.orchestrator.circuit_breaker import CircuitBreaker
from src.schemas.financial import StatutoryAuditFlag


class TestOrchestrator(unittest.TestCase):
    """Verifies dynamic classification, tool calling handoffs, and circuit breaker escalation."""

    def setUp(self):
        self.router = DynamicModelRouter()
        self.handoff = AutonomousHandoffOrchestrator()
        self.circuit_breaker = CircuitBreaker(confidence_threshold=0.85)

    def test_router_header_classification(self):
        t1 = self.router.classify_task("bulk-extraction")
        self.assertEqual(t1.deployment_name, "gpt-4o-mini")
        self.assertEqual(t1.tier_level, 1)

        t3 = self.router.classify_task("statutory-audit")
        self.assertEqual(t3.deployment_name, "o1-preview")
        self.assertEqual(t3.tier_level, 3)

        t2 = self.router.classify_task("standard-dialogue")
        self.assertEqual(t2.deployment_name, "gpt-4o")
        self.assertEqual(t2.tier_level, 2)

    def test_router_cost_calculation(self):
        # 1M input + 500k output on gpt-4o-mini ($0.15 + $0.30 = $0.45)
        cost = self.router.compute_estimated_cost("gpt-4o-mini", 1_000_000, 500_000)
        self.assertEqual(cost, 0.45)

    def test_autonomous_handoff_tool_schema(self):
        tools = self.handoff.get_tool_definitions()
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["function"]["name"], "transfer_to_reasoning_model")

    def test_autonomous_handoff_execution(self):
        args = {
            "escalation_reason": "Complex cross-border tax treaty calculation with conflicting withholding rules",
            "audit_scope": "CROSS_BORDER_TAX",
            "context_summary": "Extracted foreign dividend records across 4 jurisdictions.",
        }
        history = [{"role": "user", "content": "Analyze tax withholding."}]
        result = self.handoff.handle_tool_call("transfer_to_reasoning_model", args, history)
        self.assertEqual(result["delegated_to"], "o1-preview")
        self.assertEqual(result["handoff_status"], "ESCALATED")
        self.assertEqual(result["preserved_turns"], 1)

    def test_circuit_breaker_confidence_degraded(self):
        raw = {"finding_id": "F-01", "severity": "HIGH", "standard_reference": "ASC 606", "description": "Valid issue", "remediation_required": True}
        healthy, action, instance = self.circuit_breaker.evaluate_extraction(
            StatutoryAuditFlag,
            raw,
            model_confidence=0.72,  # Below 0.85 threshold
        )
        self.assertFalse(healthy)
        self.assertIn("CONFIDENCE_DEGRADED", action)
        self.assertIsNone(instance)

    def test_circuit_breaker_healthy_pass(self):
        raw = {"finding_id": "F-01", "severity": "HIGH", "standard_reference": "ASC 606", "description": "Valid finding description", "remediation_required": True}
        healthy, action, instance = self.circuit_breaker.evaluate_extraction(
            StatutoryAuditFlag,
            raw,
            model_confidence=0.95,
        )
        self.assertTrue(healthy)
        self.assertIsNone(action)
        self.assertIsNotNone(instance)


if __name__ == "__main__":
    unittest.main()
