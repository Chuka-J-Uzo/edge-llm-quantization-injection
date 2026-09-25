#!/usr/bin/env python3
"""
Main experiment runner.

For each model config (size x quant):
  1. launch llama-server UNDER `perf stat -I <ms>` (counters for all server threads,
     sampled every interval, written as CSV)
  2. start a system sampler (RSS, CPU%, threads, ctx switches, CPU freq, temperature)
  3. warm up, then send every eval prompt (shuffled, seeded), recording epoch
     start/end timestamps so telemetry can be joined per request later
  4. shut down cleanly; move to next config

Resumable: completed (config, prompt id) pairs are skipped on re-run.

Layout: results/runs/<run_id>/
  <config>.jsonl            one line per prompt: output, timings, timestamps
  <config>.perf.<part>.csv  perf interval counters (time is seconds since perf_t0)
  <config>.sys.<part>.csv   system sampler
  <config>.meta.<part>.json perf_t0, command, versions, settings
  <config>.server.<part>.log

Pilot:  python scripts/run_experiment.py --run-id pilot --limit 30 --configs 0.5b-Q4_K_M 1.5b-Q4_K_M
Full:   python scripts/run_experiment.py --run-id main
"""
import argparse
import json
import os
import platform
import random
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pandas as pd
import psutil
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "models"
EVAL = ROOT / "data" / "processed" / "eval_set.parquet"
CFG = ROOT / "configs" / "experiment.yaml"

# Most informative quants first, so a partial run is still useful
PRIORITY = ["F16", "Q8_0", "Q4_K_M", "Q2_K", "Q6_K", "Q5_K_M", "Q4_0", "Q3_K_M"]
DEFAULT_EVENTS = ["cycles", "instructions", "cache-references", "cache-misses",
                  "branch-misses", "context-switches", "page-faults"]


# ------------------------------------------------------------------ helpers
def load_cfg():
    try:
        return yaml.safe_load(CFG.read_text()) or {}
    except FileNotFoundError:
        return {}


def discover_configs(filters):
    found = {}
    for p in MODELS.glob("*/*.gguf"):
        base, quant = p.stem.rsplit("-", 1)          # qwen2.5-0.5b , Q4_K_M
        found[p.stem] = dict(config=p.stem, size=base.split("-")[-1], quant=quant, path=p)
    ordered = []
    for q in PRIORITY:
        for size in sorted({c["size"] for c in found.values()}):
            for c in found.values():
                if c["quant"] == q and c["size"] == size:
                    ordered.append(c)
    ordered += [c for c in found.values() if c not in ordered]
    if filters:
        ordered = [c for c in ordered if any(f.lower() in c["config"].lower() for f in filters)]
    return ordered


def find_llama_server():
    for c in [os.environ.get("LLAMA_SERVER"), shutil.which("llama-server")]:
        if c and Path(c).is_file():
            return c
    sys.exit("llama-server not found. Run: source env.sh")


def on_ac_power():
    """True if mains power is connected (or if it cannot be determined, e.g. desktops)."""
    base = Path("/sys/class/power_supply")
    mains = []
    for p in base.glob("*"):
        try:
            if (p / "type").read_text().strip() == "Mains":
                mains.append(p)
        except OSError:
            pass
    if not mains:
        return True
    return any((p / "online").read_text().strip() == "1" for p in mains)


def background_load(seconds=3.0):
    """System-wide CPU% over a short window + the top CPU consumers."""
    procs = list(psutil.process_iter(["pid", "name"]))
    for pr in procs:
        try:
            pr.cpu_percent(None)
        except psutil.Error:
            pass
    total = psutil.cpu_percent(interval=seconds)
    top = []
    for pr in procs:
        try:
            top.append((pr.cpu_percent(None), pr.info["name"], pr.info["pid"]))
        except psutil.Error:
            pass
    top.sort(reverse=True)
    return total, [t for t in top[:5] if t[0] > 5]


def wait_for_ac(run_dir, stop_flag, settle):
    if on_ac_power():
        return
    t0 = time.time()
    msg = f"{time.strftime('%Y-%m-%d %H:%M:%S')} on battery -> paused"
    print(f"  !! {msg}", flush=True)
    with open(run_dir / "pauses.log", "a") as f:
        f.write(msg + "\n")
    while not on_ac_power() and not stop_flag.is_set():
        time.sleep(5)
    if stop_flag.is_set():
        return
    print(f"  .. power back after {(time.time() - t0) / 60:.1f} min; settling {settle:.0f}s", flush=True)
    time.sleep(settle)
    with open(run_dir / "pauses.log", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} resumed after {time.time() - t0:.0f}s\n")


def cpu_temp():
    try:
        temps = psutil.sensors_temperatures()
        for key in ("coretemp", "k10temp", "acpitz"):
            if key in temps and temps[key]:
                return temps[key][0].current
    except Exception:
        pass
    return None


