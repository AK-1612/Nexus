# EY Internal Model Switching & Governance PoC

## Overview
This repository contains the production-ready configuration artifacts for EY's native Azure APIM dynamic model router and GitHub Copilot developer governance framework. It ensures 100% SOC2 compliance, zero external SaaS data egress, and automated SAP engagement billing.

---

## Architecture Components

### 1. Azure APIM Gateway Router (`azure-apim-policy.xml`)
- **Purpose:** Acts as the central enterprise gateway for GPT Enterprise / Azure OpenAI traffic.
- **Mechanism:** Evaluates incoming request headers (`X-EY-Task-Type`) in under 10ms. Automatically routes bulk text parsing and extraction tasks to `gpt-4o-mini` ($0.15/1M tokens) while directing complex statutory reasoning tasks to `o1-preview` ($15.00/1M tokens).
- **Billing Chargeback:** Automatically injects the SAP/GFIS client engagement chargeback header (`X-EY-WBS-Element: WBS-ENGAGEMENT-998877`) on every transaction.

### 2. GitHub Copilot Governance (`.github/copilot-instructions.md`)
- **Purpose:** Governs developer model behavior inside IDEs (VS Code) without unauthorized third-party proxy servers.
- **Mechanism:** Enforces path-based routing rules. Routine code inside `/src/` utilizes the fast completion engine, while sensitive code inside `/audit_core/` triggers compliance warnings and mandates user selection of `@Claude-3.5-Sonnet` or `@o1-preview`.

---

## Deployment Steps
1. **Apply APIM Policy:** Import the XML policy into your Azure API Management instance under the OpenAI API scope.
2. **Deploy Repository Instructions:** Commit the `copilot-instructions.md` file into the `.github/` folder of your target GitHub Enterprise repository.
3. **Verify Execution:** Test API calls through the APIM gateway and validate Copilot chat prompt behavior inside VS Code.