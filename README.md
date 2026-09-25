# Capable Enough to Be Hijacked

Code, benchmark and results for the paper **"Capable Enough to Be Hijacked: Quantization, Caution, and Indirect Prompt Injection in Small Edge LLMs"** by Chuka Josemaria Uzo (Independent Researcher, [ORCID 0009-0009-9411-2858](https://orcid.org/0009-0009-9411-2858)).

**Paper:** [https://doi.org/10.5281/zenodo.22962299](https://doi.org/10.5281/zenodo.22962299)

## What the study does

Two small instruction-tuned models (Qwen2.5-0.5B-Instruct and Qwen2.5-1.5B-Instruct) were tested at eight llama.cpp GGUF precision levels (F16, Q8_0, Q6_K, Q5_K_M, Q4_K_M, Q4_0, Q3_K_M, Q2_K), on CPU only, with 1,175 identical prompts per configuration (18,800 responses in total):

- harmful requests (JailbreakBench, HarmBench, AdvBench)
- benign requests and over-refusal probes (JailbreakBench-benign, Alpaca, XSTest)
- a new benchmark of 375 business documents (CVs, emails, supplier invoices, product reviews, IT tickets), 300 with a hidden instruction and 75 clean twins

## Main findings

1. **The more capable model was easier to hijack**: 30.0% attack success vs 21.8% (pooled), and 72.2% vs 11.5% for "reply only ACCESS GRANTED" attacks.
2. **Compression shifted caution, not safety**: refusal of harmful requests was preserved, but refusal of harmless requests rose; at Q2_K the 1.5B model refused 64.7% of benign requests (30.7% at F16).
3. **Format mattered more than bit-width**: Q4_K_M was statistically indistinguishable from F16 on every tested metric; Q4_0 was not.

Automatic scoring was validated against human labels (refusal kappa = 0.86, injection kappa = 0.79).

## Repository contents

| Path | Contents |
| --- | --- |
| `scripts/` | Full pipeline: dataset download, benchmark generation, experiment runner, scoring, figures, validation tool |
| `configs/experiment.yaml` | Inference and telemetry settings |
| `data/synthetic/` | The indirect prompt injection benchmark (375 documents) and readable examples |
| `data/eval_set_manifest.csv` | IDs and metadata of all 1,175 evaluation prompts (no prompt text) |
| `results/tables/`, `results/figures/`, `results/summary.md` | All results tables and figures |
| `results/scored_labels.csv` | Per-response automatic labels for all 18,800 responses (no model outputs) |
| `results/validation/` | Human validation labels |

## Not included, and why

- **Raw model outputs**: some are responses to harmful requests; only labels are released.
- **Third-party datasets**: not redistributed; `scripts/download_datasets.py` fetches them from their original sources, and the seeded sampling reproduces the same evaluation set.
- **Model files**: available from the Qwen2.5 releases; quantize them with llama.cpp.
- **Kernel telemetry (perf)**: reserved for a follow-up study.

## Reproducing the experiment

Tested on Ubuntu 24.04 with Python 3.12 on a 4-core laptop CPU; the full run takes about 20 hours.

1. Build [llama.cpp](https://github.com/ggml-org/llama.cpp) (`llama-server`, `llama-quantize`).
2. Obtain F16 GGUF files of both models, quantize them to the seven formats, and place them as `models/qwen2.5-0.5b/qwen2.5-0.5b-<FORMAT>.gguf` and `models/qwen2.5-1.5b/qwen2.5-1.5b-<FORMAT>.gguf`.
3. Set up the environment:
```bash
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   export LLAMA_SERVER=/path/to/llama.cpp/build/bin/llama-server
```
4. Build the data and run:
```bash
   python scripts/download_datasets.py
   python scripts/make_injection_docs.py
   python scripts/build_eval_set.py
   python scripts/run_experiment.py --run-id main      # needs Linux perf; add --no-perf to skip telemetry
   python scripts/score_results.py
   python scripts/make_figures.py
```

## Citation

Please cite the paper: Uzo, C. J. (2026). *Capable Enough to Be Hijacked: Quantization, Caution, and Indirect Prompt Injection in Small Edge LLMs*. Zenodo. https://doi.org/10.5281/zenodo.22962299

## Licence

Code: MIT (`LICENSE`). Benchmark, labels, tables and figures: CC BY 4.0 (`LICENSE-DATA`).

## Ethics and AI assistance

All synthetic documents are fictitious and injected links use reserved example domains. An AI assistant (Claude, Anthropic) helped write the code and draft the paper; the author directed the study, ran all experiments, performed all human annotation and verified the results.
