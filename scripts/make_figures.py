#!/usr/bin/env python3
"""
Redraw the paper figures from the result tables with a categorical compression axis
(F16 -> Q2_K). Usage: python scripts/make_figures.py [--run-id main]
"""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
QUANTS = ["F16", "Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q4_0", "Q3_K_M", "Q2_K"]
PARAMS = {"0.5b": 0.49e9, "1.5b": 1.54e9}
COLORS = {"0.5b": "#1f77b4", "1.5b": "#ff7f0e"}


def prep(t):
    t = t[t["quant"].isin(QUANTS)].copy()
    t["x"] = t["quant"].map({q: i for i, q in enumerate(QUANTS)})
    t["file_mb"] = t["bpw"] * t["size"].map(PARAMS) / 8 / 1e6
    return t.sort_values(["size", "x"])


def axis(ax, ylabel, title):
    ax.set_xticks(range(len(QUANTS)))
    ax.set_xticklabels(QUANTS, rotation=35, fontsize=8)
    ax.set_xlabel("quantization level  (full precision  \u2192  most compressed)", fontsize=8)
    ax.set_ylabel(ylabel)
    ax.set_ylim(-0.02, 1.02)
    ax.set_title(title, fontsize=10)
    ax.grid(alpha=0.3)


def line(ax, t, col):
    for size, g in t.groupby("size"):
        ax.plot(g["x"], g[col], marker="o", color=COLORS.get(size), label=f"Qwen2.5-{size.upper()}")
        if f"{col}_lo" in g:
            ax.fill_between(g["x"], g[f"{col}_lo"], g[f"{col}_hi"], color=COLORS.get(size), alpha=0.15)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="main")
    a = ap.parse_args()
    base = ROOT / "results" / "analysis" / a.run_id
    safety = prep(pd.read_csv(base / "tables" / "safety_by_config.csv"))
    inj = prep(pd.read_csv(base / "tables" / "injection_by_config.csv"))
    figs = base / "figures"

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    line(axes[0], safety, "harmful_refusal")
    axis(axes[0], "refusal rate", "Refusal of harmful requests (higher = safer)")
    line(axes[1], safety, "xstest_safe_refusal")
    axis(axes[1], "refusal rate", "Over-refusal of safe prompts (lower = better)")
    line(axes[2], inj, "asr")
    axis(axes[2], "attack success rate", "Hidden-instruction attack success (lower = safer)")
    for ax in axes:
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figs / "fig1_safety_vs_compression.png", dpi=200)
    plt.close(fig)

    goals = [c for c in inj.columns if c.startswith("asr_") and not c.endswith(("_lo", "_hi"))]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), sharey=True)
    for ax, (size, g) in zip(axes, inj.groupby("size")):
        for col in goals:
            ax.plot(g["x"], g[col], marker="o", label=col.replace("asr_", ""))
        axis(ax, "attack success rate", f"Qwen2.5-{size.upper()}: attack success by attacker goal")
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figs / "fig2_injection_by_goal.png", dpi=200)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    line(axes[0], safety, "benign_refusal")
    axis(axes[0], "refusal rate", "Refusal of ordinary requests (lower = better)")
    line(axes[1], safety, "degenerate_rate")
    axis(axes[1], "rate", "Degenerate / looping answers (lower = better)")
    axes[1].set_ylim(-0.005, max(0.1, safety["degenerate_rate"].max() * 1.3))
    for ax in axes:
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(figs / "fig4_helpfulness_cost.png", dpi=200)
    plt.close(fig)

    sizes = safety.pivot(index="quant", columns="size", values="file_mb").reindex(QUANTS).round(0)
    sizes.to_csv(base / "tables" / "model_file_sizes_mb.csv")
    print("Model file sizes (MB):\n" + sizes.to_string())
    print(f"\nFigures -> {figs}")


if __name__ == "__main__":
    main()
