"""Circuit breaker and validation guardrails for model gateway traffic."""

import time
from typing import Any, Dict, Optional, Tuple

from pydantic import ValidationError


class CircuitBreaker:
    """Track gateway health and isolate repeated external-service failures."""

    def __init__(
        self,
        confidence_threshold: float = 0.85,
        fallback_model: str = "o1-preview",
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        self.confidence_threshold = confidence_threshold
        self.fallback_model = fallback_model
        self.failure_threshold = max(1, failure_threshold)
        self.recovery_timeout = recovery_timeout
        self._failures = 0
        self._opened_at: float | None = None

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._opened_at = time.monotonic()

    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if time.monotonic() - self._opened_at >= self.recovery_timeout:
            self._opened_at = None
            return False
        return True

    def evaluate_extraction(
        self,
        schema_cls: Any,
        raw_payload: Dict[str, Any],
        model_confidence: float = 1.0,
    ) -> Tuple[bool, Optional[str], Optional[Any]]:
        """Validate a model payload against its Pydantic schema and confidence SLA."""
        if model_confidence < self.confidence_threshold:
            return (
                False,
                f"CONFIDENCE_DEGRADED: Score {model_confidence:.2f} < {self.confidence_threshold:.2f} - Escalating to {self.fallback_model}",
                None,
            )

        try:
            instance = schema_cls.model_validate(raw_payload)
            return (True, None, instance)
        except ValidationError as err:
            return (
                False,
                f"SCHEMA_VIOLATION: Validation failed with {len(err.errors())} error(s) - Escalating to {self.fallback_model}",
                None,
            )
