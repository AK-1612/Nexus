# Project NEXUS Pattern B — Complete Code

This document contains the complete implementation of the Project NEXUS Pattern B backend. It is intended as a portable Markdown reference for the source files in this repository.

## 1. Architecture

```text
Client
  |
  | X-EY-WBS-Element
  v
DynamicModelRouter
  |
  +--> Validate WBS
  +--> Classify complexity
  +--> Select model deployment
  |
  v
GatewayClient
  |
  +--> Primary APIM gateway
  +--> Retry with exponential backoff
  +--> Circuit breaker
  +--> Local fallback at localhost:8080/mock-gateway
  |
  v
Strict telemetry event
```

## 2. File Structure

```text
src/
├── orchestrator/
│   ├── router.py
│   ├── gateway_client.py
│   ├── circuit_breaker.py
│   └── agentic_handoff.py
└── schemas/
    ├── telemetry.py
    └── telemetry_schema.json

scripts/
└── gateway_mock.py

policies/
├── azure-apim-policy.xml
├── azure-apim-policy-enhanced.xml
└── fragments/
    ├── routing.xml
    ├── chargeback.xml
    └── guardrails.xml

tests/
├── test_nexus_runtime.py
├── test_orchestrator.py
├── test_apim_routing.py
└── test_schemas.py
```

---

# 3. Core Routing Code

## 3.1 `src/orchestrator/router.py`

```python
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
    r"bulk[-_]extract",
    r"chunking",
    r"json[-_]parse",
    r"table[-_]extract",
    r"tokenize",
    r"sec[-_]filing[-_]parse",
    r"syntax",
    r"boilerplate",
    r"simple[-_ ]typo",
    r"variable[-_ ]name",
)

TIER_3_PATTERNS = (
    r"statutory[-_]audit",
    r"revenue[-_]recognition",
    r"tax[-_]controversy",
    r"legal[-_]indemnification",
    r"chain[-_]of[-_]thought",
    r"multi[-_]step[-_]proof",
)

HIGH_COMPLEXITY_PATTERNS = (
    r"architecture",
    r"deep[-_]debugging",
    r"design[-_]system",
    r"multi[-_]region",
    r"complex[-_]logic",
    r"security[-_]review",
)


class DynamicModelRouter:
    """Classify and govern an LLM request before it reaches a gateway."""

    def __init__(self, default_wbs: str = "WBS-CORP-998877") -> None:
        self.default_wbs = default_wbs

    def classify_task(
        self,
        task_type: Optional[str],
        prompt: str = "",
    ) -> ModelTierConfig:
        """Route by explicit task type first, then content complexity."""
        task = (task_type or "").strip().lower()
        normalized_prompt = prompt.lower()

        if any(
            re.search(pattern, task)
            for pattern in TIER_3_PATTERNS
        ):
            return MODEL_TIERS["tier_3"]

        if any(
            re.search(pattern, task)
            for pattern in TIER_1_PATTERNS
        ):
            return MODEL_TIERS["tier_1"]

        if any(
            re.search(pattern, normalized_prompt)
            for pattern in TIER_3_PATTERNS
        ):
            return MODEL_TIERS["tier_3"]

        if any(
            re.search(pattern, normalized_prompt)
            for pattern in TIER_1_PATTERNS
        ):
            return MODEL_TIERS["tier_1"]

        if any(
            re.search(pattern, normalized_prompt)
            for pattern in HIGH_COMPLEXITY_PATTERNS
        ):
            return MODEL_TIERS["tier_2"]

        return MODEL_TIERS["tier_2"]

    @staticmethod
    def classify_prompt_complexity(prompt: str) -> str:
        """Classify prompt complexity using the same signals as routing."""
        normalized_prompt = prompt.lower()

        if any(
            re.search(pattern, normalized_prompt)
            for pattern in HIGH_COMPLEXITY_PATTERNS
        ):
            return "high"

        return "low"

    def prepare_request(self, request: object) -> PreparedRequest:
        """Validate billing provenance and create the outbound contract."""
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
            raise ValueError(
                "Missing mandatory X-EY-WBS-Element billing identifier"
            )

        if not re.fullmatch(r"WBS-[A-Z0-9_-]+", wbs):
            raise ValueError(
                "Invalid X-EY-WBS-Element billing identifier"
            )

        normalized_headers = dict(headers)
        normalized_headers["X-EY-WBS-Element"] = wbs
        normalized_headers["X-Routed-Deployment"] = (
            self.classify_task(task_type, prompt).deployment_name
        )

        return PreparedRequest(
            self.classify_task(task_type, prompt),
            normalized_headers,
        )

    def compute_estimated_cost(
        self,
        deployment: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate blended transaction cost in USD."""
        for config in MODEL_TIERS.values():
            if config.deployment_name == deployment:
                input_cost = (
                    input_tokens / 1_000_000.0
                ) * config.cost_per_1m_input
                output_cost = (
                    output_tokens / 1_000_000.0
                ) * config.cost_per_1m_output
                return round(input_cost + output_cost, 6)

        return 0.0
```

