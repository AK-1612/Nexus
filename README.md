# Nexus

### Enterprise LLM Token Optimization, Governance & Resilient Routing Engine

[![CI](https://github.com/AK-1612/Nexus/actions/workflows/ci.yml/badge.svg)](https://github.com/AK-1612/Nexus/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)](tests/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Governance](https://img.shields.io/badge/governance-WBS%20Enforced-orange.svg)](#perimeter-defense--wbs-enforcement)
[![Resilience](https://img.shields.io/badge/resilience-Circuit%20Breaker%20Active-success.svg)](#gateway-client--circuit-breaker-resilience)

---

## Executive Overview

Unregulated enterprise generative AI adoption leads to severe token cost inflation, unmonitored shadow traffic, missing cost-center billing attribution, and brittle single-provider dependencies. Routing every task to a frontier reasoning model is a 100× cost inefficiency.

**Nexus** resolves this by implementing a **decoupled application-level routing engine** paired with **pre-request perimeter defense**, **3-tier model spectrum classification**, **circuit breaker health isolation**, **automatic fallback resilience**, and **zero-tolerance telemetry auditing**.

```
Without Nexus:   100% Traffic ──► Frontier Reasoning (o1 / GPT-4o)      $33.6M / yr
With Nexus:       80% Traffic ──► Tier 1: Fast SLM (gpt-4o-mini)
                  15% Traffic ──► Tier 2: Advanced Workhorse (gpt-4o)     $4.8M / yr
                   5% Traffic ──► Tier 3: Frontier Reasoning (o1-preview)
──────────────────────────────────────────────────────────────────────────────────
Net Realized Enterprise Savings:                                        ~85.7% ($28.8M)
```

---

## Architecture

```text
                           [Enterprise Application Request]
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    Perimeter Defense Validation       │
                      │    (Mandatory X-EY-WBS-Element)       │
                      └──────────────────┬────────────────────┘
                                         │ Valid WBS
                                         ▼
                      ┌───────────────────────────────────────┐
                      │          DynamicModelRouter           │
                      │  • Task type pattern matching         │
                      │  • Prompt complexity classification   │
                      │  • Blended token cost estimation      │
                      └──────────────────┬────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
  [ Tier 1: Fast SLM ]         [ Tier 2: Workhorse ]           [ Tier 3: Frontier ]
     gpt-4o-mini                      gpt-4o                       o1-preview
  $0.15 / $0.60 per 1M         $2.50 / $10.00 per 1M          $15.00 / $60.00 per 1M
  Bulk extraction, syntax,     Architecture, multi-region     Statutory audit, CoT,
  chunking, JSON formatting    systems, complex logic         high-risk proofs
        │                                │                                │
        └────────────────────────────────┼────────────────────────────────┘
                                         │
                                         ▼
                      ┌───────────────────────────────────────┐
                      │             GatewayClient             │
                      │  • Exponential backoff (1s, 2s, 4s)   │
                      │  • CircuitBreaker state isolation     │
                      └──────────────────┬────────────────────┘
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   │ Healthy                                   │ Outage / Tripped
                   ▼                                           ▼
         [ Primary APIM Gateway ]                    [ Local Sandbox Fallback ]
       (https://primary-gateway/v1)                  (http://localhost:8080/mock-gateway)
                   │                                           │
                   └─────────────────────┬─────────────────────┘
                                         │
                                         ▼
                      ┌───────────────────────────────────────┐
                      │       Strict Telemetry Contract       │
                      │  • Zero-tolerance schema validation   │
                      │  • extra="forbid", strict=True        │
                      └───────────────────────────────────────┘
```

---

## Core Capabilities

### 1. Perimeter Defense & WBS Enforcement
Every outbound request is validated by `DynamicModelRouter.prepare_request()` before opening any network sockets.
- The request **must** carry a compliant `X-EY-WBS-Element` header matching `^WBS-[A-Z0-9_-]+$`.
- Requests lacking compliant billing codes are rejected immediately in-application, preventing untracked token burn.

### 2. 3-Tier Dynamic Model Spectrum
The router inspects explicit task types and prompt semantics to select the optimal model tier:

| Tier | Deployment | Target Workloads | Blended Pricing (Input / Output per 1M) |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Fast SLM)** | `gpt-4o-mini` | Bulk parsing, extraction, syntax fix, chunking, JSON formatting | $0.15 / $0.60 |
| **Tier 2 (Workhorse)** | `gpt-4o` | Enterprise architecture, multi-region workflows, deep debugging | $2.50 / $10.00 |
| **Tier 3 (Reasoning)** | `o1-preview` | Statutory audit, chain-of-thought proofs, revenue recognition | $15.00 / $60.00 |

### 3. Gateway Client & Circuit Breaker Resilience
The `GatewayClient` provides robust transport governance:
- **Exponential Backoff**: Up to `max_retries` with exponential sleep intervals (1s, 2s, 4s).
- **Circuit Breaker**: Isolates consecutive primary gateway failures (threshold-gated). When open, calls to degraded endpoints are halted to prevent cascading latency.
- **Automated Fallback**: Automatically reroutes requests to the local enterprise mock sandbox (`http://localhost:8080/mock-gateway`) if the primary gateway is unreachable.

### 4. Zero-Tolerance Telemetry Contract
Every processed transaction generates a `TelemetryEvent` strictly validated by Pydantic v2:
- Mandatory fields: `timestamp` (RFC3339), `wbsElement`, `promptComplexity` (`low` | `high`), and `tokenCount` (ge=1).
- Configured with `extra="forbid"` and `strict=True` to guarantee audit trail integrity.

---

## Repository Structure

```text
.
├── docs/
│   ├── presentations/
│   │   ├── Project Nexus.pdf                # Master executive & technical slide deck
│   │   └── Project Nexus.pptx               # Master editable presentation
│   └── README.md                            # Documentation index
├── src/
│   ├── orchestrator/
│   │   ├── __init__.py                      # Public API exports
│   │   ├── router.py                        # DynamicModelRouter & ModelTierConfig
│   │   ├── gateway_client.py                # Governed GatewayClient with fallback
│   │   └── circuit_breaker.py               # CircuitBreaker health state tracker
│   └── schemas/
│       ├── __init__.py                      # Schema exports
│       ├── telemetry.py                     # Strict Pydantic v2 TelemetryEvent
│       └── telemetry_schema.json            # JSON schema validation contract
├── scripts/
│   └── gateway_mock.py                      # Local enterprise gateway simulator
├── tests/
│   ├── test_nexus_runtime.py                # Behavioral & integration test suite
│   └── test_orchestrator.py                 # Unit tests for router & circuit breaker
├── .github/
│   ├── copilot-instructions.md              # IDE governance guidelines
│   └── workflows/ci.yml                     # CI pipeline with coverage enforcement
├── pyproject.toml                           # Modern build configuration
└── requirements.txt                         # Dependencies (pydantic>=2.0.0, etc.)
```

---

## Quickstart

### 1. Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov pyyaml
```

### 2. Launch Local Gateway Sandbox
Start the enterprise mock gateway in the background or a separate terminal:
```bash
python scripts/gateway_mock.py --port 8080
```

### 3. Dispatch Governed Requests via Gateway Client
```python
from src.orchestrator.gateway_client import GatewayClient, GatewayRequest

client = GatewayClient(
    primary_url="https://primary-gateway.corp.net/v1/chat/completions",
    fallback_url="http://127.0.0.1:8080/mock-gateway",
)

request = GatewayRequest(
    task_type="bulk-extraction",
    prompt="Extract balance sheet items from 10-K tables",
    headers={"X-EY-WBS-Element": "WBS-AUDIT-2026-Q3"},
)

response = client.send(request)
print(f"Routed Model: {response.model}")
print(f"Gateway:      {response.gateway}")
print(f"Telemetry:    {response.telemetry.to_dict()}")
```

### 4. Direct API Call via cURL
```bash
curl -X POST http://127.0.0.1:8080/chat/completions \
  -H "X-Task-Type: bulk-extraction" \
  -H "X-EY-WBS-Element: WBS-CLIENT-99001" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Parse table contents into JSON"}]}'
```

Response:
```json
{
  "id": "chatcmpl-mock-gateway-001",
  "object": "chat.completion",
  "model": "gpt-4o-mini",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "[GATEWAY SIMULATION] Request successfully routed to gpt-4o-mini (Tier 1)."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 1500,
    "completion_tokens": 300,
    "total_tokens": 1800
  },
  "enterprise_governance": {
    "task_type": "bulk-extraction",
    "wbs_element": "WBS-CLIENT-99001",
    "routed_deployment": "gpt-4o-mini",
    "estimated_transaction_cost_usd": 0.000405
  },
  "telemetry": {
    "timestamp": "2026-10-09T04:30:00Z",
    "wbsElement": "WBS-CLIENT-99001",
    "promptComplexity": "low",
    "tokenCount": 1800
  }
}
```

---

## Test Suite & Validation

**31 tests across two suites, 99% coverage.** Every critical path — routing classification, WBS perimeter enforcement, telemetry schema contracts, gateway primary/fallback/retry, and circuit breaker state transitions — has dedicated, documented coverage.

Run the test suite with coverage:
```bash
.venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing
```

---

### `tests/test_nexus_runtime.py` — Behavioral & Integration Tests (17 tests)

End-to-end behavioral tests that exercise Nexus from request ingestion to gateway dispatch. All gateway I/O is mocked via `unittest.mock.patch` against `urlopen`.

#### Routing Classification

| Test | What It Verifies |
| :--- | :--- |
| `test_low_complexity_routes_to_fast_model` | Task type `syntax` classifies to `gpt-4o-mini` (Tier 1) |
| `test_high_complexity_routes_to_advanced_model` | Task type `architecture` classifies to `gpt-4o` (Tier 2) |
| `test_tier3_task_routes_to_frontier_model` | Task type `statutory-audit` classifies to `o1-preview` (Tier 3) |

#### WBS Perimeter Defense

| Test | What It Verifies |
| :--- | :--- |
| `test_missing_wbs_is_rejected_before_gateway_contact` | Request with no billing header raises `ValueError` before any network I/O |
| `test_invalid_wbs_format_is_rejected` | Header value not matching `^WBS-[A-Z0-9_-]+$` is rejected immediately |
| `test_prepare_request_valid_wbs_enriches_headers` | Valid WBS produces a `PreparedRequest` with `X-Routed-Deployment` injected into headers |

#### Telemetry Schema Contract

| Test | What It Verifies |
| :--- | :--- |
| `test_telemetry_schema_accepts_required_fields` | Valid `TelemetryEvent` validates and exposes all four mandatory fields |
| `test_telemetry_schema_rejects_unknown_fields` | `extra="forbid"` causes `ValidationError` on any unrecognised field |
| `test_telemetry_schema_rejects_zero_token_count` | `tokenCount` must be `>= 1`; a value of `0` is a schema violation |

#### Gateway — Primary Path

| Test | What It Verifies |
| :--- | :--- |
| `test_gateway_primary_success` | Primary gateway success records WBS on telemetry and returns `gateway="primary"` |
| `test_gateway_tier3_request_routed_to_o1_preview` | Statutory-audit task sends `model=o1-preview` in the request body to the gateway |
| `test_gateway_response_payload_is_preserved` | Full gateway JSON payload (including `usage` fields) is stored verbatim on `GatewayResponse.payload` |

#### Gateway — Fallback & Retry

| Test | What It Verifies |
| :--- | :--- |
| `test_gateway_falls_back_when_primary_is_unreachable` | Primary `OSError` triggers exactly one fallback call; `gateway="local-fallback"` |
| `test_gateway_retries_exhaust_then_fall_back` | With `max_retries=2`, three primary attempts are made before the fallback is used (4 total `urlopen` calls) |

#### Circuit Breaker — Integration

| Test | What It Verifies |
| :--- | :--- |
| `test_gateway_raises_when_circuit_breaker_open` | Pre-opened breaker causes `send()` to raise `RuntimeError` without any network I/O |
| `test_circuit_breaker_opens_after_threshold` | Single failure with `failure_threshold=1` immediately trips the breaker |
| `test_circuit_breaker_recovers_after_timeout` | Breaker auto-resets to closed after `recovery_timeout` expires |

---

### `tests/test_orchestrator.py` — Unit Tests (14 tests)

Isolated unit tests for `DynamicModelRouter`, `CircuitBreaker.evaluate_extraction`, and cost estimation. No I/O.

#### Header-Based Routing

| Test | What It Verifies |
| :--- | :--- |
| `test_router_header_classification` | All three explicit task types (`bulk-extraction`, `statutory-audit`, `standard-dialogue`) map to the correct tier |
| `test_router_tier3_overrides_tier1_task_keyword` | Tier-3 `task_type` takes precedence over a Tier-1 prompt keyword |
| `test_router_unknown_task_defaults_to_tier2` | Unrecognised task type with a generic prompt defaults to `gpt-4o` (Tier 2) |

#### Prompt-Based Routing

| Test | What It Verifies |
| :--- | :--- |
| `test_router_prompt_classification` | Tier-1, Tier-2, and Tier-3 semantic keywords in the prompt drive correct classification when `task_type` is absent |
| `test_router_complexity_classification` | Low-signal prompts → `"low"`; architecture/design signals → `"high"` |

#### Cost Estimation

| Test | What It Verifies |
| :--- | :--- |
| `test_router_cost_calculation` | Blended USD cost is correct for `gpt-4o-mini` and `gpt-4o`; unknown model returns `0.0` |
| `test_router_cost_calculation_o1_preview` | Frontier model `o1-preview` cost reflects $15/$60 per 1M pricing |
| `test_router_cost_zero_tokens` | Zero token counts produce `$0.00` without errors |

#### Circuit Breaker — `evaluate_extraction`

| Test | What It Verifies |
| :--- | :--- |
| `test_circuit_breaker_confidence_degraded` | Confidence below SLA threshold triggers `CONFIDENCE_DEGRADED` escalation |
| `test_circuit_breaker_schema_violation` | Invalid Pydantic payload triggers `SCHEMA_VIOLATION` escalation |
| `test_circuit_breaker_healthy_pass` | Valid payload with sufficient confidence returns the validated instance |
| `test_circuit_breaker_confidence_at_exact_threshold` | Confidence exactly equal to `0.85` is accepted (boundary condition) |

#### Circuit Breaker — State Machine

| Test | What It Verifies |
| :--- | :--- |
| `test_circuit_breaker_state_transitions` | Failure count increments correctly; breaker opens at threshold; `record_success()` resets it |
| `test_circuit_breaker_success_resets_partial_failure_count` | A success before threshold resets the counter, requiring the full threshold to be reached again |

---

### Execution Output

```text
============================= test session starts ==============================
collected 31 items

tests/test_nexus_runtime.py::TestNexusRuntime::test_circuit_breaker_opens_after_threshold PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_circuit_breaker_recovers_after_timeout PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_gateway_falls_back_when_primary_is_unreachable PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_gateway_primary_success PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_gateway_raises_when_circuit_breaker_open PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_gateway_response_payload_is_preserved PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_gateway_retries_exhaust_then_fall_back PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_gateway_tier3_request_routed_to_o1_preview PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_high_complexity_routes_to_advanced_model PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_invalid_wbs_format_is_rejected PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_low_complexity_routes_to_fast_model PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_missing_wbs_is_rejected_before_gateway_contact PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_prepare_request_valid_wbs_enriches_headers PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_telemetry_schema_accepts_required_fields PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_telemetry_schema_rejects_unknown_fields PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_telemetry_schema_rejects_zero_token_count PASSED
tests/test_nexus_runtime.py::TestNexusRuntime::test_tier3_task_routes_to_frontier_model PASSED
tests/test_orchestrator.py::TestOrchestrator::test_circuit_breaker_confidence_at_exact_threshold PASSED
tests/test_orchestrator.py::TestOrchestrator::test_circuit_breaker_confidence_degraded PASSED
tests/test_orchestrator.py::TestOrchestrator::test_circuit_breaker_healthy_pass PASSED
tests/test_orchestrator.py::TestOrchestrator::test_circuit_breaker_schema_violation PASSED
tests/test_orchestrator.py::TestOrchestrator::test_circuit_breaker_state_transitions PASSED
tests/test_orchestrator.py::TestOrchestrator::test_circuit_breaker_success_resets_partial_failure_count PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_complexity_classification PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_cost_calculation PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_cost_calculation_o1_preview PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_cost_zero_tokens PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_header_classification PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_prompt_classification PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_tier3_overrides_tier1_task_keyword PASSED
tests/test_orchestrator.py::TestOrchestrator::test_router_unknown_task_defaults_to_tier2 PASSED

---------- coverage: platform darwin, python 3.14.6 ----------
Name                                  Stmts   Miss  Cover
---------------------------------------------------------
src/__init__.py                           1      0   100%
src/orchestrator/__init__.py              4      0   100%
src/orchestrator/circuit_breaker.py      33      0   100%
src/orchestrator/gateway_client.py       66      1    98%
src/orchestrator/router.py               54      0   100%
src/schemas/__init__.py                   2      0   100%
src/schemas/telemetry.py                 15      0   100%
---------------------------------------------------------
TOTAL                                   175      1    99%
============================== 31 passed in 0.12s ==============================
```

---

## Documentation & Presentations

- **Executive & Technical Deck**: [`docs/presentations/Project Nexus.pptx`](file:///Users/anshulk/Downloads/Task%209%20-%20Dynamic%20LLM%20Routing./docs/presentations/Project%20Nexus.pptx) / [`Project Nexus.pdf`](file:///Users/anshulk/Downloads/Task%209%20-%20Dynamic%20LLM%20Routing./docs/presentations/Project%20Nexus.pdf)
  - Authored by Anshul Vikas Kumaria, Summer Intern, AI Research Team.

---

## License

This project is licensed under the [Apache 2.0 License](LICENSE).
