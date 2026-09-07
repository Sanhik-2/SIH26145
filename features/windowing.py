"""Bridge: FeatureStream → NJ-ODE tensors (values, mask, t_grid).

Owns standardization (mirrored into the model's x_mean/x_std buffers so
checkpoints carry the scaler — kills the preprocessing-drift bug class).
Collision policy per slot: bytes=sum, iat=min, entropy=max, burst=max.
Real time is normalized to the model's [0,1] horizon; window_s is a free
parameter (default 10 s → 10 ms effective slot resolution on a 0.01 grid).
"""
import numpy as np
import torch

from features.extractor import D_X


class Windower:
    def __init__(self, model, window_s=10.0):
        self.model = model
        self.window_s = float(window_s)
        self.K, self.dt = model.K, model.dt     # grid geometry comes from the model
        self.mean_ = self.std_ = None

    @torch.no_grad()
    def fit_standardizer(self, *streams):
        """Fit on BENIGN data only (unsupervised — no labels to leak)."""
        X = np.concatenate([s.F for s in streams if len(s)], axis=0)
        self.mean_ = X.mean(0).astype(np.float32)
        self.std_ = np.maximum(X.std(0), 0.1).astype(np.float32)   # floor: no /1e-8 explosions
        self.model.x_mean.copy_(torch.tensor(self.mean_))
        self.model.x_std.copy_(torch.tensor(self.std_))
        return self.mean_, self.std_

    def _slot(self, stream, t0):
        values = np.zeros((self.K + 1, D_X), dtype=np.float32)
        mask = np.zeros(self.K + 1, dtype=bool)
        m = (stream.t >= t0) & (stream.t < t0 + self.window_s)
        if m.any():
            t, F = stream.t[m], stream.F[m]
            j = np.minimum(((t - t0) / self.window_s / self.dt).astype(np.int64), self.K)
            order = np.argsort(j, kind="stable")
            j, F = j[order], F[order]
            starts = np.flatnonzero(np.r_[True, j[1:] != j[:-1]])
            slots = j[starts]
            values[slots, 0] = np.minimum.reduceat(F[:, 0], starts)
            values[slots, 1] = np.add.reduceat(F[:, 1], starts)
            values[slots, 2] = np.maximum.reduceat(F[:, 2], starts)
            values[slots, 3] = np.maximum.reduceat(F[:, 3], starts)
            mask[slots] = True
        values = np.clip((values - self.mean_) / self.std_, -30.0, 30.0)  # bound deviations
        values[~mask] = 0.0
        return values, mask

    def windows(self, stream, stride_s=None):
        """Sliding windows → (values (N,K+1,4), mask (N,K+1) bool, t_grid (K+1,))."""
        if self.mean_ is None:
            raise RuntimeError("call fit_standardizer() before windows()")
        stride = self.window_s if stride_s is None else stride_s
        vals, masks = [], []
        t0 = float(stream.t[0])
        while t0 < stream.t[-1]:
            v, m = self._slot(stream, t0)
            if m.any():
                vals.append(v); masks.append(m)
            t0 += stride
        return (torch.from_numpy(np.stack(vals)),
                torch.from_numpy(np.stack(masks)),
                torch.linspace(0.0, 1.0, self.K + 1, dtype=torch.float32))

