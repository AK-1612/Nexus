"""Dynamic LLM routing with explicit governance and billing enforcement."""

from dataclasses import dataclass
from typing import Dict, Mapping, Optional
import re


@dataclass(frozen=True)
class ModelTierConfig:
    deployment_name: str
    tier_level: int
    cost_per_1m_input: float
    cost_per_1m_output: float
    description: str


@dataclass(frozen=True)
class PreparedRequest:
    tier: ModelTierConfig
    headers: Mapping[str, str]


MODEL_TIERS: Dict[str, ModelTierConfig] = {
    "tier_1": ModelTierConfig(
        deployment_name="gpt-4o-mini",
        tier_level=1,
        cost_per_1m_input=0.15,
        cost_per_1m_output=0.60,
        description="Fast SLM: bulk parsing, extraction, JSON formatting, and chunking",
    ),
    "tier_2": ModelTierConfig(
        deployment_name="gpt-4o",
        tier_level=2,
        cost_per_1m_input=2.50,
        cost_per_1m_output=10.00,
        description="Advanced workhorse: architecture, deep debugging, and complex reasoning",
    ),
    "tier_3": ModelTierConfig(
        deployment_name="o1-preview",
        tier_level=3,
        cost_per_1m_input=15.00,
        cost_per_1m_output=60.00,
        description="Frontier reasoning: statutory audit and high-risk proofing",
    ),
}

TIER_1_PATTERNS = (
    r"bulk[-_ ]extract",
    r"chunking",
    r"json[-_ ]parse",
    r"table[-_ ]extract",
    r"tokenize",
    r"sec[-_ ]filing[-_ ]parse",
    r"syntax",
    r"boilerplate",
    r"simple[-_ ]typo",
    r"variable[-_ ]name",
)
TIER_3_PATTERNS = (
    r"statutory[-_ ]audit",
    r"revenue[-_ ]recognition",
    r"tax[-_ ]controversy",
    r"legal[-_ ]indemnification",
    r"chain[-_ ]of[-_ ]thought",
    r"multi[-_ ]step[-_ ]proof",
)
HIGH_COMPLEXITY_PATTERNS = (
    r"architecture",
    r"deep[-_ ]debugging",
    r"design[-_ ]system",
    r"multi[-_ ]region",
    r"complex[-_ ]logic",
    r"security[-_ ]review",
)


class DynamicModelRouter:
    """Classify and govern an LLM request before it reaches a gateway."""

    def __init__(self, default_wbs: str = "WBS-CORP-998877") -> None:
        self.default_wbs = default_wbs

    def classify_task(self, task_type: Optional[str], prompt: str = "") -> ModelTierConfig:
        """Route by explicit task type first, then content complexity."""
        task = (task_type or "").strip().lower()
        normalized_prompt = prompt.lower()

        if any(re.search(pattern, task) for pattern in TIER_3_PATTERNS):
            return MODEL_TIERS["tier_3"]
        if any(re.search(pattern, task) for pattern in TIER_1_PATTERNS):
            return MODEL_TIERS["tier_1"]
        if any(re.search(pattern, normalized_prompt) for pattern in TIER_3_PATTERNS):
            return MODEL_TIERS["tier_3"]
        if any(re.search(pattern, normalized_prompt) for pattern in TIER_1_PATTERNS):
            return MODEL_TIERS["tier_1"]
        if any(re.search(pattern, normalized_prompt) for pattern in HIGH_COMPLEXITY_PATTERNS):
            return MODEL_TIERS["tier_2"]
        return MODEL_TIERS["tier_2"]

    @staticmethod
    def classify_prompt_complexity(prompt: str) -> str:
        """Classify prompt complexity using the same high-risk signals as routing."""
        normalized_prompt = prompt.lower()
        if any(re.search(pattern, normalized_prompt) for pattern in HIGH_COMPLEXITY_PATTERNS):
            return "high"
        return "low"

    def prepare_request(self, request: object) -> PreparedRequest:
        """Validate billing provenance and create the outbound request contract."""
        task_type = getattr(request, "task_type", "")
        prompt = getattr(request, "prompt", "")
        headers = getattr(request, "headers", {}) or {}
        wbs = next(
            (
                headers[name].strip()
                for name in (
                    "X-EY-WBS-Element",
                    "X-WBS-Element",
                    "X-Cost-Center",
                    "X-Billing-ID",
                )
                if headers.get(name, "").strip()
            ),
            "",
        )
        if not wbs:
            raise ValueError("Missing mandatory X-EY-WBS-Element billing identifier")
        if not re.fullmatch(r"WBS-[A-Z0-9_-]+", wbs):
            raise ValueError("Invalid X-EY-WBS-Element billing identifier")

        normalized_headers = dict(headers)
        normalized_headers["X-EY-WBS-Element"] = wbs
        normalized_headers["X-Routed-Deployment"] = self.classify_task(task_type, prompt).deployment_name
        return PreparedRequest(self.classify_task(task_type, prompt), normalized_headers)

    def compute_estimated_cost(
        self,
        deployment: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate the blended transaction cost in USD."""
        for config in MODEL_TIERS.values():
            if config.deployment_name == deployment:
                input_cost = (input_tokens / 1_000_000.0) * config.cost_per_1m_input
                output_cost = (output_tokens / 1_000_000.0) * config.cost_per_1m_output
                return round(input_cost + output_cost, 6)
        return 0.0
