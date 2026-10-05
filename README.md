# Nexus — Enterprise LLM Dynamic Routing Gateway

[![CI](https://github.com/AK-1612/Nexus/actions/workflows/ci.yml/badge.svg)](https://github.com/AK-1612/Nexus/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![SOC2](https://img.shields.io/badge/compliance-SOC2%20Type%20II-green)](#security--compliance)

Sub-10ms dynamic LLM model routing across a 3-tier model spectrum, with native Azure APIM gateway policies, automated ERP/SAP WBS cost chargebacks, and GitHub Copilot developer governance — all inside a 100% Azure tenant boundary.

---

## Why Nexus

Routing every query to a frontier model is a 100× cost mistake. Most enterprise workloads don't need it.

```
Without Nexus:  All traffic ──► GPT-4o / o1-preview      $33.6M / year
With Nexus:     80% ──► gpt-4o-mini  ($0.15 / 1M tokens)
                15% ──► gpt-4o       ($2.50 / 1M tokens)  $16.3M / year
                 5% ──► o1-preview   ($15.00 / 1M tokens)
                                                    ────────────────────
                                                    Net savings: $17.3M
```

Routing decisions happen inside Azure APIM in **<10ms** with zero external proxy egress.

---

## How It Works — 3 Patterns

### Pattern C · Azure APIM Gateway *(server-side, <10ms)*
The APIM policy inspects the `X-Task-Type` request header and routes to the right Azure OpenAI deployment. No proxy. No third-party SaaS. Compiled native C# inside your tenant.

```
X-Task-Type: bulk-extraction   ──►  gpt-4o-mini
X-Task-Type: standard          ──►  gpt-4o        (default)
X-Task-Type: statutory-audit   ──►  o1-preview
```

SAP/ERP cost-center billing code (`X-WBS-Element`) is automatically injected on every request.

### Pattern B · GitHub Copilot Governance *(IDE, <50ms)*
[`.github/copilot-instructions.md`](.github/copilot-instructions.md) enforces path-based routing inside VS Code with no plugins required.

```
/src/**          →  Copilot Fast Engine (<50ms)
/audit_core/**   →  Compliance flag + @o1-preview / @Claude-3.5-Sonnet
```

### Pattern A · Agentic Autonomous Handoff *(in-flight escalation)*
Low-cost models self-evaluate complexity and call `transfer_to_reasoning_model()` to escalate mid-task to `o1-preview` with full context preserved.

---

## Repository Structure

```
.
├── policies/
│   ├── azure-apim-policy.xml          # Baseline APIM routing policy
│   ├── azure-apim-policy-enhanced.xml # Production 3-tier policy
│   └── fragments/                     # Modular policy building blocks
│       ├── routing.xml
│       ├── chargeback.xml
│       └── guardrails.xml
├── src/
│   ├── orchestrator/
│   │   ├── router.py                  # Task classifier & cost estimator
│   │   ├── agentic_handoff.py         # Pattern A tool-calling escalation
│   │   └── circuit_breaker.py         # Confidence-gated auto-escalation
│   └── schemas/
│       └── financial.py               # Pydantic v2 schemas (trial balance, audit flags)
├── infra/
│   └── main.bicep                     # Azure APIM deployment IaC
├── scripts/
│   └── gateway_mock.py                # Local gateway simulator
├── tests/
│   ├── test_apim_routing.py
│   ├── test_orchestrator.py
│   └── test_schemas.py
└── .github/
    ├── copilot-instructions.md        # Pattern B: IDE governance rules
    └── workflows/ci.yml               # CI pipeline
```

---

## Quick Start

```bash
git clone https://github.com/AK-1612/Nexus.git
cd Nexus

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run local gateway mock
python3 scripts/gateway_mock.py --port 8080

# Test routing
curl -X POST http://127.0.0.1:8080/chat/completions \
  -H "X-Task-Type: bulk-extraction" \
  -H "X-WBS-Element: WBS-CLIENT-001" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Extract line items from this table."}]}'
```

Response includes routing decision and estimated cost:
```json
{
  "model": "gpt-4o-mini",
  "enterprise_governance": {
    "routed_deployment": "gpt-4o-mini",
    "wbs_element": "WBS-CLIENT-001",
    "estimated_transaction_cost_usd": 0.000405
  }
}
```

---

## Deploy to Azure

**Via Azure CLI (Bicep):**
```bash
az deployment group create \
  --resource-group rg-nexus-prod \
  --template-file infra/main.bicep \
  --parameters apimServiceName=apim-nexus azureOpenAIServiceName=aoai-nexus-eastus
```

**Via Azure Portal:**
1. API Management → your OpenAI API → **Inbound processing** → `</>` Code editor
2. Paste [`policies/azure-apim-policy-enhanced.xml`](policies/azure-apim-policy-enhanced.xml)
3. Replace `{{azure-openai-resource-name}}` → Save

---

## Tests

```bash
pytest tests/ -v
```
```
15 passed in 0.05s
```

Covers APIM XML validation, 3-tier routing simulation, Pydantic schema enforcement, autonomous handoff tool schema, and circuit breaker escalation logic.

---

## Security & Compliance

- **Zero external egress** — all routing runs inside Azure APIM, no SaaS proxies
- **Zero-trust auth** — Azure Managed Identity; no API keys in policy
- **SOC2 Type II boundary** — prompt data never leaves your Azure subscription
- **Subscription-keyed rate limiting** — prevents noisy-neighbor quota exhaustion
- **Automated ERP billing** — `X-WBS-Element` stamped on every transaction for SAP reconciliation

---

## License

[Apache 2.0](LICENSE)