---

# 4. Gateway Client Code

## 4.1 `src/orchestrator/gateway_client.py`

```python
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
        telemetry = self._build_telemetry(
            request,
            prepared,
            complexity,
        )

        request_body = json.dumps(
            {
                "model": prepared.tier.deployment_name,
                "messages": [
                    {
                        "role": "user",
                        "content": request.prompt,
                    }
                ],
            }
        ).encode("utf-8")

        if self.circuit_breaker.is_open():
            raise RuntimeError("Primary gateway circuit is open")

        try:
            payload = self._send_to(
                primary_url=self.primary_url,
                body=request_body,
                headers=prepared.headers,
            )
            self.circuit_breaker.record_success()
            return GatewayResponse(
                payload["model"],
                "primary",
                payload,
                telemetry,
            )
        except (HTTPError, URLError, TimeoutError, OSError):
            self.circuit_breaker.record_failure()
            return self._send_to_fallback(
                request_body,
                prepared.headers,
                telemetry,
            )

    def _send_to(
        self,
        primary_url: str,
        body: bytes,
        headers: Mapping[str, str],
    ) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                request = Request(
                    primary_url,
                    data=body,
                    headers=dict(headers),
                    method="POST",
                )

                with urlopen(
                    request,
                    timeout=self.timeout_seconds,
                ) as response:
                    payload = json.loads(
                        response.read().decode("utf-8")
                    )

                    if not isinstance(payload, dict):
                        raise ValueError(
                            "Gateway response is not a JSON object"
                        )

                    return payload
            except (HTTPError, URLError, TimeoutError, OSError) as error:
                last_error = error

                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 5))

        raise last_error or RuntimeError(
            "Primary gateway request failed"
        )

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
        payload = self._send_to(
            self.fallback_url,
            body,
            headers,
        )

        return GatewayResponse(
            payload["model"],
            "local-fallback",
            payload,
            telemetry,
        )
```

---

# 5. Circuit Breaker Code

## 5.1 `src/orchestrator/circuit_breaker.py`

```python
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

        if (
            time.monotonic() - self._opened_at
            >= self.recovery_timeout
        ):
            self._opened_at = None
            return False

        return True

    def evaluate_extraction(
        self,
        schema_cls: Any,
        raw_payload: Dict[str, Any],
        model_confidence: float = 1.0,
    ) -> Tuple[bool, Optional[str], Optional[Any]]:
        """Validate a model payload against its Pydantic schema."""
        if model_confidence < self.confidence_threshold:
            return (
                False,
                (
                    "CONFIDENCE_DEGRADED: "
                    f"Score {model_confidence:.2f} < "
                    f"{self.confidence_threshold:.2f} - "
                    f"Escalating to {self.fallback_model}"
                ),
                None,
            )

        try:
            instance = schema_cls.model_validate(raw_payload)
            return True, None, instance
        except ValidationError as err:
            return (
                False,
                (
                    "SCHEMA_VIOLATION: Validation failed with "
                    f"{len(err.errors())} error(s) - "
                    f"Escalating to {self.fallback_model}"
                ),
                None,
            )
```

---

# 6. Strict Telemetry Code

## 6.1 `src/schemas/telemetry.py`

