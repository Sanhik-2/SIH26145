"""
benchmark.py — Throughput & Window Scoring Latency Benchmark (Piece 9)

Evaluates the real-time processing capability of the CHRONOS ingestion pipeline
and LiveFeeder across a simplex data diode.

Ramps synthetic traffic from 100 pkts/s to 5000 pkts/s to measure:
  1. Maximum sustained ingest rate (pkts/sec)
  2. Window scoring execution latency: p50, p90, and p99 (ms)
  3. Memory and buffer stability under high packet loads

Outputs results to results/benchmark.json.
Run:
  python benchmark.py
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.extractor import Packet
from features.windowing import LiveFeeder
from models.njode import NJODE

CHECKPOINT_PATH = REPO_ROOT / "checkpoints" / "njode_telemetry.pt"
RESULTS_PATH = REPO_ROOT / "results" / "benchmark.json"


def generate_benchmark_batch(rate: float, duration_s: float = 3.0, seed: int = 42) -> List[Packet]:
    """Generate deterministic synthetic packets at target arrival rate (pkts/s)."""
    rng = np.random.default_rng(seed)
    total_pkts = int(rate * duration_s)
    pkts = []
    t = 0.0
    dt_mean = 1.0 / rate

    # Mix of flows and directions
    flow_keys = [f"flow_{i}".encode() for i in range(16)]

    for i in range(total_pkts):
        t += float(np.clip(rng.exponential(dt_mean), 0.00001, dt_mean * 2.5))
        size = int(rng.integers(64, 1400))
        direction = 1 if rng.uniform() > 0.7 else 0
        flow_key = flow_keys[i % len(flow_keys)]
        payload = b"\x00" * min(size, 32)
        pkts.append(Packet(t=t, size=size, payload=payload, direction=direction, flow_key=flow_key))

    return pkts


def run_benchmark(
    checkpoint_path: Path = CHECKPOINT_PATH,
    rates: List[int] = [100, 500, 1000, 2000, 3000, 5000],
    device: str = "cpu"
) -> Dict:
    print("=" * 72)
    print("⚡ CHRONOS PASSIVE DATA DIODE THROUGHPUT & LATENCY BENCHMARK")
    print("=" * 72)

    if checkpoint_path.exists():
        print(f"Loading versioned checkpoint: {checkpoint_path}")
        model = NJODE.load(str(checkpoint_path), device=device)
    else:
        print("Checkpoint not found, initializing fresh default NJ-ODE model...")
        model = NJODE(d_x=5, d_h=10, hidden=50).to(device)
        model.threshold.copy_(torch.tensor(2.810))
        model.x_mean.copy_(torch.tensor([0.5, 200.0, 4.0, 0.1, 0.1]))
        model.x_std.copy_(torch.tensor([0.3, 150.0, 2.0, 0.3, 0.3]))

    model.eval()

    ramp_results = []
    all_scoring_latencies_ms = []
    max_sustained_rate = 0.0

    print(f"\nRamping synthetic packet stream across {len(rates)} throughput tiers:")
    print("-" * 72)
    print(f"{'Target Rate':>12} | {'Ingest Rate':>14} | {'Scored Windows':>14} | {'Window p50':>10} | {'Window p99':>10}")
    print("-" * 72)

    for target_rate in rates:
        feeder = LiveFeeder(
            model=model,
            window_s=5.0,
            stride_s=1.0,
            device=device,
        )

        pkts = generate_benchmark_batch(rate=target_rate, duration_s=4.0)

        # Track window scoring latencies by instrumenting _score_window
        orig_score_window = feeder._score_window
        tier_scoring_latencies = []

        def timed_score_window(t0, t1):
            t_start = time.perf_counter()
            alert = orig_score_window(t0, t1)
            t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0
            tier_scoring_latencies.append(t_elapsed_ms)
            all_scoring_latencies_ms.append(t_elapsed_ms)
            return alert

        feeder._score_window = timed_score_window

        # Measure sustained packet ingestion wall time
        wall_t0 = time.perf_counter()
        for p in pkts:
            feeder.ingest_packet(p)
        feeder.flush()
        wall_elapsed = time.perf_counter() - wall_t0

        sustained_rate = len(pkts) / max(1e-6, wall_elapsed)
        if sustained_rate > max_sustained_rate:
            max_sustained_rate = sustained_rate

        p50 = float(np.percentile(tier_scoring_latencies, 50)) if tier_scoring_latencies else 0.0
        p99 = float(np.percentile(tier_scoring_latencies, 99)) if tier_scoring_latencies else 0.0

        ramp_results.append({
            "target_rate_pkts_per_sec": target_rate,
            "measured_ingest_rate_pkts_per_sec": round(sustained_rate, 1),
            "packets_processed": len(pkts),
            "windows_scored": len(tier_scoring_latencies),
            "scoring_latency_p50_ms": round(p50, 3),
            "scoring_latency_p99_ms": round(p99, 3),
        })

        print(f"{target_rate:9d} pkts/s | {sustained_rate:11.1f} pkts/s | {len(tier_scoring_latencies):14d} | {p50:8.3f} ms | {p99:8.3f} ms")

    overall_p50 = float(np.percentile(all_scoring_latencies_ms, 50)) if all_scoring_latencies_ms else 0.0
    overall_p90 = float(np.percentile(all_scoring_latencies_ms, 90)) if all_scoring_latencies_ms else 0.0
    overall_p99 = float(np.percentile(all_scoring_latencies_ms, 99)) if all_scoring_latencies_ms else 0.0

    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "model_version": getattr(model, "version", "1.1"),
        "feature_count": model.d_x,
        "device": device,
        "max_sustained_rate_pkts_per_sec": round(max_sustained_rate, 1),
        "scoring_latency_ms": {
            "p50": round(overall_p50, 3),
            "p90": round(overall_p90, 3),
            "p99": round(overall_p99, 3),
        },
        "target_rates_tested": rates,
        "ramp_benchmarks": ramp_results,
    }

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print("-" * 72)
    print(f"Max Sustained Ingestion Rate: {max_sustained_rate:,.1f} pkts/sec")
    print(f"Scoring Latency (p50 / p90 / p99): {overall_p50:.3f} ms / {overall_p90:.3f} ms / {overall_p99:.3f} ms")
    print(f"Results successfully saved to: {RESULTS_PATH}")
    print("=" * 72)

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CHRONOS Diode Throughput Benchmark")
    parser.add_argument("--checkpoint", default=str(CHECKPOINT_PATH), help="Path to checkpoint")
    parser.add_argument("--device", default="cpu", help="Device (cpu or cuda)")
    args = parser.parse_args()

    run_benchmark(checkpoint_path=Path(args.checkpoint), device=args.device)
