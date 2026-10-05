"""
Dynamic LLM Task Router & Complexity Classifier.
Evaluates query complexity and maps incoming requests to optimal model tiers (Pillar 4).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
import re


@dataclass(frozen=True)
class ModelTierConfig:
    deployment_name: str
    tier_level: int
    cost_per_1m_input: float
    cost_per_1m_output: float
    description: str


MODEL_TIERS: Dict[str, ModelTierConfig] = {
    "tier_1": ModelTierConfig(
        deployment_name="gpt-4o-mini",
        tier_level=1,
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        description="Fast SLM: Bulk parsing, extraction, JSON formatting, chunking",
    ),
    "tier_2": ModelTierConfig(
        deployment_name="gpt-4o",
        tier_level=2,
        cost_per_1m_input=2.50,
        cost_per_1m_output=10.00,
        description="Standard Workhorse: Engagement dialogue, report synthesis, routine unit tests",
    ),
    "tier_3": ModelTierConfig(
        deployment_name="o1-preview",
        tier_level=3,
        cost_per_1m_input=15.00,
        cost_per_1m_output=60.00,
        description="Frontier Reasoning: Statutory revenue recognition, tax controversy proofing, logic proofs",
    ),
}

# Task category signatures
TIER_1_PATTERNS = [
    r"bulk[-_]extract",
    r"chunking",
    r"json[-_]parse",
    r"table[-_]extract",
    r"tokenize",
    r"sec[-_]filing[-_]parse",
]

TIER_3_PATTERNS = [
    r"statutory[-_]audit",
    r"revenue[-_]recognition",
    r"tax[-_]controversy",
    r"legal[-_]indemnification",
    r"chain[-_]of[-_]thought",
    r"multi[-_]step[-_]proof",
]


class DynamicModelRouter:
    """Enterprise dynamic router matching task signatures to Azure OpenAI endpoints."""

    def __init__(self, default_wbs: str = "WBS-CORP-998877"):
        self.default_wbs = default_wbs

    def classify_task(self, task_type: Optional[str], prompt: str = "") -> ModelTierConfig:
        """Classifies request based on explicit task header or semantic query heuristics."""
        task = (task_type or "").strip().lower()

        # 1. Header-driven deterministic routing (APIM Pattern C)
        for pattern in TIER_1_PATTERNS:
            if re.search(pattern, task):
                return MODEL_TIERS["tier_1"]

        for pattern in TIER_3_PATTERNS:
            if re.search(pattern, task):
                return MODEL_TIERS["tier_3"]

        # 2. Content heuristics fallback
        normalized_prompt = prompt.lower()
        if any(re.search(p, normalized_prompt) for p in TIER_3_PATTERNS):
            return MODEL_TIERS["tier_3"]

        if any(re.search(p, normalized_prompt) for p in TIER_1_PATTERNS):
            return MODEL_TIERS["tier_1"]

        # 3. Default to Tier 2 Standard (protecting spend from defaulting to o1)
        return MODEL_TIERS["tier_2"]

    def compute_estimated_cost(
        self,
        deployment: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculates blended dollar transaction cost for ERP/SAP chargeback reconciliation."""
        for cfg in MODEL_TIERS.values():
            if cfg.deployment_name == deployment:
                input_cost = (input_tokens / 1_000_000.0) * cfg.cost_per_1m_input
                output_cost = (output_tokens / 1_000_000.0) * cfg.cost_per_1m_output
                return round(input_cost + output_cost, 6)
        return 0.0