class SysSampler(threading.Thread):
    def __init__(self, pid, path, interval=0.5):
        super().__init__(daemon=True)
        self.pid, self.path, self.interval = pid, path, interval
        self.stop_evt = threading.Event()

    def run(self):
        try:
            proc = psutil.Process(self.pid)
            proc.cpu_percent(None)
        except psutil.NoSuchProcess:
            return
        with open(self.path, "w") as f:
            f.write("ts,rss_mb,cpu_pct,num_threads,ctx_vol,ctx_invol,freq_mhz,temp_c,sys_cpu_pct,load1,on_ac\n")
            psutil.cpu_percent(None)
            while not self.stop_evt.is_set():
                try:
                    mi, cs = proc.memory_info(), proc.num_ctx_switches()
                    freq = psutil.cpu_freq()
                    f.write(f"{time.time():.3f},{mi.rss / 2**20:.1f},{proc.cpu_percent(None):.1f},"
                            f"{proc.num_threads()},{cs.voluntary},{cs.involuntary},"
                            f"{freq.current if freq else ''},{cpu_temp() or ''},"
                            f"{psutil.cpu_percent(None):.1f},{os.getloadavg()[0]:.2f},{int(on_ac_power())}\n")
                    f.flush()
                except psutil.NoSuchProcess:
                    break
                self.stop_evt.wait(self.interval)


def find_server_pid(parent_pid, timeout=15):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            for ch in psutil.Process(parent_pid).children(recursive=True):
                if "llama-server" in ch.name() or any("llama-server" in x for x in ch.cmdline()[:1]):
                    return ch.pid
        except psutil.NoSuchProcess:
            return None
        time.sleep(0.1)
    return None


def wait_healthy(base, proc, timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if proc.poll() is not None:
            return False
        try:
            if requests.get(f"{base}/health", timeout=2).status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(0.25)
    return False


def chat(base, system, user, max_tokens, seed):
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    body = {"messages": msgs, "max_tokens": int(max_tokens), "temperature": 0, "seed": seed,
            "cache_prompt": False}
    r = requests.post(f"{base}/v1/chat/completions", json=body, timeout=900)
    r.raise_for_status()
    return r.json()


def done_ids(path):
    ids = set()
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rec = json.loads(line)
                if "error" not in rec:
                    ids.add(rec["id"])
            except json.JSONDecodeError:
                pass
    return ids


# ------------------------------------------------------------------ one config
def run_config(c, ev, a, cfg, server_bin, run_dir, stop_flag):
    out_jsonl = run_dir / f"{c['config']}.jsonl"
    finished = done_ids(out_jsonl)
    order = list(ev.index)
    random.Random(f"{a.seed}-{c['config']}").shuffle(order)   # seeded order per config
    todo = ev.loc[order]
    if a.limit:
        todo = todo.head(a.limit)                              # pilot: random mixed subset
    todo = todo[~todo["id"].isin(finished)]
    if todo.empty:
        print(f"  {c['config']}: already complete, skipping")
        return

    part = len(list(run_dir.glob(f"{c['config']}.meta.*.json")))
    perf_csv = run_dir / f"{c['config']}.perf.{part}.csv"
    sys_csv = run_dir / f"{c['config']}.sys.{part}.csv"
    log_path = run_dir / f"{c['config']}.server.{part}.log"
    inf = cfg.get("inference", {})
    port = a.port
    base = f"http://127.0.0.1:{port}"

    server_cmd = [server_bin, "-m", str(c["path"]), "--port", str(port), "-t", str(a.threads),
                  "-c", str(inf.get("ctx_size", 2048)), "-ngl", "0", "--parallel", "1"]
    if a.cpus:
        server_cmd = ["taskset", "-c", a.cpus] + server_cmd
    events = cfg.get("telemetry", {}).get("perf_events", DEFAULT_EVENTS)
    if a.no_perf:
        cmd = server_cmd
    else:
        cmd = ["perf", "stat", "-x", ",", "-I", str(a.perf_interval), "-e", ",".join(events),
               "-o", str(perf_csv), "--"] + server_cmd

    if not a.ignore_battery:
        wait_for_ac(run_dir, stop_flag, a.settle)
    bg_total, bg_top = background_load()
    if bg_total > 15:
        print(f"  !! background CPU load {bg_total:.0f}% before start. Top: "
              + ", ".join(f"{n}({p:.0f}%)" for p, n, _ in bg_top), flush=True)
    log = open(log_path, "w")
    perf_t0 = time.time()
    proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT)
    server_pid = proc.pid if a.no_perf else find_server_pid(proc.pid)
    meta = dict(config=c["config"], size=c["size"], quant=c["quant"], part=part,
                model_path=str(c["path"].resolve()), model_bytes=c["path"].resolve().stat().st_size,
                perf_t0=perf_t0, perf_interval_ms=a.perf_interval, perf_events=events,
                threads=a.threads, cpus=a.cpus, cmd=cmd, server_pid=server_pid,
                host=platform.node(), kernel=platform.release(), seed=a.seed,
                background_cpu_pct_at_start=bg_total,
                background_top=[dict(name=n, pid=pid, cpu=p) for p, n, pid in bg_top])
    sampler = None
    try:
        if not wait_healthy(base, proc):
            print(f"  {c['config']}: server failed to start, see {log_path}")
            return
        if server_pid:
            sampler = SysSampler(server_pid, sys_csv)
            sampler.start()
        for _ in range(2):  # warm-up (not recorded)
            chat(base, "", "Say hello in five words.", 16, a.seed)
        meta["t_measure_start"] = time.time()
        (run_dir / f"{c['config']}.meta.{part}.json").write_text(json.dumps(meta, indent=2))

        n, t_cfg = len(todo), time.time()
        with open(out_jsonl, "a") as f:
            for i, (_, row) in enumerate(todo.iterrows(), 1):
                if stop_flag.is_set():
                    break
                if not a.ignore_battery and not on_ac_power():
                    wait_for_ac(run_dir, stop_flag, a.settle)
                    if stop_flag.is_set():
                        break
                rec = dict(run_id=a.run_id, config=c["config"], size=c["size"], quant=c["quant"],
                           part=part, id=row["id"], source=row["source"], kind=row["kind"])
                t_start, m_start = time.time(), time.monotonic()
                try:
                    j = chat(base, row["system"], row["user"], row["max_tokens"], a.seed)
                    ch = j["choices"][0]
                    rec.update(output=ch["message"]["content"], finish_reason=ch.get("finish_reason"),
                               usage=j.get("usage"), timings=j.get("timings"))
                except Exception as e:
                    rec["error"] = repr(e)
                t_end, m_end = time.time(), time.monotonic()
                # CLOCK_MONOTONIC stops during suspend, wall clock does not
                suspended = (t_end - t_start) - (m_end - m_start) > 2.0
                rec.update(t_start=round(t_start, 4), t_end=round(t_end, 4), wall_s=round(m_end - m_start, 4),
                           suspended=suspended, on_ac=on_ac_power())
                f.write(json.dumps(rec) + "\n")
                f.flush()
                if i % 25 == 0 or i == n:
                    per = (time.time() - t_cfg) / i
                    print(f"  {c['config']:22s} {i:4d}/{n}  {per:5.2f}s/prompt  "
                          f"config ETA {per * (n - i) / 60:5.1f} min", flush=True)
                time.sleep(a.gap)
        meta["t_measure_end"] = time.time()
        (run_dir / f"{c['config']}.meta.{part}.json").write_text(json.dumps(meta, indent=2))
    finally:
        if sampler:
            sampler.stop_evt.set()
        if server_pid and server_pid != proc.pid:
            try:
                os.kill(server_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=20)          # perf exits after its child and flushes its file
        except subprocess.TimeoutExpired:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        log.close()


