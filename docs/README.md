# Documentation & Architecture Repository

This directory contains the executive presentations, strategic evaluations, architectural diagrams, and empirical lab research notes supporting the EY Internal Model Switching & Governance architecture.

---

## Directory Index

### 1. Executive Presentations (`docs/presentations/`)
- **`Internal Model Switching for GPT & Copilot Ecosystems..pdf`** / **`.pptx`**:
  * Executive presentation on native dynamic routing across Azure OpenAI & GitHub Copilot ecosystems.
  * Details the $17.3M global annual savings model, 100% Azure tenant enclosure (SOC2 Type II compliance), sub-50ms developer SLA, and swapping Patterns A, B, and C.
- **`Enterprise LLM Token Optimization..pdf`** / **`.pptx`**:
  * Comprehensive slide deck on enterprise token optimization frameworks, rate limiting, and multi-tier model spectra.

### 2. Research & Architecture Notes (`docs/research-notes/`)
- **`Enterprise LLM Token Optimization & Dynamic Model Routing - Notes..pages`** / **`.pdf`**:
  * The 6 Pillars of Token Governance:
    * Layer 1: Zero-Token Interception (Semantic vector caching via Redis/GPTCache)
    * Layer 2: Prompt & Context Compression (Microsoft LLMLingua entropy scoring & cross-encoder reranking)
    * Layer 3: Provider KV Caching (Prefix tree memory reuse)
    * Layer 4: Dynamic Model Routing (Stanford FrugalGPT & UC Berkeley RouteLLM cascades)
    * Layer 5: Output Schema Locking (Grammar-guided finite state machine generation via Pydantic/Instructor)
    * Layer 6: Enterprise Gateways (APIM sidecars, real-time cost accounting, and region fallbacks)
- **`Enterprise LLM Token Optimization & Dynamic Model Routing..pages`** / **`.pdf`**:
  * Extended operational write-up and implementation guidelines.
