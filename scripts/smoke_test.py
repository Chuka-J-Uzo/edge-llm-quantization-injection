#!/usr/bin/env python3
"""
Smoke test: start llama-server for every GGUF under models/, ask one question,
record load time, output, and llama.cpp's own timings. CPU-only (-ngl 0).

Usage:
  python scripts/smoke_test.py                      # all models
  python scripts/smoke_test.py --only 0.5b-Q4_K_M   # substring filter
Output: results/smoke/smoke_test.jsonl
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
OUT = ROOT / "results" / "smoke"
PROMPT = "In one sentence, what is a supply chain risk?"


def find_llama_server(cli_value):
    for c in [cli_value, os.environ.get("LLAMA_SERVER"), shutil.which("llama-server"),
              str(Path.home() / "llama.cpp/build/bin/llama-server")]:
        if c and Path(c).is_file() and os.access(c, os.X_OK):
            return c
    sys.exit("llama-server not found. Run: source env.sh")


def list_models(only):
    paths = sorted(MODELS.glob("*/*.gguf"))
    return [p for p in paths if not only or only.lower() in p.name.lower()]


def wait_healthy(base, proc, timeout=180):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return None
        try:
            if requests.get(f"{base}/health", timeout=2).status_code == 200:
                return time.time() - t0
        except requests.RequestException:
            pass
        time.sleep(0.25)
    return None


def run_one(server, model, port, threads, max_tokens):
    base = f"http://127.0.0.1:{port}"
    log = open(OUT / f"server_{model.stem}.log", "w")
    cmd = [server, "-m", str(model), "--port", str(port), "-t", str(threads),
           "-c", "2048", "-ngl", "0", "--parallel", "1"]
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    rec = {"model": model.stem, "model_bytes": model.resolve().stat().st_size,
           "threads": threads, "prompt": PROMPT}
    try:
        load_s = wait_healthy(base, proc)
        if load_s is None:
            rec["error"] = f"server did not become healthy; see results/smoke/{Path(log.name).name}"
            return rec
        rec["load_s"] = round(load_s, 3)
        body = {"messages": [{"role": "user", "content": PROMPT}],
                "max_tokens": max_tokens, "temperature": 0, "seed": 42}
        t0 = time.time()
        r = requests.post(f"{base}/v1/chat/completions", json=body, timeout=300)
        r.raise_for_status()
        j = r.json()
        rec["wall_s"] = round(time.time() - t0, 3)
        rec["output"] = j["choices"][0]["message"]["content"]
        rec["usage"] = j.get("usage")
        rec["timings"] = j.get("timings")
        return rec
    except Exception as e:
        rec["error"] = repr(e)
        return rec
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--llama-server")
    ap.add_argument("--only", help="substring filter on model filename")
    ap.add_argument("--port", type=int, default=8089)
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--max-tokens", type=int, default=64)
    a = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    server = find_llama_server(a.llama_server)
    models = list_models(a.only)
    if not models:
        sys.exit(f"No .gguf files found under {MODELS}")
    print(f"llama-server: {server}\nthreads: {a.threads}\nmodels: {len(models)}\n")

    out_file = OUT / "smoke_test.jsonl"
    with open(out_file, "w") as f:
        for m in models:
            rec = run_one(server, m, a.port, a.threads, a.max_tokens)
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if "error" in rec:
                print(f"[FAIL] {m.stem:22s} {rec['error']}")
            else:
                tps = (rec.get("timings") or {}).get("predicted_per_second")
                tps_s = f"{tps:6.1f} tok/s" if tps else "   n/a tok/s"
                print(f"[ OK ] {m.stem:22s} load {rec['load_s']:5.2f}s  {tps_s}  | "
                      f"{rec['output'][:70]!r}")
    print(f"\nSaved -> {out_file}")


if __name__ == "__main__":
    main()