# ------------------------------------------------------------------ main
def main():
    cfg = load_cfg()
    inf = cfg.get("inference", {})
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="main")
    ap.add_argument("--configs", nargs="*", help="substring filters, e.g. 0.5b-Q4_K_M 1.5b-F16")
    ap.add_argument("--limit", type=int, help="max prompts per config (pilot runs)")
    ap.add_argument("--eval-set", default=str(EVAL))
    ap.add_argument("--threads", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--cpus", help="pin server to CPUs, e.g. 0-3 (optional)")
    ap.add_argument("--port", type=int, default=int(inf.get("port", 8089)))
    ap.add_argument("--seed", type=int, default=int(cfg.get("seed", 42)))
    ap.add_argument("--perf-interval", type=int,
                    default=int(cfg.get("telemetry", {}).get("perf_interval_ms", 100)))
    ap.add_argument("--no-perf", action="store_true", help="run without perf (debugging)")
    ap.add_argument("--gap", type=float, default=0.3, help="idle seconds between prompts (separates telemetry)")
    ap.add_argument("--cooldown", type=float, default=20, help="seconds between configs (thermal)")
    ap.add_argument("--ignore-battery", action="store_true", help="do not pause when running on battery")
    ap.add_argument("--settle", type=float, default=60, help="seconds to wait after AC power returns")
    a = ap.parse_args()

    ev = pd.read_parquet(a.eval_set)
    configs = discover_configs(a.configs)
    if not configs:
        sys.exit("No matching model configs found.")
    server_bin = find_llama_server()
    run_dir = ROOT / "results" / "runs" / a.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"run: {a.run_id} | prompts/config: {a.limit or len(ev)} | configs: {len(configs)} | "
          f"threads: {a.threads} | perf: {not a.no_perf}")
    print("order:", ", ".join(c["config"] for c in configs), "\n")

    stop_flag = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: (print("\nStopping after current prompt..."), stop_flag.set()))
    t0 = time.time()
    for k, c in enumerate(configs, 1):
        if stop_flag.is_set():
            break
        print(f"[{k}/{len(configs)}] {c['config']}  (elapsed {(time.time() - t0) / 3600:.2f} h)", flush=True)
        run_config(c, ev, a, cfg, server_bin, run_dir, stop_flag)
        if k < len(configs) and not stop_flag.is_set():
            time.sleep(a.cooldown)
    print(f"\nDone. Results in {run_dir}  (total {(time.time() - t0) / 3600:.2f} h)")


if __name__ == "__main__":
    main()
