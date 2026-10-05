# EY Internal Model Switching & Governance PoC

## Overview
This repository contains the production-ready configuration artifacts for EY's native Azure APIM dynamic model router and GitHub Copilot developer governance framework. It enforces **100% native Azure tenant enclosure (SOC2 Type II compliant)**, zero external SaaS data egress, automated SAP / GFIS client engagement billing chargebacks, and sub-50ms developer SLAs.

---

## Executive Summary & ROI Metrics
- **Annual Global Azure Savings:** **$17.3M projected savings** across 300,000 global practitioners generating 1.2B tokens monthly (reducing baseline spend from $33.6M to $16.3M).
- **Data Boundary Guarantee:** 100% Azure Subscription enclosure. Third-party proxy platforms (e.g., public SaaS routers) are strictly prohibited by EY Risk.
- **Throughput Velocity:** 3x to 5x ingestion boost on bulk data tasks with sub-10ms gateway inspection and sub-50ms IDE completion latency.

---

## 3-Tier Model Spectrum & Workload Mapping

| Tier | Target Model | Blended Cost / 1M Tokens | Target Volume Allocation | Representative Workloads & Use Cases |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1: Fast Ingestion** | Azure `gpt-4o-mini` | **$0.15** | **80%** | SEC document chunking, trial balance JSON extraction, table parsing, classification |
| **Tier 2: Standard Work** | Azure `gpt-4o` | **$2.50** | **15%** | Engagement dialogue, report synthesis, standard code generation & unit tests |
| **Tier 3: Deep Reasoning** | Azure `o1-preview` / `Claude 3.5 Sonnet` | **$15.00** | **5%** | Statutory revenue recognition, tax controversy proofing, legal indemnification, complex math |

---

## Architectural Mechanics: Swapping Patterns A, B, & C

