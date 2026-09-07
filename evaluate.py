"""
evaluate.py — backend evaluation harness (Piece 2)

Train NJ-ODE on benign telemetry → calibrate τ on held-out benign → measure
per-attack detection. Deterministic seeds, one JSON result file for the PPT.

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
from features.windowing import Windower
from models.njode import NJODE
from simulation.attacks.c2_beacon import c2_beacon_stream
from simulation.attacks.dga_tunnel import dga_tunnel_stream
from simulation.attacks.exfil_burst import exfil_burst_stream
from simulation.benign.telemetry import telemetry_stream

def _peak_scores(s):
    """NaN-aware per-window peak score (torch.nanmax was removed in new torch)."""
    return torch.nan_to_num(s, nan=float("-inf")).amax(dim=1)

WINDOW_S = 10.0
TRAIN_S = 480.0
N_CAL, N_FPR, N_ATTACK = 16, 24, 40


def trim(stream, t_end):
    keep = stream.t < t_end
    return FeatureStream(stream.t[keep], stream.F[keep])


def tensorset(win, stream):
    v, m, t = win.windows(stream)
    return v, m, t.expand(v.shape[0], -1)


def mixed_window_stream(win, benign_seed, attack_fn, attack_seed):
    """Benign + attack packets sharing one 10 s span — what the tap would see."""
    benign = telemetry_stream(duration_s=WINDOW_S, seed=benign_seed)
    attack = attack_fn(duration_s=WINDOW_S, seed=attack_seed)
    return win, featurize(sorted(benign + attack, key=lambda p: p.t))


def main():
    torch.manual_seed(0)

    print("[1/5] benign corpus...")
    train_stream = featurize(telemetry_stream(duration_s=TRAIN_S, seed=0))
    cal_stream = trim(featurize(telemetry_stream(duration_s=N_CAL * WINDOW_S, seed=7)),
                      N_CAL * WINDOW_S)
    fpr_stream = trim(featurize(telemetry_stream(duration_s=N_FPR * WINDOW_S, seed=13)),
                      N_FPR * WINDOW_S)

    model = NJODE(d_x=4, d_h=10)
    win = Windower(model, window_s=WINDOW_S)
    win.fit_standardizer(train_stream)

    print("[2/5] training + calibration...")
    v, m, t = tensorset(win, train_stream)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(v, m, t), batch_size=32, shuffle=True)
    model.fit(loader, epochs=60, log_every=20)
    model.calibrate([( *tensorset(win, cal_stream), )])

    print("[3/5] benign test windows (FPR)...")
    v_f, m_f, t_f = tensorset(win, fpr_stream)
    s_b, f_b = model.compute_anomaly_scores(v_f, m_f, t_f)
    fpr = f_b.any(dim=1).float().mean().item()
    peak_benign = _peak_scores(s_b)

    attacks = {"c2_beacon": c2_beacon_stream,
               "exfil_burst": exfil_burst_stream,
               "dga_tunnel": dga_tunnel_stream}

    print("[4/5] attack windows...")
    rows = {}
    for name, fn in attacks.items():
        peaks, det, n_flag, n_obs = [], 0, 0, 0
        for i in range(N_ATTACK):
            _, stream = mixed_window_stream(win, 1000 + i, fn, 2000 + i)
            v_a, m_a, t_a = tensorset(win, stream)
            s, f = model.compute_anomaly_scores(v_a, m_a, t_a)
            peaks.append(_peak_scores(s)[0].item())
            det += int(bool(f.any()))
            n_flag += int(f.sum())
            n_obs += int((~torch.isnan(s)).sum())
        rows[name] = {"detection_rate": det / N_ATTACK,
                      "flagged_obs_rate": n_flag / n_obs,
                      "mean_peak_score": float(np.mean(peaks))}

    print("\n[5/5] RESULTS  (τ = %.3f | benign FPR = %.1f%% | benign peak S: "
          "mean %.2f, p99 %.2f)" % (model.threshold.item(), 100 * fpr,
                                    peak_benign.mean(), torch.quantile(peak_benign, 0.99)))
    print("-" * 66)
    print(f"{'attack':<14}{'detected':>10}{'flag-obs':>10}{'mean peak S':>14}")
    print("-" * 66)
    for name, r in rows.items():
        print(f"{name:<14}{r['detection_rate']*100:>9.0f}%"
              f"{r['flagged_obs_rate']*100:>9.1f}%{r['mean_peak_score']:>14.1f}")
    print("-" * 66)

    Path("results").mkdir(exist_ok=True)
    with open("results/eval.json", "w") as fh:
        json.dump({"threshold": model.threshold.item(), "benign_fpr": fpr,
                   "benign_peak_mean": peak_benign.mean().item(),
                   "benign_peak_p99": torch.quantile(peak_benign, 0.99).item(),
                   **rows}, fh, indent=2)
    print("saved → results/eval.json")


if __name__ == "__main__":
    main()

