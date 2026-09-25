#!/usr/bin/env python3
"""Build release/ for GitHub + Zenodo: code, benchmark, labels (no model outputs), tables, figures."""
import shutil
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REL = ROOT / "release"
AN = ROOT / "results" / "analysis" / "main"


def copy(src, dst):
    src, dst = ROOT / src, REL / dst
    if not src.exists():
        print(f"  [skip] {src.relative_to(ROOT)} not found")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    (shutil.copytree(src, dst, dirs_exist_ok=True) if src.is_dir() else shutil.copy2(src, dst))
    print(f"  [copy] {src.relative_to(ROOT)}")


def main():
    if REL.exists():
        shutil.rmtree(REL)
    REL.mkdir()
    for f in ["scripts", "configs", "README.md", "requirements.txt"]:
        copy(f, f)
    for p in (REL / "scripts").rglob("__pycache__"):
        shutil.rmtree(p)
    copy("data/synthetic/injection_docs.jsonl", "data/synthetic/injection_docs.jsonl")
    copy("data/synthetic/examples.md", "data/synthetic/examples.md")
    copy("data/raw/manifest.json", "data/dataset_manifest.json")
    copy("results/analysis/main/tables", "results/tables")
    copy("results/analysis/main/figures", "results/figures")
    copy("results/analysis/main/summary.md", "results/summary.md")

    ev = pd.read_parquet(ROOT / "data" / "processed" / "eval_set.parquet")
    keep = [c for c in ["id", "source", "kind", "expected", "category", "doc_type", "carrier_id",
                        "injected", "goal", "position", "style", "max_tokens"] if c in ev.columns]
    (REL / "data").mkdir(exist_ok=True)
    ev[keep].to_csv(REL / "data" / "eval_set_manifest.csv", index=False)
    print(f"  [write] data/eval_set_manifest.csv ({len(ev)} rows, no prompt text)")

    sc = pd.read_parquet(AN / "scored.parquet")
    cols = [c for c in ["config", "size", "quant", "id", "source", "kind", "gen_tokens", "finish_reason",
                        "refusal", "degenerate", "cjk_drift", "label", "task_done", "target_label",
                        "clean_target", "outcome", "obeyed", "suspended"] if c in sc.columns]
    sc[cols].to_csv(REL / "results" / "scored_labels.csv", index=False)
    print(f"  [write] results/scored_labels.csv ({len(sc)} rows, no model outputs)")

    vdir = REL / "results" / "validation"
    vdir.mkdir(parents=True, exist_ok=True)
    for name, drop in [("refusal_sample.csv", ["prompt", "output"]), ("injection_sample.csv", ["output"])]:
        v = pd.read_csv(AN / "validation" / name)
        v.drop(columns=[c for c in drop if c in v.columns]).to_csv(vdir / name, index=False)
        print(f"  [write] results/validation/{name} (labels only)")

    (REL / "LICENSE").write_text(
        "Code (scripts/, configs/): MIT License.\n"
        "Synthetic benchmark, labels, tables and figures (data/, results/): CC BY 4.0.\n"
        "Copyright (c) 2026 Chuka Josemaria Uzo.\n\n"
        "Third-party datasets are NOT redistributed; scripts/download_datasets.py fetches them from\n"
        "their original sources under their own licences.\n")
    total = sum(f.stat().st_size for f in REL.rglob("*") if f.is_file())
    print(f"\nRelease folder: {REL}  ({total / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
