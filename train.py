"""Backend training: generate multi-regime benign traffic (telemetry + web_sync) →
featurize → window → train → calibrate → checkpoint.
Proves the unified multi-regime pipeline with zero manual steps.
"""
import torch

from features.extractor import featurize
from features.windowing import Windower
from models.njode import NJODE
from simulation.benign.telemetry import telemetry_stream
from simulation.benign.web_sync import web_sync_stream


def main():
    torch.manual_seed(0)
    print("[1/5] generating multi-regime benign streams (telemetry + web_sync, 600 s)...")
    s_tel = featurize(telemetry_stream(duration_s=600.0, seed=0))
    s_sync = featurize(web_sync_stream(duration_s=600.0, seed=1))
    print(f"      {len(s_tel)} telemetry packets, {len(s_sync)} web_sync packets featurized")

    model = NJODE(d_x=5, d_h=10)                 # Protocol v1.1: d_x=5, d_h=10, hidden=50
    win = Windower(model, window_s=10.0)
    win.fit_standardizer(s_tel, s_sync)          # Scaler fitted jointly on benign baseline

    v_tel, m_tel, t_grid = win.windows(s_tel)
    v_sync, m_sync, _ = win.windows(s_sync)

    n_tr_tel, n_tr_sync = int(0.8 * len(v_tel)), int(0.8 * len(v_sync))
    v_train = torch.cat([v_tel[:n_tr_tel], v_sync[:n_tr_sync]], dim=0)
    m_train = torch.cat([m_tel[:n_tr_tel], m_sync[:n_tr_sync]], dim=0)
    t_train = t_grid.expand(v_train.shape[0], -1)

    v_cal = torch.cat([v_tel[n_tr_tel:], v_sync[n_tr_sync:]], dim=0)
    m_cal = torch.cat([m_tel[n_tr_tel:], m_sync[n_tr_sync:]], dim=0)
    t_cal = t_grid.expand(v_cal.shape[0], -1)

    print(f"[2/5] {len(v_train)} training windows, {len(v_cal)} calibration windows × {v_train.shape[1]} grid slots")

    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(v_train, m_train, t_train),
        batch_size=32, shuffle=True)

    print("[3/5] training NJ-ODE on multiregime benign baseline...")
    model.fit(loader, epochs=60, log_every=10)

    print("[4/5] calibrating τ on held-out benign windows...")
    model.calibrate([(v_cal, m_cal, t_cal)])

    model.save("checkpoints/njode_telemetry.pt")
    print("[5/5] versioned checkpoint saved → checkpoints/njode_telemetry.pt ✓")


if __name__ == "__main__":
    main()

