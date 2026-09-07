"""
evaluate.py — backend evaluation harness (Piece 2)

Train NJ-ODE on multi-regime benign baseline (telemetry + web_sync) →
calibrate τ on held-out benign → measure per-attack detection & channel attribution.
Deterministic seeds, one JSON result file for the PPT / judges.

HONEST CAVEAT (keep this in your back pocket for Q&A): these attacks are the
*conspicuous* regime on a synthetic benign baseline — near-perfect separation
is EXPECTED here. This run validates plumbing + gives a regression harness.
Generalization claims come from CIC-IDS2017 PCAP validation later.
"""
import json
from pathlib import Path

import numpy as np
import torch

from features.extractor import FeatureStream, featurize
from features.windowing import LiveFeeder, Windower
from models.njode import NJODE
from simulation.attacks.c2_beacon import c2_beacon_stream
from simulation.attacks.dga_tunnel import dga_tunnel_stream
from simulation.attacks.exfil_burst import exfil_burst_stream
from simulation.benign.telemetry import telemetry_stream
from simulation.benign.web_sync import web_sync_stream

def _peak_scores(s):
    """NaN-aware per-window peak score."""
    return torch.nan_to_num(s, nan=float("-inf")).amax(dim=1)

WINDOW_S = 10.0
TRAIN_S = 480.0
N_CAL, N_FPR, N_ATTACK = 16, 24, 40


def trim(stream, t_end):
    keep = stream.t < t_end
    return FeatureStream(stream.t[keep], stream.F[keep])


def tensorset(win, *streams):
    vals, masks = [], []
    t_grid = None
    for s in streams:
        v, m, t = win.windows(s)
        if len(v) > 0:
            vals.append(v)
            masks.append(m)
            t_grid = t
    if not vals:
        raise ValueError("No windows generated from streams")
    v_cat = torch.cat(vals, dim=0)
    m_cat = torch.cat(masks, dim=0)
    return v_cat, m_cat, t_grid.expand(v_cat.shape[0], -1)


def mixed_window_stream(win, benign_seed, attack_fn, attack_seed):
    """Benign telemetry + attack packets sharing one 10 s span — what the tap would see."""
    benign_tel = telemetry_stream(duration_s=WINDOW_S, seed=benign_seed)
    attack = attack_fn(duration_s=WINDOW_S, seed=attack_seed)
    return win, featurize(sorted(benign_tel + attack, key=lambda p: p.t))


def main():
    torch.manual_seed(0)

    print("[1/5] multi-regime benign corpus (telemetry + web_sync)...")
    train_tel = featurize(telemetry_stream(duration_s=TRAIN_S, seed=0))
    train_sync = featurize(web_sync_stream(duration_s=TRAIN_S, seed=1))

    cal_tel = trim(featurize(telemetry_stream(duration_s=N_CAL * WINDOW_S, seed=7)), N_CAL * WINDOW_S)
    cal_sync = trim(featurize(web_sync_stream(duration_s=N_CAL * WINDOW_S, seed=8)), N_CAL * WINDOW_S)

    fpr_tel = trim(featurize(telemetry_stream(duration_s=N_FPR * WINDOW_S, seed=13)), N_FPR * WINDOW_S)
    fpr_sync = trim(featurize(web_sync_stream(duration_s=N_FPR * WINDOW_S, seed=14)), N_FPR * WINDOW_S)

    model = NJODE(d_x=4, d_h=10)
    win = Windower(model, window_s=WINDOW_S)
    win.fit_standardizer(train_tel, train_sync)

    print("[2/5] training + calibration on multiregime baseline...")
    v, m, t = tensorset(win, train_tel, train_sync)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(v, m, t), batch_size=32, shuffle=True)
    model.fit(loader, epochs=60, log_every=20)
    model.calibrate([tensorset(win, cal_tel, cal_sync)])

    print("[3/5] benign test windows (FPR)...")
    v_f, m_f, t_f = tensorset(win, fpr_tel, fpr_sync)
    s_b, f_b = model.compute_anomaly_scores(v_f, m_f, t_f)
    fpr = f_b.any(dim=1).float().mean().item()
    peak_benign = _peak_scores(s_b)

    attacks = {
        "c2_beacon": (c2_beacon_stream, ("tunnel/encrypted-c2", "beacon/recon")),
        "exfil_burst": (exfil_burst_stream, ("exfil-flood",)),
        "dga_tunnel": (dga_tunnel_stream, ("tunnel/encrypted-c2",)),
    }

    print("[4/5] attack windows & channel attribution...")
    feeder = LiveFeeder(model, window_s=WINDOW_S, stride_s=2.0)
    rows = {}
    for name, (fn, exp_threat) in attacks.items():
        exp_tuple = exp_threat if isinstance(exp_threat, tuple) else (exp_threat,)
        peaks, det, n_flag, n_obs, correct_attr = [], 0, 0, 0, 0
        for i in range(N_ATTACK):
            _, stream = mixed_window_stream(win, 1000 + i, fn, 2000 + i)
            v_a, m_a, t_a = tensorset(win, stream)
            s, f = model.compute_anomaly_scores(v_a, m_a, t_a)
            p_score = _peak_scores(s)[0].item()
            peaks.append(p_score)
            is_det = bool(f.any())
            det += int(is_det)
            n_flag += int(f.sum())
            n_obs += int((~torch.isnan(s)).sum())

            # Test LiveFeeder channel attribution on this attack stream
            alerts = list(feeder.feed_stream(stream))
            for alert in alerts:
                if alert.is_anomaly and alert.attribution:
                    if alert.attribution["threat_type"] in exp_tuple:
                        correct_attr += 1
                        break

        rows[name] = {
            "detection_rate": det / N_ATTACK,
            "flagged_obs_rate": n_flag / n_obs,
            "mean_peak_score": float(np.mean(peaks)),
            "attribution_accuracy": correct_attr / N_ATTACK,
            "expected_attribution": "/".join(exp_tuple),
        }

    peak_benign_valid = peak_benign[torch.isfinite(peak_benign)]
    mean_benign = float(peak_benign_valid.mean().item()) if len(peak_benign_valid) > 0 else 0.0
    p99_benign = float(torch.quantile(peak_benign_valid, 0.99).item()) if len(peak_benign_valid) > 0 else 0.0

    print("\n[5/5] RESULTS  (τ = %.3f | benign FPR = %.1f%% | benign peak S: "
          "mean %.2f, p99 %.2f)" % (model.threshold.item(), 100 * fpr,
                                    mean_benign, p99_benign))
    print("-" * 78)
    print(f"{'attack':<14}{'detected':>10}{'flag-obs':>10}{'mean peak S':>14}{'attribution':>16}{'threat type':>14}")
    print("-" * 78)
    for name, r in rows.items():
        print(f"{name:<14}{r['detection_rate']*100:>9.0f}%"
              f"{r['flagged_obs_rate']*100:>9.1f}%{r['mean_peak_score']:>14.1f}"
              f"{r['attribution_accuracy']*100:>15.0f}%{r['expected_attribution']:>14}")
    print("-" * 78)

    Path("results").mkdir(exist_ok=True)
    with open("results/eval.json", "w") as fh:
        json.dump({"threshold": model.threshold.item(), "benign_fpr": fpr,
                   "benign_peak_mean": mean_benign,
                   "benign_peak_p99": p99_benign,
                   **rows}, fh, indent=2)
    print("saved → results/eval.json")


if __name__ == "__main__":
    main()

