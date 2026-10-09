#!/usr/bin/env python3
"""
Nexus Live Demo — Interactive prompt router with real Ollama LLM output.

Routes your prompt through the Nexus 3-tier classification engine, then
sends it to a local Ollama model that maps to the selected tier.

Usage
-----
    .venv/bin/python scripts/demo.py

Requirements
------------
    ollama must be running:  ollama serve
    Models must be pulled:   ollama pull llama3
"""

import json
import sys
import urllib.request
from datetime import datetime, timezone

from src.orchestrator.router import DynamicModelRouter
from src.schemas.telemetry import TelemetryEvent

# ---------------------------------------------------------------------------
# Tier → Ollama model mapping
# ---------------------------------------------------------------------------
# Maps Nexus tiers to locally available Ollama models.
# Tier 1 (fast/cheap) → smaller/faster model
# Tier 2 (workhorse)  → balanced model
# Tier 3 (frontier)   → best available local model

OLLAMA_MODEL_MAP = {
    1: "llama3:latest",   # Fast SLM equivalent
    2: "qwen3:8b",        # Advanced workhorse equivalent
    3: "qwen3:8b",        # Frontier equivalent (best available locally)
}

OLLAMA_URL = "http://localhost:11434/api/chat"

TIER_LABELS = {
    1: "Tier 1 — Fast SLM       (gpt-4o-mini equivalent)",
    2: "Tier 2 — Advanced Model  (gpt-4o equivalent)",
    3: "Tier 3 — Frontier Reasoning (o1-preview equivalent)",
}

BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║         N E X U S  —  Dynamic LLM Routing Engine                ║
║         Enterprise Token Optimization & Governance              ║
╚══════════════════════════════════════════════════════════════════╝
"""

SEPARATOR = "─" * 66


def call_ollama(model: str, prompt: str) -> str:
    """Send a prompt to the local Ollama /api/chat endpoint and return the response text."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"].strip()
    except Exception as exc:
        return f"[ERROR contacting Ollama: {exc}]"


def compute_cost(tier_level: int, input_tokens: int, output_tokens: int) -> float:
    pricing = {
        1: (0.15, 0.60),
        2: (2.50, 10.00),
        3: (15.00, 60.00),
    }
    inp, out = pricing.get(tier_level, (2.50, 10.00))
    return round((input_tokens / 1_000_000) * inp + (output_tokens / 1_000_000) * out, 6)


def run_demo() -> None:
    router = DynamicModelRouter()
    print(BANNER)
    print("  Type your prompt and press Enter. Type 'exit' to quit.\n")
    print("  Tip: try 'Fix the syntax error', 'Design a multi-region architecture',")
    print("       or 'Perform a statutory audit compliance check'.\n")
    print(SEPARATOR)

    while True:
        try:
            task_type_raw = input("\n  Task type (or press Enter to skip): ").strip() or None
            prompt = input("  Prompt: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  Goodbye.\n")
            break

        if prompt.lower() in {"exit", "quit", "q"}:
            print("\n  Goodbye.\n")
            break
        if not prompt:
            continue

        # ── 1. Nexus routing ───────────────────────────────────────────────
        tier = router.classify_task(task_type_raw, prompt)
        complexity = router.classify_prompt_complexity(prompt)
        ollama_model = OLLAMA_MODEL_MAP[tier.tier_level]

        # Estimate tokens (rough: words + overhead)
        input_tokens  = len(prompt.split()) * 2
        estimated_cost = compute_cost(tier.tier_level, input_tokens, 300)

        print(f"\n{SEPARATOR}")
        print(f"  🔀  NEXUS ROUTING DECISION")
        print(f"{SEPARATOR}")
        print(f"  Tier selected  : {TIER_LABELS[tier.tier_level]}")
        print(f"  Nexus model    : {tier.deployment_name}")
        print(f"  Local model    : {ollama_model}")
        print(f"  Complexity     : {complexity}")
        print(f"  Est. cost (1k) : ${estimated_cost:.6f}")
        print(f"{SEPARATOR}")

        # ── 2. Build telemetry ─────────────────────────────────────────────
        telemetry = TelemetryEvent(
            timestamp=datetime.now(timezone.utc),
            wbsElement="WBS-DEMO-LIVE-001",
            promptComplexity=complexity,
            tokenCount=max(1, input_tokens),
        )

        # ── 3. Call Ollama ─────────────────────────────────────────────────
        print(f"\n  ⏳  Sending to {ollama_model} via Ollama...\n")
        response_text = call_ollama(ollama_model, prompt)

        # ── 4. Display output + telemetry ──────────────────────────────────
        print(f"  💬  RESPONSE")
        print(f"{SEPARATOR}")
        # Word-wrap at ~64 chars
        words = response_text.split()
        line, lines = [], []
        for word in words:
            if sum(len(w) + 1 for w in line) + len(word) > 62:
                lines.append("  " + " ".join(line))
                line = [word]
            else:
                line.append(word)
        if line:
            lines.append("  " + " ".join(line))
        print("\n".join(lines))

        print(f"\n{SEPARATOR}")
        print(f"  📊  TELEMETRY AUDIT RECORD")
        print(f"{SEPARATOR}")
        for k, v in telemetry.to_dict().items():
            print(f"  {k:<20}: {v}")
        print(f"{SEPARATOR}\n")


if __name__ == "__main__":
    run_demo()
