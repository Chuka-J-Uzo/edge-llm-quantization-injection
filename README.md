# edge-llm-security-telemetry

Does quantization weaken the safety of small LLMs, and can kernel-level
telemetry detect adversarial inputs on edge devices?

- Models: Qwen2.5-0.5B / 1.5B-Instruct x 8 precision levels (llama.cpp GGUF)
- Attacks: public jailbreak benchmarks + synthetic indirect prompt injection
  (CVs, emails, supplier invoices, web pages, support tickets)
- Telemetry: llama.cpp timings, perf hardware counters, bpftrace

## Quick start
    source env.sh
    python scripts/download_datasets.py
    python scripts/smoke_test.py

## Ethics
Raw model outputs to harmful prompts stay private (results/ is git-ignored).
Only aggregate scores, labels and redacted examples are published.
