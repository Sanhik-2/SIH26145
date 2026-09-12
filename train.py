"""Backend training: generate multi-regime benign traffic (telemetry + web_sync) →
featurize → window → train → calibrate → checkpoint.
Proves the unified multi-regime pipeline with zero manual steps.
"""
import argparse
import sys
import torch

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from features.extractor import featurize
from features.windowing import Windower
from models.njode import NJODE
from simulation.benign.telemetry import telemetry_stream
from simulation.benign.web_sync import web_sync_stream
from simulation.real_dataset_sim import real_benign_stream


def main():
    parser = argparse.ArgumentParser(description="Train CHRONOS NJ-ODE model on multiregime benign baseline.")
    parser.add_argument("--epochs", type=int, default=60, help="Training epochs (default: 60)")
    parser.add_argument("--duration", type=float, default=600.0, help="Duration of training streams in seconds (default: 600)")
    parser.add_argument("--output", default="checkpoints/njode_telemetry.pt", help="Checkpoint output path")
    parser.add_argument("--device", default="cpu", help="Compute device (cpu or cuda)")
    parser.add_argument("--use-real", action="store_true", default=True, help="Train on real benchmark datasets (default: True)")
    args = parser.parse_args()

    torch.manual_seed(0)
    print(f"[1/5] generating multi-regime benign streams (Real CIC-IDS/Tranco/NPPAD + Telemetry + WebSync, {args.duration} s)...")
    s_real = featurize(real_benign_stream(duration_s=args.duration, seed=0))
    s_tel = featurize(telemetry_stream(duration_s=args.duration, seed=1))
    s_sync = featurize(web_sync_stream(duration_s=args.duration, seed=2))
    print(f"      {len(s_real)} real-derived packets, {len(s_tel)} telemetry packets, {len(s_sync)} web_sync packets featurized")

    model = NJODE(d_x=5, d_h=10)                 # Protocol v1.1: d_x=5, d_h=10, hidden=50
    win = Windower(model, window_s=10.0)
    win.fit_standardizer(s_real, s_tel, s_sync)  # Scaler fitted jointly on multi-regime benign baseline

    v_real, m_real, t_grid = win.windows(s_real)
    v_tel, m_tel, _ = win.windows(s_tel)
    v_sync, m_sync, _ = win.windows(s_sync)

    n_tr_real = int(0.8 * len(v_real)) if len(v_real) > 0 else 0
    n_tr_tel = int(0.8 * len(v_tel)) if len(v_tel) > 0 else 0
    n_tr_sync = int(0.8 * len(v_sync)) if len(v_sync) > 0 else 0

    train_v = [v for v in [v_real[:n_tr_real], v_tel[:n_tr_tel], v_sync[:n_tr_sync]] if len(v) > 0]
    train_m = [m for m in [m_real[:n_tr_real], m_tel[:n_tr_tel], m_sync[:n_tr_sync]] if len(m) > 0]
    cal_v = [v for v in [v_real[n_tr_real:], v_tel[n_tr_tel:], v_sync[n_tr_sync:]] if len(v) > 0]
    cal_m = [m for m in [m_real[n_tr_real:], m_tel[n_tr_tel:], m_sync[n_tr_sync:]] if len(m) > 0]

    v_train = torch.cat(train_v, dim=0)
    m_train = torch.cat(train_m, dim=0)
    t_train = t_grid.expand(v_train.shape[0], -1)

    v_cal = torch.cat(cal_v, dim=0)
    m_cal = torch.cat(cal_m, dim=0)
    t_cal = t_grid.expand(v_cal.shape[0], -1)

    print(f"[2/5] {len(v_train)} training windows, {len(v_cal)} calibration windows × {v_train.shape[1]} grid slots")

    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(v_train, m_train, t_train),
        batch_size=32, shuffle=True)

    if args.device != "cpu" and torch.cuda.is_available():
        model = model.to(args.device)

    print(f"[3/5] training NJ-ODE on multiregime benign baseline ({args.epochs} epochs)...")
    model.fit(loader, epochs=args.epochs, log_every=10)

    print("[4/5] calibrating τ on held-out benign windows...")
    model.calibrate([(v_cal, m_cal, t_cal)])

    model.save(args.output)
    print(f"[5/5] versioned checkpoint saved → {args.output} ✓")


if __name__ == "__main__":
    main()

