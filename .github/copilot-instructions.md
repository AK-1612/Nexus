# EY Enterprise GitHub Copilot Governance Rules

## 1. Scope & Execution Routing
- **Standard Development (`/src/**`):** 
  - Routine code edits, documentation comments, and unit test generation must execute via the Copilot Fast Completion Engine (Target SLA: <50ms).
- **Security & Statutory Audits (`/audit_core/**`):** 
  - When reviewing code inside audit directories, Copilot must inject a pre-response compliance flag warning the user against unchecked logic.
  - Mandate step-by-step chain-of-thought verification by instructing the developer to tag `@Claude-3.5-Sonnet` or `@o1-preview`.

## 2. Code Quality & Formatting Mandates
- **Schema Validation:** All financial calculations, trial balance parsing, and data extractions must utilize strict Pydantic v2 schemas or strongly typed type hints.
- **Data Privacy:** Prohibit hardcoding credentials, API keys, or unmasked PII in generated test mocks.
