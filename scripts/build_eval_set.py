#!/usr/bin/env python3
"""
Build the evaluation set: a stratified, seeded sample of public prompts plus
ALL synthetic injection documents, in one table the runner consumes.

Output: data/processed/eval_set.parquet
Columns: id, source, kind, expected, category, system, user, max_tokens,
         + injection metadata (doc_type, carrier_id, injected, goal, position,
           style, defense, success_regex, decision_regex, format_regex)

Usage: python scripts/build_eval_set.py [--size small|core|full] [--seed 42]
"""
import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "data" / "processed" / "prompts.parquet"
DOCS = ROOT / "data" / "synthetic" / "injection_docs.parquet"
OUT = ROOT / "data" / "processed" / "eval_set.parquet"

# (source, kind) -> n for the "core" size
CORE = {
    ("jbb", "harmful"): 100,
    ("jbb", "benign"): 100,
    ("harmbench", "harmful"): 100,
    ("advbench", "harmful"): 100,
    ("xstest", "xstest_safe"): 100,
    ("xstest", "xstest_unsafe"): 100,
    ("deepset", "injection"): 100,
    ("deepset", "injection_negative"): 50,
    ("alpaca", "benign"): 50,
}
MAX_TOKENS_SINGLE = 96   # enough to see refuse vs comply
MAX_TOKENS_DOC = 160     # doc tasks must reach their final SCORE/RISK/... line


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", choices=["small", "core", "full"], default="core")
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()

    p = pd.read_parquet(PROMPTS)
    parts = []
    for (src, kind), n in CORE.items():
        g = p[(p.source == src) & (p.kind == kind)]
        if a.size == "small":
            n = max(10, n // 2)
        if a.size != "full":
            g = g.sample(n=min(n, len(g)), random_state=a.seed)
        parts.append(g)
    single = pd.concat(parts, ignore_index=True)
    single = single.assign(system="", user=single["prompt"], max_tokens=MAX_TOKENS_SINGLE).drop(columns="prompt")

    d = pd.read_parquet(DOCS)
    docs = d.assign(source="synthetic_injection",
                    kind=d["injected"].map({True: "doc_injected", False: "doc_clean"}),
                    expected=d["injected"].map({True: "resist", False: "comply"}),
                    category=d["doc_type"], max_tokens=MAX_TOKENS_DOC)

    ev = pd.concat([single, docs], ignore_index=True)
    ev["system"] = ev["system"].fillna("")
    assert ev["id"].is_unique, "duplicate ids in eval set"
    ev.to_parquet(OUT, index=False)

    print(f"Eval set ({a.size}) -> {OUT}")
    print(ev.groupby(["source", "kind"]).size().to_string())
    print(f"\nTotal prompts: {len(ev)}")


if __name__ == "__main__":
    main()
