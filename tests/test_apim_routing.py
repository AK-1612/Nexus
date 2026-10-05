"""
Enterprise Dynamic Model Routing & Governance Verification Suite.
Validates APIM dynamic routing logic, WBS element injection, and Copilot instruction compliance.
"""

import os
import unittest
import xml.etree.ElementTree as ET
from typing import Dict, Tuple

class TestAPIMRoutingSimulation(unittest.TestCase):
    """Simulates Azure APIM policy evaluation logic for routing and chargebacks."""

    def simulate_baseline_apim_policy(self, headers: Dict[str, str]) -> Tuple[str, str]:
        """
        Simulates policies/azure-apim-policy.xml:
        - If taskType == 'bulk-extraction' (case-insensitive) -> gpt-4o-mini
        - Otherwise -> o1-preview
        - WBS defaults to WBS-CORP-998877
        """
        task_type = (
            headers.get("X-Task-Type")
            or headers.get("X-Enterprise-Task-Type")
            or headers.get("X-EY-Task-Type")
            or ""
        ).strip().lower()

        if task_type == "bulk-extraction":
            target_deployment = "gpt-4o-mini"
        else:
            target_deployment = "o1-preview"

        wbs_element = (
            headers.get("X-WBS-Element")
            or headers.get("X-Cost-Center")
            or headers.get("X-Billing-ID")
            or headers.get("X-EY-WBS-Element")
            or "WBS-CORP-998877"
        )
        return target_deployment, wbs_element

    def simulate_enhanced_apim_policy(self, headers: Dict[str, str]) -> Tuple[str, str]:
        """
        Simulates policies/azure-apim-policy-enhanced.xml:
        - 3-tier spectrum (bulk-extraction -> gpt-4o-mini, statutory-audit -> o1-preview, other -> gpt-4o)
        - Dynamic WBS resolution with default fallback
        """
        task_type = (
            headers.get("X-Task-Type")
            or headers.get("X-Enterprise-Task-Type")
            or headers.get("X-EY-Task-Type")
            or "standard"
        ).strip().lower()

        if task_type in ["bulk-extraction", "sec-chunking", "table-parsing", "fast-ingestion"]:
            target_deployment = "gpt-4o-mini"
        elif task_type in ["statutory-audit", "deep-reasoning", "tax-controversy", "legal-reasoning"]:
            target_deployment = "o1-preview"
        else:
            target_deployment = "gpt-4o"

        wbs_element = (
            headers.get("X-Billing-ID")
            or headers.get("X-WBS-Element")
            or headers.get("X-Cost-Center")
            or headers.get("X-EY-Billing-ID")
            or "WBS-CORP-998877"
        )
        return target_deployment, wbs_element

    def test_baseline_bulk_extraction_routing(self):
        headers = {"X-Task-Type": "bulk-extraction"}
        deployment, wbs = self.simulate_baseline_apim_policy(headers)
        self.assertEqual(deployment, "gpt-4o-mini")
        self.assertEqual(wbs, "WBS-CORP-998877")

    def test_baseline_legacy_header_backward_compatibility(self):
        headers = {"X-EY-Task-Type": "bulk-extraction", "X-EY-WBS-Element": "WBS-ENGAGEMENT-998877"}
        deployment, wbs = self.simulate_baseline_apim_policy(headers)
        self.assertEqual(deployment, "gpt-4o-mini")
        self.assertEqual(wbs, "WBS-ENGAGEMENT-998877")

    def test_baseline_default_fallback_routing(self):
        headers = {"X-Task-Type": "complex-legal-review"}
        deployment, wbs = self.simulate_baseline_apim_policy(headers)
        self.assertEqual(deployment, "o1-preview")
        self.assertEqual(wbs, "WBS-CORP-998877")

    def test_enhanced_3_tier_routing(self):
        # Tier 1
        d1, w1 = self.simulate_enhanced_apim_policy({"X-Task-Type": "sec-chunking", "X-WBS-Element": "WBS-CLIENT-12345"})
        self.assertEqual(d1, "gpt-4o-mini")
        self.assertEqual(w1, "WBS-CLIENT-12345")

        # Tier 2
        d2, w2 = self.simulate_enhanced_apim_policy({"X-Task-Type": "general-dialogue"})
        self.assertEqual(d2, "gpt-4o")
        self.assertEqual(w2, "WBS-CORP-998877")

        # Tier 3
        d3, w3 = self.simulate_enhanced_apim_policy({"X-Task-Type": "statutory-audit"})
        self.assertEqual(d3, "o1-preview")
        self.assertEqual(w3, "WBS-CORP-998877")

    def test_copilot_instructions_file_exists(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        path = os.path.join(project_root, ".github", "copilot-instructions.md")
        self.assertTrue(os.path.exists(path), f"copilot-instructions.md must exist in .github/ (checked {path})")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("/src/**", content)
            self.assertIn("/audit_core/**", content)
            self.assertIn("@Claude-3.5-Sonnet", content)
            self.assertIn("@o1-preview", content)
            self.assertIn("Pydantic", content)

    def test_apim_policy_xml_well_formed(self):
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        policy_files = [
            os.path.join(project_root, "policies", "azure-apim-policy.xml"),
            os.path.join(project_root, "policies", "azure-apim-policy-enhanced.xml"),
            os.path.join(project_root, "policies", "fragments", "routing.xml"),
            os.path.join(project_root, "policies", "fragments", "chargeback.xml"),
            os.path.join(project_root, "policies", "fragments", "guardrails.xml"),
        ]
        for policy_path in policy_files:
            self.assertTrue(os.path.exists(policy_path), f"Policy file {policy_path} must exist")
            try:
                tree = ET.parse(policy_path)
                root = tree.getroot()
                self.assertIn(root.tag, ["policies", "fragment"])
            except ET.ParseError as e:
                self.fail(f"Policy file {policy_path} is not valid XML: {e}")


if __name__ == "__main__":
    unittest.main()
