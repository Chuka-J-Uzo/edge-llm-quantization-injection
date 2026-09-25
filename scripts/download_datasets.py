#!/usr/bin/env python3
"""
Download public red-teaming / baseline datasets and normalise them into ONE table.

AdvBench, HarmBench and XSTest are pulled from the authors' GitHub repos first
(ungated, canonical); the HuggingFace mirrors are only a fallback.

Output:
  data/raw/<name>.parquet          untouched copy of each source
  data/raw/manifest.json           what was downloaded, from where, when, rows
  data/processed/prompts.parquet   unified table: id, source, kind, category, expected, prompt

  kind      : harmful | benign | xstest_safe | xstest_unsafe | injection | injection_negative
  expected  : refuse | comply | resist   (what a well-behaved model SHOULD do)
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from datasets import load_dataset

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
SEED = 42
ALPACA_N = 300

GH = "https://raw.githubusercontent.com"
ADVBENCH_CSV = f"{GH}/llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv"
HARMBENCH_CSV = f"{GH}/centerforaisafety/HarmBench/main/data/behavior_datasets/harmbench_behaviors_text_all.csv"
XSTEST_CSV = f"{GH}/paul-rottger/xstest/main/xstest_prompts.csv"


def frame(source, kind, expected, prompts, category=None):
    return pd.DataFrame({
        "source": source, "kind": kind,
        "category": category if category is not None else None,
        "expected": expected, "prompt": prompts,
    })


def first_ok(*attempts):
    """Try (label, callable) pairs in order; return (label, DataFrame) of the first that works."""
    errors = []
    for label, fn in attempts:
        try:
            return label, fn()
        except Exception as e:
            errors.append(f"{label}: {e!r}"[:250])
    raise RuntimeError(" | ".join(errors))


def col(df, *names):
    for n in names:
        if n in df.columns:
            return df[n]
    raise KeyError(f"none of {names} in columns {list(df.columns)}")


# ---------------- loaders (each returns (origin, normalised_df)) ----------------

def load_jbb():
    parts = []
    for split, kind, exp in [("harmful", "harmful", "refuse"), ("benign", "benign", "comply")]:
        df = load_dataset("JailbreakBench/JBB-Behaviors", "behaviors", split=split).to_pandas()
        df.to_parquet(RAW / f"jbb_{split}.parquet")
        parts.append(frame("jbb", kind, exp, df["Goal"], df.get("Category")))
    return "hf:JailbreakBench/JBB-Behaviors", pd.concat(parts, ignore_index=True)


def load_advbench():
    origin, df = first_ok(
        (ADVBENCH_CSV, lambda: pd.read_csv(ADVBENCH_CSV)),
        ("hf:walledai/AdvBench", lambda: load_dataset("walledai/AdvBench", split="train").to_pandas()),
    )
    df.to_parquet(RAW / "advbench.parquet")
    return origin, frame("advbench", "harmful", "refuse", col(df, "goal", "prompt"))


def load_harmbench():
    def gh():
        d = pd.read_csv(HARMBENCH_CSV)
        return d[d["FunctionalCategory"] == "standard"]
    origin, df = first_ok(
        (HARMBENCH_CSV, gh),
        ("hf:walledai/HarmBench", lambda: load_dataset("walledai/HarmBench", "standard", split="train").to_pandas()),
    )
    df.to_parquet(RAW / "harmbench_standard.parquet")
    return origin, frame("harmbench", "harmful", "refuse",
                         col(df, "Behavior", "prompt"), col(df, "SemanticCategory", "category"))


def load_xstest():
    origin, df = first_ok(
        (XSTEST_CSV, lambda: pd.read_csv(XSTEST_CSV)),
        ("hf:walledai/XSTest", lambda: load_dataset("walledai/XSTest", split="test").to_pandas()),
    )
    df.to_parquet(RAW / "xstest.parquet")
    if "label" in df.columns:
        safe = df["label"].astype(str).str.lower().eq("safe")
    else:  # XSTest convention: contrast_* types are the unsafe prompts
        safe = ~df["type"].astype(str).str.startswith("contrast")
    typ = df.get("type")
    return origin, pd.concat([
        frame("xstest", "xstest_safe", "comply", df.loc[safe, "prompt"],
              typ[safe] if typ is not None else None),
        frame("xstest", "xstest_unsafe", "refuse", df.loc[~safe, "prompt"],
              typ[~safe] if typ is not None else None),
    ], ignore_index=True)


def load_deepset():
    parts = []
    for split in ["train", "test"]:
        df = load_dataset("deepset/prompt-injections", split=split).to_pandas()
        df.to_parquet(RAW / f"deepset_{split}.parquet")
        parts.append(df)
    df = pd.concat(parts, ignore_index=True)
    inj = df["label"] == 1
    return "hf:deepset/prompt-injections", pd.concat([
        frame("deepset", "injection", "resist", df.loc[inj, "text"]),
        frame("deepset", "injection_negative", "comply", df.loc[~inj, "text"]),
    ], ignore_index=True)


def load_alpaca():
    df = load_dataset("tatsu-lab/alpaca", split="train").to_pandas()
    df = df[df["input"].str.strip() == ""].sample(n=ALPACA_N, random_state=SEED)
    df.to_parquet(RAW / "alpaca_sample.parquet")
    return "hf:tatsu-lab/alpaca", frame("alpaca", "benign", "comply", df["instruction"])


LOADERS = {
    "jbb": load_jbb,
    "advbench": load_advbench,
    "harmbench": load_harmbench,
    "xstest": load_xstest,
    "deepset": load_deepset,
    "alpaca": load_alpaca,
}


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    manifest, frames, failed = {}, [], []

    for name, fn in LOADERS.items():
        print(f"-> {name:10s} ... ", end="", flush=True)
        try:
            origin, df = fn()
            frames.append(df)
            manifest[name] = {"origin": origin, "rows": len(df),
                              "downloaded_utc": datetime.now(timezone.utc).isoformat()}
            print(f"{len(df)} rows  [{origin}]")
        except Exception as e:
            failed.append((name, repr(e)))
            print("FAILED")

    if not frames:
        sys.exit("Nothing downloaded. Check your internet connection.")

    all_df = pd.concat(frames, ignore_index=True)
    all_df["prompt"] = all_df["prompt"].astype(str).str.strip()
    all_df = all_df[all_df["prompt"].str.len() > 0]
    before = len(all_df)
    all_df = all_df.drop_duplicates(subset="prompt", keep="first")
    all_df.insert(0, "id", [hashlib.sha1(f"{s}|{p}".encode()).hexdigest()[:12]
                            for s, p in zip(all_df["source"], all_df["prompt"])])
    all_df = all_df.reset_index(drop=True)
    all_df.to_parquet(OUT / "prompts.parquet", index=False)

    (RAW / "manifest.json").write_text(json.dumps(
        {"datasets": manifest, "failed": failed, "dedup_removed": before - len(all_df)}, indent=2))

    print("\nUnified table -> data/processed/prompts.parquet")
    print(all_df.groupby(["source", "kind", "expected"]).size().to_string())
    print(f"\nTotal: {len(all_df)} prompts ({before - len(all_df)} duplicates removed)")
    if failed:
        print("\nFailed sources (paste these errors to Claude):")
        for n, e in failed:
            print(f"  {n}: {e[:400]}")


if __name__ == "__main__":
    main()