```
                     ┌────────────────────────────────────────────────────────┐
                     │            EY Enterprise Request Entry Point           │
                     └───────────────────────────┬────────────────────────────┘
                                                 │
                  ┌──────────────────────────────┼─────────────────────────────┐
                  │                              │                             │
                  ▼                              ▼                             ▼
       [Pattern C: APIM Gateway]       [Pattern B: Copilot Rules]     [Pattern A: Agentic Handoff]
      ┌─────────────────────────┐    ┌────────────────────────────┐   ┌───────────────────────────┐
      │ Azure APIM Gateway      │    │ Developer IDE Scope Filter │   │ Python Orchestrator       │
      │ • Sub-10ms Header Check │    │ • `/src/**` -> Fast Engine │   │ • Self-evaluates logic    │
      │ • SAP WBS Injection     │    │ • `/audit_core/**` ->      │   │ • Triggers tool call:     │
      │ • Rate Limit Guardrail  │    │   Warning + `@o1-preview`  │   │   `transfer_to_o1()`      │
      └───────────┬─────────────┘    └─────────────┬──────────────┘   └─────────────┬─────────────┘
                  │                                │                                │
                  ▼                                ▼                                ▼
         Azure OpenAI Backends           VS Code / Copilot Chat           Azure OpenAI Multi-Tier
      (`gpt-4o-mini` / `o1-preview`)      (Fast / Claude / o1)            (`gpt-4o-mini` -> `o1`)
```

### 1. Pattern C — Azure APIM Gateway Router (`policies/azure-apim-policy.xml`)
- **Purpose:** Central enterprise gateway for all programmatic GPT Enterprise and Azure OpenAI API traffic.
- **Latency Impact:** 0ms to sub-10ms penalty (native C#-compiled APIM expression evaluation).
- **Mechanism:** Inspects incoming `X-EY-Task-Type` headers. Routes `bulk-extraction` workloads directly to `gpt-4o-mini` deployments while routing complex reasoning requests to `o1-preview`.
- **Engagement Chargeback:** Injects SAP/GFIS client engagement chargeback header (`X-EY-WBS-Element: WBS-ENGAGEMENT-998877`) for automated billing reconciliation.
- **Enterprise Guardrails:** Enforces a rate limit of 500 calls per 60-second renewal window.

### 2. Pattern B — GitHub Copilot Governance (`.github/copilot-instructions.md`)
- **Purpose:** Governs developer model behavior inside IDEs (VS Code) natively, eliminating unauthorized third-party proxy plugins.
- **Mechanism:** Enforces path-based routing rules:
  - Routine code in `/src/**` executes via Copilot Fast Completion Engine (<50ms SLA).
  - High-risk code in `/audit_core/**` triggers an automatic compliance warning and mandates chain-of-thought verification via `@Claude-3.5-Sonnet` or `@o1-preview`.
- **Quality Mandates:** Enforces Pydantic v2 strict schemas for all financial data calculations and strictly prohibits unmasked PII or credentials in test mocks.

### 3. Pattern A — Agentic Tool Calling & Autonomous Handoffs
- **Purpose:** In-flight escalation during multi-step autonomous agent runs.
- **Mechanism:** `gpt-4o-mini` handles primary execution; when statutory thresholds or reasoning limits are reached, the agent autonomously executes `transfer_to_o1_agent(prompt_context)` with full conversation history preserved.

---

## Repository Structure

```
.
├── .github/
│   ├── workflows/
│   │   └── ci.yml                   # Automated CI workflow validating APIM XML and test suite
│   └── copilot-instructions.md      # Pattern B: IDE Copilot governance & routing rules
├── docs/
│   ├── README.md                    # Detailed documentation and reference index
│   ├── presentations/               # Executive slide decks (.pdf & .pptx)
│   │   ├── Enterprise LLM Token Optimization..pdf
│   │   ├── Enterprise LLM Token Optimization..pptx
│   │   ├── Internal Model Switching for GPT & Copilot Ecosystems..pdf
│   │   └── Internal Model Switching for GPT & Copilot Ecosystems.pptx
│   └── research-notes/              # Architecture whitepapers & research (.pdf & .pages)
│       ├── Enterprise LLM Token Optimization & Dynamic Model Routing - Notes..pages
│       ├── Enterprise LLM Token Optimization & Dynamic Model Routing - Notes..pdf
│       ├── Enterprise LLM Token Optimization & Dynamic Model Routing..pages
│       └── Enterprise LLM Token Optimization & Dynamic Model Routing..pdf
├── policies/
│   ├── azure-apim-policy.xml        # Pattern C: Baseline APIM policy for PoC
│   └── azure-apim-policy-enhanced.xml # Pattern C+: Production 3-tier APIM policy with dynamic WBS
├── tests/
│   ├── __init__.py                  # Python test package marker
│   └── test_apim_routing.py         # Automated simulation suite for APIM routing & Copilot rules
├── .gitignore                       # Standard enterprise gitignore
├── README.md                        # Project overview & architectural guide
└── requirements.txt                 # Dependencies for development and test suites
```

---

## Deployment Steps

### Step 1: Apply Azure APIM Policy
1. Open the [Azure Portal](https://portal.azure.com/) and navigate to your **API Management Services** instance.
2. Under **APIs**, select your **Azure OpenAI Service API**.
3. Choose the target scope (**All operations** or specific POST `/chat/completions`).
4. Click **Inbound processing** -> **</> Code editor**.
5. Paste the XML policy from [`policies/azure-apim-policy.xml`](./policies/azure-apim-policy.xml) (or the production-hardened [`policies/azure-apim-policy-enhanced.xml`](./policies/azure-apim-policy-enhanced.xml)).
6. Replace `your-resource-name` with your Azure OpenAI instance name and click **Save**.

### Step 2: Deploy Repository Instructions
1. Ensure the `.github/` directory exists at the root of your enterprise repository.
2. Commit and push [`.github/copilot-instructions.md`](./.github/copilot-instructions.md) to your default branch.
3. Reload VS Code / GitHub Copilot to allow the instruction set to be ingested into developer prompt contexts.

### Step 3: Run Validation Test Suite
Execute the automated test suite locally:
```bash
python3 -m unittest discover tests -v
```

### Step 4: Verify Live Gateway Execution
Send a test bulk extraction request:
```bash
curl -X POST "https://<your-apim-gateway>.azure-api.net/openai/deployments/router/chat/completions?api-version=2024-08-01-preview" \
  -H "Content-Type: application/json" \
  -H "api-key: <APIM_SUBSCRIPTION_KEY>" \
  -H "X-EY-Task-Type: bulk-extraction" \
  -H "X-EY-Billing-ID: WBS-ENGAGEMENT-998877" \
  -d '{
    "messages": [{"role": "user", "content": "Extract trial balance line items from table."}]
  }'
```
