# Nexus — GitHub Copilot Instructions

## Project Overview

**Nexus** is an enterprise LLM token optimization, governance, and resilient routing engine.
It classifies every AI request into one of three model tiers before any network socket opens,
enforces mandatory billing attribution via WBS headers, and provides automatic fallback
resilience through a built-in circuit breaker.

---

## Repository Structure

```
src/
├── orchestrator/
│   ├── router.py           # DynamicModelRouter — classify_task, prepare_request, compute_estimated_cost
│   ├── circuit_breaker.py  # CircuitBreaker — evaluate_extraction, record_failure/success, is_open
│   └── gateway_client.py   # GatewayClient — send, _send_to, _send_to_fallback, _build_telemetry
└── schemas/
    └── telemetry.py        # TelemetryEvent — Pydantic v2 strict schema

tests/
├── test_orchestrator.py    # 14 pure unit tests (no I/O)
└── test_nexus_runtime.py   # 17 behavioral/integration tests (urlopen mocked)

scripts/
└── gateway_mock.py         # Local HTTP server simulating Azure APIM
```

---

## Architecture & Core Rules

### 1. Three-Tier Model Spectrum
Every request is classified into exactly one tier — never bypass this:

| Tier | Model | Workloads |
|---|---|---|
| 1 | `gpt-4o-mini` | Bulk extraction, chunking, syntax, JSON parsing |
| 2 | `gpt-4o` | Architecture, deep debugging, complex reasoning |
| 3 | `o1-preview` | Statutory audit, revenue recognition, chain-of-thought |

**Tier 3 always wins** — if a Tier-3 pattern is detected in `task_type`, it cannot be
overridden by prompt keywords.

### 2. Perimeter Defense — WBS Enforcement
`prepare_request()` in `router.py` **must** be called before any gateway I/O.
- Required header: `X-EY-WBS-Element` matching `^WBS-[A-Z0-9_-]+$`
- Four fallback aliases accepted: `X-WBS-Element`, `X-Cost-Center`, `X-Billing-ID`
- Raise `ValueError` immediately on missing or malformed WBS — never silently continue

### 3. Pattern Matching
- Use `re.search()` against regex patterns in `TIER_1_PATTERNS`, `TIER_3_PATTERNS`, `HIGH_COMPLEXITY_PATTERNS`
- Patterns handle hyphen/underscore/space variants (e.g. `r"bulk[-_ ]extract"`)
- Always lowercase inputs before matching: `task.strip().lower()`

### 4. Circuit Breaker
Two separate responsibilities — keep them separate:
- **`evaluate_extraction()`** — schema + confidence gate (Pydantic validation + SLA threshold)
- **State machine** — `record_failure()` / `record_success()` / `is_open()` for gateway health
- `record_success()` resets `_failures` to **zero** (full reset, not decrement)
- `is_open()` auto-recovers after `recovery_timeout` — no manual reset needed

### 5. Telemetry Contract
`TelemetryEvent` is the non-negotiable audit trail. Never relax these constraints:
- `extra="forbid"` — unknown fields must raise `ValidationError`
- `strict=True` — no type coercion
- `tokenCount: int = Field(ge=1)` — zero is a schema violation
- `promptComplexity: Literal["low", "high"]` — no free-text values

---

## Coding Conventions

- **Python 3.10+** — use `X | Y` union syntax, `match/case` where appropriate
- **Pydantic v2** — use `model_validate()`, `model_dump()`, never `dict()` or `.parse_obj()`
- **Dataclasses** — `@dataclass(frozen=True)` for immutable value objects (`ModelTierConfig`, `PreparedRequest`)
- **Type annotations** — all public functions must be fully annotated; use `from __future__ import annotations` where needed
- **No third-party dependencies** beyond `pydantic` — stdlib only (`http.server`, `urllib`, `re`, `dataclasses`)
- **Docstrings** — every public class and method gets a one-line docstring minimum

---

## Testing Rules

- **No real network I/O in tests** — always patch `src.orchestrator.gateway_client.urlopen`
- **`time.sleep` must be patched** in retry tests — use `@patch("src.orchestrator.gateway_client.time.sleep", return_value=None)`
- **Use `model_validate({...})`** instead of constructor kwargs when testing invalid/extra fields — avoids static type-checker errors
- **Boundary conditions always tested** — e.g. confidence exactly at `0.85`, `tokenCount=0`, `failure_threshold=1`
- Target: **31 tests, 99% coverage** — run with:
  ```bash
  .venv/bin/pytest tests/ -v --cov=src --cov-report=term-missing
  ```

---

## Cost Pricing (per 1M tokens)

| Model | Input | Output |
|---|---|---|
| `gpt-4o-mini` | $0.15 | $0.60 |
| `gpt-4o` | $2.50 | $10.00 |
| `o1-preview` | $15.00 | $60.00 |

Cost formula: `(input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate`
Round to 6 decimal places. Unknown models return `0.0`.

---

## What NOT to Do

- ❌ Do not route directly to a model without calling `prepare_request()` first
- ❌ Do not add fields to `TelemetryEvent` without `ge`/`le`/`Literal` constraints
- ❌ Do not catch `ValidationError` silently — surface it as a `SCHEMA_VIOLATION` action string
- ❌ Do not use `time.sleep()` in tests — always patch it
- ❌ Do not install new dependencies — this project is stdlib + pydantic only
- ❌ Do not hardcode WBS values in source — they must come from request headers
