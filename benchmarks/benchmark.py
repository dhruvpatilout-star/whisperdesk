"""
benchmarks/benchmark.py

Task 3: Compare 3 approaches on the SAME 10 audio samples.
  Approach A: faster-whisper tiny.en (int8)
  Approach B: faster-whisper base.en (int8)
  Approach C: faster-whisper small.en (int8)

Expects:
  benchmarks/test_audio/  -> 10 wav/mp3 files, 5-15s each
  benchmarks/ground_truth.json -> {"sample1.wav": "the exact spoken text", ...}

Outputs:
  benchmarks/results.json  (raw per-sample numbers)
  Prints the summary table used in the README.

Install:
  pip install faster-whisper jiwer psutil
"""

import json
import os
import sys
import tracemalloc
from pathlib import Path

import jiwer

sys.path.append(str(Path(__file__).resolve().parent.parent))
from engine.transcriber import transcribe_file  # noqa: E402

AUDIO_DIR = Path(__file__).parent / "test_audio"
GROUND_TRUTH_PATH = Path(__file__).parent / "ground_truth.json"
RESULTS_PATH = Path(__file__).parent / "results.json"

APPROACHES = {
    "A_tiny.en": "tiny.en",
    "B_base.en": "base.en",
    "C_small.en": "small.en",
}


def load_ground_truth() -> dict:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"Missing {GROUND_TRUTH_PATH}. Create a JSON file mapping each "
            f"audio filename to its exact spoken-text transcript."
        )
    return json.loads(GROUND_TRUTH_PATH.read_text())


def run_approach(approach_name: str, model_size: str, ground_truth: dict) -> dict:
    per_sample = []
    for fname, truth in ground_truth.items():
        audio_path = AUDIO_DIR / fname
        if not audio_path.exists():
            print(f"  [skip] {fname} not found in {AUDIO_DIR}")
            continue

        tracemalloc.start()
        result = transcribe_file(str(audio_path), model_size)
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        wer = jiwer.wer(truth, result.text)
        per_sample.append({
            "file": fname,
            "predicted": result.text,
            "ground_truth": truth,
            "rtf": result.rtf,
            "wer": wer,
            "peak_mem_mb": peak_bytes / (1024 * 1024),
        })
        print(f"  {fname}: RTF={result.rtf:.3f} WER={wer:.2%}")

    return {"model_size": model_size, "samples": per_sample}


def summarize(samples: list) -> dict:
    if not samples:
        return {"p95_latency_rtf": None, "avg_wer_pct": None, "peak_ram_mb": None}
    rtfs = sorted(s["rtf"] for s in samples)
    p95_idx = max(0, int(len(rtfs) * 0.95) - 1)
    return {
        "p95_latency_rtf": round(rtfs[p95_idx], 3),
        "avg_wer_pct": round(100 * sum(s["wer"] for s in samples) / len(samples), 2),
        "peak_ram_mb": round(max(s["peak_mem_mb"] for s in samples), 1),
    }


def main():
    ground_truth = load_ground_truth()
    all_results = {}

    for approach_name, model_size in APPROACHES.items():
        print(f"\n=== Approach {approach_name} ({model_size}) ===")
        run_data = run_approach(approach_name, model_size, ground_truth)
        run_data["summary"] = summarize(run_data["samples"])
        all_results[approach_name] = run_data

    RESULTS_PATH.write_text(json.dumps(all_results, indent=2))

    print("\n\n| Metric | A (tiny.en) | B (base.en) | C (small.en) |")
    print("|---|---|---|---|")
    row = lambda key, fmt: " | ".join(fmt(all_results[a]["summary"][key]) for a in APPROACHES)
    print(f"| P95 Latency (RTF) | {row('p95_latency_rtf', lambda v: f'{v}')} |")
    print(f"| Avg WER (%) | {row('avg_wer_pct', lambda v: f'{v}')} |")
    print(f"| Peak RAM (MB) | {row('peak_ram_mb', lambda v: f'{v}')} |")
    print(f"\nFull per-sample data written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
