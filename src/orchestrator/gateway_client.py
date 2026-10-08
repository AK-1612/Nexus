"""Governed gateway transport with routing, retries, fallback, and circuit breaking."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.orchestrator.circuit_breaker import CircuitBreaker
from src.orchestrator.router import DynamicModelRouter
from src.schemas.telemetry import TelemetryEvent


@dataclass(frozen=True)
class GatewayRequest:
    task_type: str
    prompt: str
    headers: Mapping[str, str]


@dataclass(frozen=True)
class GatewayResponse:
    model: str
    gateway: str
    payload: dict[str, Any]
    telemetry: TelemetryEvent


class GatewayClient:
    """Send governed requests to Azure APIM, then the local sandbox on failure."""

    def __init__(
        self,
        primary_url: str = "https://api.example.invalid/v1/chat/completions",
        fallback_url: str = "http://localhost:8080/mock-gateway",
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        self.primary_url = primary_url
        self.fallback_url = fallback_url
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.router = DynamicModelRouter()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3)

    def send(self, request: GatewayRequest) -> GatewayResponse:
        prepared = self.router.prepare_request(request)
        complexity = self.router.classify_prompt_complexity(request.prompt)
        telemetry = self._build_telemetry(request, prepared, complexity)
        request_body = json.dumps(
            {
                "model": prepared.tier.deployment_name,
                "messages": [{"role": "user", "content": request.prompt}],
            }
        ).encode("utf-8")

        if self.circuit_breaker.is_open():
            raise RuntimeError("Primary gateway circuit is open")

        try:
            payload = self._send_to(primary_url=self.primary_url, body=request_body, headers=prepared.headers)
            self.circuit_breaker.record_success()
            return GatewayResponse(payload["model"], "primary", payload, telemetry)
        except (HTTPError, URLError, TimeoutError, OSError):
            self.circuit_breaker.record_failure()
            return self._send_to_fallback(request_body, prepared.headers, telemetry)

    def _send_to(self, primary_url: str, body: bytes, headers: Mapping[str, str]) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                request = Request(
                    primary_url,
                    data=body,
                    headers=dict(headers),
                    method="POST",
                )
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("Gateway response is not a JSON object")
                    return payload
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                last_error = error
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 5))
        raise last_error or RuntimeError("Primary gateway request failed")

    def _build_telemetry(
        self,
        request: GatewayRequest,
        prepared: Any,
        complexity: str,
    ) -> TelemetryEvent:
        token_count = len(request.prompt.split()) + 1
        wbs = prepared.headers["X-EY-WBS-Element"]
        return TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            wbsElement=wbs,
            promptComplexity=complexity,
            tokenCount=token_count,
        )

    def _send_to_fallback(
        self,
        body: bytes,
        headers: Mapping[str, str],
        telemetry: TelemetryEvent,
    ) -> GatewayResponse:
        payload = self._send_to(self.fallback_url, body, headers)
        return GatewayResponse(payload["model"], "local-fallback", payload, telemetry)