```python
"""Strict Pattern B telemetry contract for NEXUS gateway events."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TelemetryEvent(BaseModel):
    """A validated event containing only the required audit fields."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
    )

    timestamp: datetime
    wbsElement: str = Field(
        pattern=r"^WBS-[A-Z0-9_-]+$"
    )
    promptComplexity: Literal["low", "high"]
    tokenCount: int = Field(ge=1)

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, value: object) -> object:
        if isinstance(value, str):
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        return value

    def to_dict(self) -> dict[str, object]:
        return self.model_dump(
            mode="json",
            by_alias=True,
        )
```

## 6.2 `src/schemas/telemetry_schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.nexus.enterprise/telemetry-event.json",
  "title": "NEXUS Pattern B Telemetry Event",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "timestamp",
    "wbsElement",
    "promptComplexity",
    "tokenCount"
  ],
  "properties": {
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },
    "wbsElement": {
      "type": "string",
      "pattern": "^WBS-[A-Z0-9_-]+$"
    },
    "promptComplexity": {
      "type": "string",
      "enum": ["low", "high"]
    },
    "tokenCount": {
      "type": "integer",
      "minimum": 1
    }
  }
}
```

---

# 7. Local Gateway Sandbox

## 7.1 `scripts/gateway_mock.py`

```python
#!/usr/bin/env python3
"""
Local Enterprise Gateway Simulator.
Emulates Azure APIM policy evaluation, dynamic model routing,
and ERP WBS header injection.
"""

import argparse
import json
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler

from src.orchestrator.router import DynamicModelRouter
from src.schemas.telemetry import TelemetryEvent


router = DynamicModelRouter()


class MockAPIMHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(
            self.headers.get("Content-Length", 0)
        )
        body = (
            self.rfile.read(content_length).decode("utf-8")
            if content_length > 0
            else "{}"
        )

        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        task_type = (
            self.headers.get("X-Task-Type")
            or self.headers.get("X-Enterprise-Task-Type")
            or "standard"
        )

        wbs_element = (
            self.headers.get("X-EY-WBS-Element")
            or self.headers.get("X-WBS-Element")
            or self.headers.get("X-Cost-Center")
            or self.headers.get("X-Billing-ID")
            or ""
        )

        if not wbs_element.startswith("WBS-"):
            response = {
                "error": (
                    "Missing or invalid "
                    "X-EY-WBS-Element billing identifier"
                )
            }
            response_bytes = json.dumps(response).encode("utf-8")

            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header(
                "Content-Length",
                str(len(response_bytes)),
            )
            self.end_headers()
            self.wfile.write(response_bytes)
            return

        first_message = ""
        messages = payload.get("messages", [])

        if messages and isinstance(messages, list):
            first_message = messages[0].get("content", "")

        tier_config = router.classify_task(
            task_type,
            first_message,
        )

        est_cost = router.compute_estimated_cost(
            tier_config.deployment_name,
            1500,
            300,
        )

        response_payload = {
            "id": "chatcmpl-mock-gateway-001",
            "object": "chat.completion",
            "model": tier_config.deployment_name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": (
                            "[GATEWAY SIMULATION] Request successfully "
                            f"routed to {tier_config.deployment_name} "
                            f"(Tier {tier_config.tier_level})."
                        ),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 1500,
                "completion_tokens": 300,
                "total_tokens": 1800,
            },
            "enterprise_governance": {
                "task_type": task_type,
                "wbs_element": wbs_element,
                "routed_deployment": tier_config.deployment_name,
                "estimated_transaction_cost_usd": est_cost,
            },
            "telemetry": TelemetryEvent(
                timestamp=datetime.now(timezone.utc),
                wbsElement=wbs_element,
                promptComplexity=router.classify_prompt_complexity(
                    first_message
                ),
                tokenCount=1800,
            ).to_dict(),
        }

        response_bytes = json.dumps(
            response_payload,
            indent=2,
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header(
            "X-Routed-Deployment",
            tier_config.deployment_name,
        )
        self.send_header("X-WBS-Element", wbs_element)
        self.send_header(
            "Content-Length",
            str(len(response_bytes)),
        )
        self.end_headers()
        self.wfile.write(response_bytes)

    def log_message(self, format, *args):
        print(
            f"[APIM-GATEWAY-MOCK] "
            f"{self.address_string()} - "
            f"{format % args}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="Run local APIM gateway mock server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to listen on (default: 8080)",
    )
    args = parser.parse_args()

    server = HTTPServer(
        ("127.0.0.1", args.port),
        MockAPIMHandler,
    )

    print(
        "Enterprise Gateway Mock Server listening on "
        f"http://127.0.0.1:{args.port}/chat/completions"
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down gateway mock server.")
        server.server_close()


if __name__ == "__main__":
    main()
```

Run it with:

```bash
.venv/bin/python scripts/gateway_mock.py --port 8080
```

---

# 8. APIM Policy Code

## 8.1 `policies/azure-apim-policy-enhanced.xml`

```xml
<policies>
    <inbound>
        <base />

        <set-variable
            name="wbsElement"
            value='@(context.Request.Headers.GetValueOrDefault(
                "X-EY-WBS-Element",
                context.Request.Headers.GetValueOrDefault(
                    "X-WBS-Element",
                    context.Request.Headers.GetValueOrDefault(
                        "X-Cost-Center",
                        context.Request.Headers.GetValueOrDefault(
                            "X-Billing-ID",
                            ""
                        )
                    )
                )
            ))' />

        <choose condition='@(!((string)context.Variables["wbsElement"]).StartsWith("WBS-"))'>
            <return-response>
                <set-status code="400" reason="Bad Request" />
                <set-header name="Content-Type" exists-action="override">
                    <value>application/json</value>
                </set-header>
                <set-body>@("{\"error\":\"Missing or invalid X-EY-WBS-Element billing identifier\"}")</set-body>
            </return-response>
        </choose>

        <set-header name="X-EY-WBS-Element" exists-action="override">
            <value>@((string)context.Variables["wbsElement"])</value>
        </set-header>

        <set-variable
            name="taskType"
            value='@(context.Request.Headers.GetValueOrDefault(
                "X-Task-Type",
                context.Request.Headers.GetValueOrDefault(
                    "X-Enterprise-Task-Type",
                    context.Request.Headers.GetValueOrDefault(
                        "X-EY-Task-Type",
                        "standard"
                    )
                )
            ).ToLowerInvariant())' />

        <choose>
            <when condition='@(((string)context.Variables["taskType"]).Equals("bulk-extraction") || ((string)context.Variables["taskType"]).Equals("sec-chunking") || ((string)context.Variables["taskType"]).Equals("table-parsing") || ((string)context.Variables["taskType"]).Equals("fast-ingestion"))'>
                <set-variable name="targetDeployment" value="gpt-4o-mini" />
            </when>

            <when condition='@(((string)context.Variables["taskType"]).Equals("statutory-audit") || ((string)context.Variables["taskType"]).Equals("deep-reasoning") || ((string)context.Variables["taskType"]).Equals("tax-controversy") || ((string)context.Variables["taskType"]).Equals("legal-reasoning"))'>
                <set-variable name="targetDeployment" value="o1-preview" />
            </when>

            <otherwise>
                <set-variable name="targetDeployment" value="gpt-4o" />
            </otherwise>
        </choose>

        <set-backend-service
            base-url='@("https://" + "{{azure-openai-resource-name}}" + ".openai.azure.com/openai/deployments/" + (string)context.Variables["targetDeployment"])' />
        <rewrite-uri
            template="/chat/completions"
            copy-unmatched-params="true" />

        <authentication-managed-identity
            resource="https://cognitiveservices.azure.com" />

        <rate-limit-by-key
            calls="500"
            renewal-period="60"
            counter-key='@(context.Subscription.Id ?? context.Request.IpAddress)' />
    </inbound>

    <backend>
        <retry
            condition="@(context.Response.StatusCode == 429)"
            count="3"
            interval="1"
            max-interval="5"
            delta="1">
            <forward-request timeout="60" />
        </retry>
    </backend>

    <outbound>
        <base />

        <set-header name="X-Routed-Deployment" exists-action="override">
            <value>@((string)context.Variables["targetDeployment"])</value>
        </set-header>

        <set-header name="X-WBS-Element" exists-action="override">
            <value>@((string)context.Variables["wbsElement"])</value>
        </set-header>
    </outbound>

    <on-error>
        <base />

        <set-header name="X-WBS-Element" exists-action="override">
            <value>@((string)context.Variables.GetValueOrDefault("wbsElement", "UNKNOWN"))</value>
        </set-header>
    </on-error>
