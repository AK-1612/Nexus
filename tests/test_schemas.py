"""
Unit tests for Pydantic v2 Financial Extraction & Schema Validation.
"""

from decimal import Decimal
import unittest
from pydantic import ValidationError

from src.schemas.financial import TrialBalanceLineItem, TrialBalanceExtraction, StatutoryAuditFlag


class TestFinancialSchemas(unittest.TestCase):
    """Verifies schema validation and mathematical balancing constraints."""

    def test_valid_trial_balance_extraction(self):
        payload = {
            "fiscal_year": 2026,
            "period": 3,
            "entity_code": "CORP01",
            "currency": "USD",
            "wbs_element": "WBS-CORP-998877",
            "line_items": [
                {
                    "account_code": "GL-1010-CASH",
                    "account_name": "Operating Cash",
                    "debit_amount": "500000.00",
                    "credit_amount": "0.00",
                },
                {
                    "account_code": "GL-2010-AP",
                    "account_name": "Accounts Payable",
                    "debit_amount": "0.00",
                    "credit_amount": "500000.00",
                },
            ],
        }
        tb = TrialBalanceExtraction.model_validate(payload)
        self.assertEqual(tb.total_debits, Decimal("500000.00"))
        self.assertEqual(tb.total_credits, Decimal("500000.00"))
        self.assertTrue(tb.is_balanced)

    def test_invalid_line_item_both_debit_and_credit(self):
        with self.assertRaises(ValidationError):
            TrialBalanceLineItem(
                account_code="GL-1010",
                account_name="Cash",
                debit_amount=Decimal("100.00"),
                credit_amount=Decimal("50.00"),
            )

    def test_statutory_audit_flag_validation(self):
        flag = StatutoryAuditFlag(
            finding_id="AUD-2026-001",
            severity="HIGH",
            standard_reference="ASC 606 / IFRS 15",
            description="Variable consideration milestone recognized prematurely before performance obligation satisfied.",
            remediation_required=True,
        )
        self.assertEqual(flag.severity, "HIGH")
        self.assertTrue(flag.requires_partner_signoff)


if __name__ == "__main__":
    unittest.main()
