"""
Strict Pydantic v2 schemas for Enterprise Financial Data Extraction & Audit Verification.
Enforces Output Schema Locking (Pillar 5) to eliminate logit hallucinations and token bloat.
"""

from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class TrialBalanceLineItem(BaseModel):
    """Line item in a structured corporate trial balance."""
    account_code: str = Field(..., description="General Ledger account identifier", pattern=r"^[A-Z0-9\-_]{4,16}$")
    account_name: str = Field(..., min_length=2, max_length=128, description="Standard accounting nomenclature")
    debit_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Debit balance in USD")
    credit_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), description="Credit balance in USD")

    @field_validator("credit_amount")
    @classmethod
    def validate_one_sided_entry(cls, v: Decimal, info) -> Decimal:
        debit = info.data.get("debit_amount", Decimal("0.00"))
        if debit > Decimal("0.00") and v > Decimal("0.00"):
            raise ValueError("Trial balance line item cannot record both non-zero debit and credit balances.")
        return v


class TrialBalanceExtraction(BaseModel):
    """Complete parsed corporate trial balance with mathematical proofing."""
    fiscal_year: int = Field(..., ge=2000, le=2100)
    period: int = Field(..., ge=1, le=12)
    entity_code: str = Field(..., pattern=r"^[A-Z0-9]{3,8}$")
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    wbs_element: str = Field(default="WBS-CORP-998877", pattern=r"^WBS-[A-Z0-9\-_]+$")
    line_items: List[TrialBalanceLineItem] = Field(..., min_length=1)

    @property
    def total_debits(self) -> Decimal:
        return sum((item.debit_amount for item in self.line_items), Decimal("0.00"))

    @property
    def total_credits(self) -> Decimal:
        return sum((item.credit_amount for item in self.line_items), Decimal("0.00"))

    @property
    def is_balanced(self) -> bool:
        return abs(self.total_debits - self.total_credits) < Decimal("0.01")


class StatutoryAuditFlag(BaseModel):
    """Compliance audit finding with regulatory cross-references."""
    finding_id: str
    severity: str = Field(..., pattern=r"^(CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL)$")
    standard_reference: str = Field(..., description="GAAP / IFRS / SOX Section identifier")
    description: str = Field(..., min_length=10)
    remediation_required: bool
    requires_partner_signoff: bool = True
