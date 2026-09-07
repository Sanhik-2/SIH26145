"""Backend smoke: generate benign telemetry → featurize → window → train →
calibrate → checkpoint. Proves the full plumbing with zero manual steps."""
import torch

from features.extractor import featurize
from features.windowing import Windower
from simulation.benign.telemetry import telemetry_stream
from models.njode import NJODE


def main():
    torch.manual_seed(0)
    print("[1/5] benign telemetry (600 s)...")
    stream = featurize(telemetry_stream(duration_s=600.0, seed=0))
    print(f"      {len(stream)} packets featurized")

    model = NJODE(d_x=4, d_h=10)                 # paper-scale config
    win = Windower(model, window_s=10.0)
    win.fit_standardizer(stream)                 # ← MOVE UP: scaler before windows
    values, mask, t_grid = win.windows(stream)
    n = values.shape[0]
    print(f"[2/5] {n} windows × {values.shape[1]} grid slots")


    n_tr = int(0.8 * n)
    loader = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(values[:n_tr], mask[:n_tr],
                                       t_grid.expand(n_tr, -1)),
        batch_size=32, shuffle=True)

    print("[3/5] training NJ-ODE...")
    model.fit(loader, epochs=60, log_every=10)

    print("[4/5] calibrating τ on held-out benign windows...")
    model.calibrate([(values[n_tr:], mask[n_tr:], t_grid.expand(n - n_tr, -1))])

    model.save("checkpoints/njode_telemetry.pt")
    print("[5/5] checkpoint saved → backend plumbing verified end-to-end ✓")


if __name__ == "__main__":
    main()

