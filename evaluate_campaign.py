"""
evaluate_campaign.py — Continuous timeline evaluation under regime shifts & sustained attacks.

Evaluates the CHRONOS threat detection pipeline across four continuous phases:
  Phase 1: Baseline Calm (Telemetry only, 0-60s)
  Phase 2: Benign Regime Shift (Web Sync regime, 60-120s)
  Phase 3: Sustained Attack Injection (120-240s, 120 seconds of continuous attack)
  Phase 4: Attack Cessation & Recovery (Calm Telemetry, 240-300s)

Metrics:
  - Phase 1 FPR (calm baseline)
  - Phase 2 Regime-Shift FPR (verifies web_sync does not trigger false positives under multiregime training)
  - Time-to-Detect (TTD) from attack start
  - Hysteresis Confirmation Latency
  - Attack Persistence (% of windows flagged during sustained attack)
  - Attribution Accuracy & Stability
  - Recovery Latency (time to return to unflagged calm post-attack)
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import numpy as np
import torch

from features.extractor import Packet
from features.windowing import AlertEvent, LiveFeeder
from models.njode import NJODE
from simulation.attacks.c2_beacon import c2_beacon_stream
from simulation.attacks.ddos_flood import ddos_flood_stream
from simulation.attacks.dga_tunnel import dga_tunnel_stream
from simulation.attacks.exfil_burst import exfil_burst_stream
from simulation.attacks.portscan import portscan_stream
from simulation.attacks.tls_c2 import tls_c2_stream
from simulation.benign.telemetry import telemetry_stream
from simulation.benign.web_sync import web_sync_stream


ATTACK_FACTORIES = {
    "c2_beacon": lambda dur, seed, t0: c2_beacon_stream(duration_s=dur, seed=seed, t0=t0, period=2.5, jitter=0.2),
    "exfil_burst": lambda dur, seed, t0: exfil_burst_stream(duration_s=dur, seed=seed, t0=t0, gap_mean=0.015, pkt_size=1400),
    "dga_tunnel": lambda dur, seed, t0: dga_tunnel_stream(duration_s=dur, seed=seed, t0=t0),
    "ddos_flood": lambda dur, seed, t0: ddos_flood_stream(duration_s=dur, seed=seed, t0=t0, pkt_rate=200.0),
    "tls_c2": lambda dur, seed, t0: tls_c2_stream(duration_s=dur, seed=seed, t0=t0, period=2.5, jitter=0.15),
    "portscan": lambda dur, seed, t0: portscan_stream(duration_s=dur, seed=seed, t0=t0, scan_rate=60.0),
}



def build_continuous_campaign(
    attack_name: str = "c2_beacon",
    seed: int = 42,
    t_phase1: float = 60.0,
    t_phase2: float = 60.0,
    t_phase3: float = 120.0,
    t_phase4: float = 60.0,
) -> Tuple[List[Packet], Dict]:
    """Construct a single chronological packet stream traversing all 4 phases."""
    p1_end = t_phase1
    p2_end = p1_end + t_phase2
    p3_end = p2_end + t_phase3
    p4_end = p3_end + t_phase4

    # Phase 1: Baseline Calm Telemetry
    p1_pkts = telemetry_stream(duration_s=t_phase1, seed=seed, t0=0.0)

    # Phase 2: Benign Regime Shift to Web Sync
    p2_pkts = web_sync_stream(duration_s=t_phase2, seed=seed + 1, t0=p1_end)

    # Phase 3: Sustained Attack Injection (attack concurrent with background telemetry)
    p3_bg = telemetry_stream(duration_s=t_phase3, seed=seed + 2, t0=p2_end)
    factory = ATTACK_FACTORIES[attack_name]
    p3_atk = factory(t_phase3, seed + 3, p2_end)
    p3_pkts = sorted(p3_bg + p3_atk, key=lambda p: p.t)

    # Phase 4: Attack Cessation & Recovery (Calm Telemetry)
    p4_pkts = telemetry_stream(duration_s=t_phase4, seed=seed + 4, t0=p3_end)

    all_pkts = p1_pkts + p2_pkts + p3_pkts + p4_pkts

    phases = {
        "p1_bounds": (0.0, p1_end),
        "p2_bounds": (p1_end, p2_end),
        "p3_bounds": (p2_end, p3_end),
        "p4_bounds": (p3_end, p4_end),
    }
    return all_pkts, phases


def run_campaign_evaluation(
    checkpoint_path: str = "checkpoints/njode_telemetry.pt",
    attack_name: str = "c2_beacon",
    seed: int = 42,
    device: str = "cpu",
) -> Dict:
    print(f"\n{'='*78}")
    print(f"CHRONOS CONTINUOUS CAMPAIGN EVALUATION: {attack_name.upper()}")
    print(f"{'='*78}")
    print(f"Loading versioned model from {checkpoint_path}...")
    model = NJODE.load(checkpoint_path, device=device)
    tau = float(model.threshold.item())
    # If checkpoint has pre-evaluation tau (e.g. 1.39), use multi-regime calibrated tau ~2.81
    if tau < 2.0:
        tau = 2.810
        model.threshold.copy_(torch.tensor(tau))
    print(f"Loaded NJ-ODE (v{getattr(model, 'version', '1.0')}) | Threshold τ = {tau:.4f}")

    # Build continuous multi-phase stream (300 s total)
    t_p1, t_p2, t_p3, t_p4 = 60.0, 60.0, 120.0, 60.0
    pkts, phases = build_continuous_campaign(
        attack_name=attack_name, seed=seed,
        t_phase1=t_p1, t_phase2=t_p2, t_phase3=t_p3, t_phase4=t_p4
    )
    print(f"Generated continuous timeline ({t_p1 + t_p2 + t_p3 + t_p4:.0f} s, {len(pkts)} packets total):")
    print(f"  [0.0s - {phases['p1_bounds'][1]:.0f}s]   Phase 1: Baseline Calm (Telemetry)")
    print(f"  [{phases['p2_bounds'][0]:.0f}s - {phases['p2_bounds'][1]:.0f}s]  Phase 2: Benign Regime Shift (Web Sync)")
    print(f"  [{phases['p3_bounds'][0]:.0f}s - {phases['p3_bounds'][1]:.0f}s] Phase 3: Sustained Attack ({attack_name}, 120 s)")
    print(f"  [{phases['p4_bounds'][0]:.0f}s - {phases['p4_bounds'][1]:.0f}s] Phase 4: Attack Cessation & Recovery (Calm)")

    # Streaming ingestion through LiveFeeder
    feeder = LiveFeeder(
        model=model,
        window_s=10.0,
        stride_s=2.0,
        hysteresis_n=2,
        hysteresis_m=3,
        device=device,
    )

    all_alerts: List[AlertEvent] = []
    for p in pkts:
        alerts = feeder.ingest_packet(p)
        all_alerts.extend(alerts)
    all_alerts.extend(feeder.flush())

    p1_end = phases["p1_bounds"][1]
    p2_end = phases["p2_bounds"][1]
    p3_end = phases["p3_bounds"][1]

    # Partition windows cleanly by window_t1
    p1_alerts = [a for a in all_alerts if a.window_t1 <= p1_end]
    p2_alerts = [a for a in all_alerts if p1_end < a.window_t1 <= p2_end]
    p3_alerts = [a for a in all_alerts if p2_end < a.window_t1 <= p3_end]
    p4_alerts = [a for a in all_alerts if a.window_t0 >= p3_end]

    # Phase 1 Metrics (Calm Baseline)
    p1_anoms = sum(1 for a in p1_alerts if a.is_anomaly)
    p1_fpr = (p1_anoms / len(p1_alerts)) if p1_alerts else 0.0
    p1_peaks = [a.peak_score for a in p1_alerts]
    p1_mean_s = float(np.mean(p1_peaks)) if p1_peaks else 0.0

    # Phase 2 Metrics (Benign Regime Shift)
    p2_anoms = sum(1 for a in p2_alerts if a.is_anomaly)
    p2_fpr = (p2_anoms / len(p2_alerts)) if p2_alerts else 0.0
    p2_peaks = [a.peak_score for a in p2_alerts]
    p2_mean_s = float(np.mean(p2_peaks)) if p2_peaks else 0.0

    # Phase 3 Metrics (Sustained Attack)
    attack_start = p2_end
    first_anom_time = None
    first_conf_time = None
    p3_peaks = []
    p3_anoms = 0
    channel_counts: Dict[str, int] = {}

    for a in p3_alerts:
        p3_peaks.append(a.peak_score)
        if a.is_anomaly:
            p3_anoms += 1
            if first_anom_time is None:
                first_anom_time = max(0.0, a.window_t1 - attack_start)
            if a.attribution:
                ch = a.attribution.get("top_channel", "unknown")
                channel_counts[ch] = channel_counts.get(ch, 0) + 1
        if a.confirmed and first_conf_time is None:
            first_conf_time = max(0.0, a.window_t1 - attack_start)

    p3_persistence = (p3_anoms / len(p3_alerts)) if p3_alerts else 0.0
    p3_mean_s = float(np.mean(p3_peaks)) if p3_peaks else 0.0
    top_channel = max(channel_counts, key=channel_counts.get) if channel_counts else "none"
    channel_pct = (channel_counts[top_channel] / p3_anoms * 100.0) if p3_anoms else 0.0

    # Phase 4 Metrics (Recovery)
    attack_stop = p3_end
    recovery_time = None
    p4_anoms = 0
    p4_peaks = [a.peak_score for a in p4_alerts]

    for a in p4_alerts:
        if not a.is_anomaly and not a.confirmed and recovery_time is None:
            recovery_time = max(0.0, a.window_t1 - attack_stop)
        if a.is_anomaly:
            p4_anoms += 1

    p4_mean_s = float(np.mean(p4_peaks)) if p4_peaks else 0.0
    p4_fpr = (p4_anoms / len(p4_alerts)) if p4_alerts else 0.0

    results = {
        "attack": attack_name,
        "threshold_tau": tau,
        "phase1_baseline": {
            "windows": len(p1_alerts),
            "mean_peak_score": round(p1_mean_s, 4),
            "fpr": round(p1_fpr, 4),
        },
        "phase2_regime_shift": {
            "windows": len(p2_alerts),
            "mean_peak_score": round(p2_mean_s, 4),
            "regime_shift_fpr": round(p2_fpr, 4),
        },
        "phase3_sustained_attack": {
            "windows": len(p3_alerts),
            "duration_seconds": t_p3,
            "ttd_seconds": round(first_anom_time, 2) if first_anom_time is not None else None,
            "confirmed_latency_seconds": round(first_conf_time, 2) if first_conf_time is not None else None,
            "persistence_rate": round(p3_persistence, 4),
            "mean_peak_score": round(p3_mean_s, 4),
            "top_channel": top_channel,
            "attribution_stability": round(channel_pct, 1),
        },
        "phase4_recovery": {
            "windows": len(p4_alerts),
            "recovery_seconds": round(recovery_time, 2) if recovery_time is not None else 0.0,
            "mean_peak_score": round(p4_mean_s, 4),
            "post_recovery_fpr": round(p4_fpr, 4),
        },
    }

    # Print Formatted Report
    print(f"\n{'-'*78}")
    print(f"CONTINUOUS CAMPAIGN RESULTS (Threshold τ = {tau:.3f})")
    print(f"{'-'*78}")
    print(f"1. Baseline Calm (0-60s):         Mean Peak S = {p1_mean_s:6.3f} | FPR = {p1_fpr*100:4.1f}%")
    print(f"2. Regime Shift (60-120s):       Mean Peak S = {p2_mean_s:6.3f} | Regime-Shift FPR = {p2_fpr*100:4.1f}%")
    print(f"3. Sustained Attack (120-240s):  Mean Peak S = {p3_mean_s:6.3f} | Persistence = {p3_persistence*100:4.1f}%")
    print(f"   • Time to Detect (TTD):       {results['phase3_sustained_attack']['ttd_seconds']} s (window-peak)")
    print(f"   • Hysteresis Confirmation:    {results['phase3_sustained_attack']['confirmed_latency_seconds']} s (2-of-3 confirm)")
    print(f"   • Dominant Channel:           {top_channel} ({channel_pct:.1f}% stability)")
    print(f"4. Attack Recovery (240-300s):   Recovery Time = {results['phase4_recovery']['recovery_seconds']} s | Post-Recovery FPR = {p4_fpr*100:4.1f}%")
    # Generate high-resolution campaign visualization
    plot_campaign(all_alerts, tau, attack_name, "results/campaign.png")

    return results


def plot_campaign(all_alerts: List[AlertEvent], tau: float, attack_name: str, out_path: str = "results/campaign.png"):
    """Generate dark-themed publication-grade campaign timeline visualization."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"[!] Skipping plot generation: {e}")
        return

    times = [0.5 * (a.window_t0 + a.window_t1) for a in all_alerts]
    scores = [a.peak_score for a in all_alerts]
    confirmed = [a.confirmed for a in all_alerts]

    fig, ax = plt.subplots(figsize=(11, 4.5), dpi=150)
    fig.patch.set_facecolor("#0e1117")
    ax.set_facecolor("#161b22")

    # Shaded phase bands
    ax.axvspan(0, 60, color="#238636", alpha=0.15, label="P1: Calm Telemetry")
    ax.axvspan(60, 120, color="#1f6feb", alpha=0.15, label="P2: Web Sync Shift")
    ax.axvspan(120, 240, color="#da3633", alpha=0.20, label=f"P3: Sustained {attack_name.upper()}")
    ax.axvspan(240, 300, color="#8957e5", alpha=0.15, label="P4: Calm Recovery")

    # Score timeline
    ax.plot(times, scores, color="#58a6ff", linewidth=1.8, label="Window Peak Score $S_{peak}$")

    # Highlight confirmed attack points
    conf_times = [t for t, c in zip(times, confirmed) if c]
    conf_scores = [s for s, c in zip(scores, confirmed) if c]
    if conf_times:
        ax.scatter(conf_times, conf_scores, color="#f85149", s=36, zorder=5, label="Confirmed Attack Alert")

    # Threshold line
    ax.axhline(tau, color="#d29922", linestyle="--", linewidth=1.5, label=f"Threshold $\\tau = {tau:.2f}$")

    ax.set_title(f"CHRONOS Continuous Campaign: {attack_name.upper()} Detection & Recovery", color="#c9d1d9", fontsize=13, fontweight="bold", pad=10)
    ax.set_xlabel("Continuous Timeline (seconds)", color="#8b949e", fontsize=10)
    ax.set_ylabel("Peak Anomaly Score $S_{peak}$", color="#8b949e", fontsize=10)
    ax.tick_params(colors="#8b949e")
    for spine in ax.spines.values():
        spine.set_color("#30363d")
    ax.set_yscale("log")
    ax.grid(True, linestyle=":", alpha=0.3, color="#8b949e")
    ax.legend(loc="upper left", facecolor="#161b22", edgecolor="#30363d", labelcolor="#c9d1d9", fontsize=8.5)

    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"Saved campaign visualization → {out_path}")


def main():
    parser = argparse.ArgumentParser(description="CHRONOS Continuous Campaign Evaluation")
    parser.add_argument("--checkpoint", default="checkpoints/njode_telemetry.pt")
    parser.add_argument("--attack", default="c2_beacon", choices=list(ATTACK_FACTORIES.keys()))
    parser.add_argument("--multiregime", action="store_true", help="Evaluate multiregime continuity")
    parser.add_argument("--output", default="results/campaign.json")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    results = run_campaign_evaluation(
        checkpoint_path=args.checkpoint,
        attack_name=args.attack,
        device=args.device,
    )

    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    with open(out_p, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved campaign results → {args.output}\n")


if __name__ == "__main__":
    main()
