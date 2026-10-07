# Gemini Code Artifact Package

This directory contains the Gemini Code artifacts associated with the enterprise LLM routing and governance proof of concept.

## Contents

- `governance-rules.md` — developer governance rules for standard and statutory-audit code paths.
- `repository-overview.md` — overview of the repository architecture, deployment steps, tests, and compliance claims.

## Naming

The files use descriptive names so their purpose remains clear without relying on generated timestamp prefixes. The original exported filenames are retained in the repository history where applicable.

## Canonical Policy

The routing and chargeback behavior is maintained in [policies/azure-apim-policy.xml](../../policies/azure-apim-policy.xml). The exported XML fragment was removed because it was not standalone well-formed XML and duplicated the canonical policy.
