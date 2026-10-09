# Project Nexus Documentation

This directory contains the core documentation and presentation assets for **Nexus: Enterprise LLM Token Optimization, Governance & Resilient Routing Engine**.

---

## Directory Index

### 1. Master Presentations (`docs/presentations/`)
- **[`Project Nexus.pptx`](file:///Users/anshulk/Downloads/Task%209%20-%20Dynamic%20LLM%20Routing./docs/presentations/Project%20Nexus.pptx)** & **[`Project Nexus.pdf`](file:///Users/anshulk/Downloads/Task%209%20-%20Dynamic%20LLM%20Routing./docs/presentations/Project%20Nexus.pdf)**:
  - **Author**: Anshul Vikas Kumaria (Summer Intern, AI Research Team)
  - **Topic**: Enterprise LLM Token Optimization, Governance & Resilient Routing Engine
  - **Key Sections**:
    - **The Problem**: Rapid token cost inflation, unmonitored model calls, lack of cost-center billing attribution, single-provider failure risks.
    - **The Solution**: Decoupled application-level routing engine combining pre-request perimeter validation, 3-tier model spectrum selection, automated fallback resilience, and zero-tolerance telemetry auditing.
    - **3-Tier Model Spectrum**:
      - *Tier 1 (Fast SLM)*: `gpt-4o-mini` ($0.15 / $0.60 per 1M tokens) for bulk extraction, parsing, formatting, and chunking.
      - *Tier 2 (General Workhorse)*: `gpt-4o` ($2.50 / $10.00 per 1M tokens) for architecture, multi-region workflows, and complex logic.
      - *Tier 3 (Frontier Reasoning)*: `o1-preview` ($15.00 / $60.00 per 1M tokens) for statutory audit and high-risk proofs.
    - **Perimeter Defense**: Strict `X-EY-WBS-Element` header verification before external gateway contact.
    - **Resilient Transport**: Retries with exponential backoff (1s, 2s, 4s), circuit breaker trip protection, and automatic fallback to local sandbox.
    - **Telemetry & Audit**: Zero-tolerance schema contract (`TelemetryEvent`) with `extra="forbid"`.

### 2. Telemetry Schema (`src/schemas/`)
- **[`src/schemas/telemetry.py`](file:///Users/anshulk/Downloads/Task%209%20-%20Dynamic%20LLM%20Routing./src/schemas/telemetry.py)**: Pydantic v2 strict schema model.
- **[`src/schemas/telemetry_schema.json`](file:///Users/anshulk/Downloads/Task%209%20-%20Dynamic%20LLM%20Routing./src/schemas/telemetry_schema.json)**: JSON schema specification validating `timestamp`, `wbsElement`, `promptComplexity`, and `tokenCount`.