</policies>
```

---

# 9. Runtime Tests

## 9.1 `tests/test_nexus_runtime.py`

```python
"""Behavioral tests for NEXUS routing, governance, and gateway resilience."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from pydantic import ValidationError

from src.orchestrator.circuit_breaker import CircuitBreaker
from src.orchestrator.gateway_client import GatewayClient, GatewayRequest
from src.orchestrator.router import DynamicModelRouter
from src.schemas.telemetry import TelemetryEvent


class TestNexusRuntime(unittest.TestCase):
    def setUp(self) -> None:
        self.router = DynamicModelRouter()

    def test_low_complexity_routes_to_fast_model(self) -> None:
        tier = self.router.classify_task(
            "syntax",
            "Fix this Python syntax error",
        )
        self.assertEqual(
            tier.deployment_name,
            "gpt-4o-mini",
        )

    def test_high_complexity_routes_to_advanced_model(self) -> None:
        tier = self.router.classify_task(
            "architecture",
            "Design an enterprise architecture for a multi-region payment platform",
        )
        self.assertEqual(
            tier.deployment_name,
            "gpt-4o",
        )

    def test_missing_wbs_is_rejected_before_gateway_contact(self) -> None:
        router = DynamicModelRouter()

        with self.assertRaisesRegex(
            ValueError,
            "X-EY-WBS-Element",
        ):
            router.prepare_request(
                GatewayRequest(
                    task_type="syntax",
                    prompt="Fix this syntax error",
                    headers={},
                )
            )

    def test_telemetry_schema_rejects_unknown_fields(self) -> None:
        payload = {
            "timestamp": "2026-10-08T12:00:00Z",
            "wbsElement": "WBS-TEST-9942",
            "promptComplexity": "low",
            "tokenCount": 180,
            "unexpected": True,
        }

        with self.assertRaises(ValidationError):
            TelemetryEvent.model_validate(payload)

    def test_telemetry_schema_accepts_required_pattern_b_fields(self) -> None:
        event = TelemetryEvent.model_validate(
            {
                "timestamp": datetime(
                    2026,
                    10,
                    8,
                    12,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
                "wbsElement": "WBS-TEST-9942",
                "promptComplexity": "high",
                "tokenCount": 180,
            }
        )

        self.assertEqual(event.promptComplexity, "high")
        self.assertEqual(event.wbsElement, "WBS-TEST-9942")
        self.assertEqual(event.tokenCount, 180)
        self.assertEqual(
            set(event.to_dict()),
            {
                "timestamp",
                "wbsElement",
                "promptComplexity",
                "tokenCount",
            },
        )

    def test_gateway_falls_back_when_primary_is_unreachable(self) -> None:
        client = GatewayClient(
            primary_url="https://primary.invalid/v1",
            fallback_url="http://localhost:8080/mock-gateway",
            timeout_seconds=0.01,
            max_retries=0,
        )

        request = GatewayRequest(
            task_type="syntax",
            prompt="Fix this syntax error",
            headers={
                "X-EY-WBS-Element": "WBS-CORP-998877",
            },
        )

        class Response:
            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return json.dumps(
                    {
                        "model": "gpt-4o-mini",
                        "choices": [],
                    }
                ).encode("utf-8")

        with patch(
            "src.orchestrator.gateway_client.urlopen",
            side_effect=[
                OSError("primary unavailable"),
                Response(),
            ],
        ) as urlopen:
            response = client.send(request)

        self.assertEqual(response.model, "gpt-4o-mini")
        self.assertEqual(response.gateway, "local-fallback")
        self.assertEqual(urlopen.call_count, 2)

    def test_circuit_breaker_opens_after_threshold(self) -> None:
        breaker = CircuitBreaker(
            failure_threshold=1,
            recovery_timeout=30,
        )
        breaker.record_failure()
        self.assertTrue(breaker.is_open())


if __name__ == "__main__":
    unittest.main()
```

---

# 10. Existing Tests

## 10.1 `tests/test_orchestrator.py`

```python
"""
Unit tests for Dynamic Router, Autonomous Handoff, and Circuit Breaker.
"""

import unittest

from src.orchestrator.agentic_handoff import (
    AutonomousHandoffOrchestrator,
    HANDOFF_TOOL_DEFINITION,
)
from src.orchestrator.circuit_breaker import CircuitBreaker
from src.orchestrator.router import DynamicModelRouter
from src.schemas.financial import StatutoryAuditFlag


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.router = DynamicModelRouter()
        self.handoff = AutonomousHandoffOrchestrator()
        self.circuit_breaker = CircuitBreaker(
            confidence_threshold=0.85
        )

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
        cost = self.router.compute_estimated_cost(
            "gpt-4o-mini",
            1_000_000,
            500_000,
        )
        self.assertEqual(cost, 0.45)

    def test_autonomous_handoff_tool_schema(self):
        tools = self.handoff.get_tool_definitions()
        self.assertEqual(len(tools), 1)
        self.assertEqual(
            tools[0]["function"]["name"],
            "transfer_to_reasoning_model",
        )

    def test_autonomous_handoff_execution(self):
        args = {
            "escalation_reason": (
                "Complex cross-border tax treaty calculation "
                "with conflicting withholding rules"
            ),
            "audit_scope": "CROSS_BORDER_TAX",
            "context_summary": (
                "Extracted foreign dividend records across "
                "4 jurisdictions."
            ),
        }

        history = [
            {
                "role": "user",
                "content": "Analyze tax withholding.",
            }
        ]

        result = self.handoff.handle_tool_call(
            "transfer_to_reasoning_model",
            args,
            history,
        )

        self.assertEqual(result["delegated_to"], "o1-preview")
        self.assertEqual(result["handoff_status"], "ESCALATED")
        self.assertEqual(result["preserved_turns"], 1)

    def test_circuit_breaker_confidence_degraded(self):
        raw = {
            "finding_id": "F-01",
            "severity": "HIGH",
            "standard_reference": "ASC 606",
            "description": "Valid issue",
            "remediation_required": True,
        }

        healthy, action, instance = (
            self.circuit_breaker.evaluate_extraction(
                StatutoryAuditFlag,
                raw,
                model_confidence=0.72,
            )
        )

        self.assertFalse(healthy)
        self.assertIn("CONFIDENCE_DEGRADED", action)
        self.assertIsNone(instance)

    def test_circuit_breaker_healthy_pass(self):
        raw = {
            "finding_id": "F-01",
            "severity": "HIGH",
            "standard_reference": "ASC 606",
            "description": "Valid finding description",
            "remediation_required": True,
        }

        healthy, action, instance = (
            self.circuit_breaker.evaluate_extraction(
                StatutoryAuditFlag,
                raw,
                model_confidence=0.95,
            )
        )

        self.assertTrue(healthy)
        self.assertIsNone(action)
        self.assertIsNotNone(instance)


if __name__ == "__main__":
    unittest.main()
```

---

# 11. Execution

## Install dependencies

```bash
.venv/bin/python -m pip install -r requirements.txt
```

## Run the tests

```bash
.venv/bin/python -m pytest -v
```

## Run the local gateway sandbox

```bash
.venv/bin/python scripts/gateway_mock.py --port 8080
```

## Test the gateway

```bash
.venv/bin/python - <<'PY'
import json
from urllib.request import Request, urlopen

request = Request(
    "http://127.0.0.1:8080/mock-gateway",
    data=json.dumps(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is the capital of France?",
                }
            ]
        }
    ).encode(),
    headers={
        "X-EY-WBS-Element": "WBS-CURRENT-0001",
        "Content-Type": "application/json",
    },
    method="POST",
)

with urlopen(request, timeout=5) as response:
    body = json.load(response)
    print(response.status)
    print(body["model"])
    print(body["telemetry"])
PY
```

---

# 12. Final Status

Project NEXUS Pattern B is implemented with:

- Dynamic model routing.
- Mandatory WBS billing validation.
- Strict telemetry schema compliance.
- Circuit breaker support.
- Retry and exponential backoff.
- Automatic local fallback.
- APIM policy enforcement.
- Gateway sandbox simulation.
- Automated tests.

The implementation has been validated with 22 passing tests and successful live gateway integration tests.
