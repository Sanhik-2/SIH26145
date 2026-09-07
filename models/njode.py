"""
models/njode.py — CHRONOS anomaly core (Neural Jump ODE)

NJ-ODE (Herrera, Krach & Teichmann, ICLR 2021, arXiv:2006.04727) adapted for
passive threat detection on unidirectional (simplex) IP traffic.

A window of packets = one "path": feature vectors x_i observed at irregular
times t_i. The model learns the conditional expectation E[X_t | A_t] of
BENIGN traffic (semi-supervised manifold). Just before each packet arrives,
outputNN yields the online prediction y⁻; the one-step prediction error
S = ||x − y⁻||² is the anomaly score. Zero-days / C2 beacons / exfil bursts
violate the benign conditional expectation → S spikes past calibrated τ.

Objective (paper eq. 33, verbatim):
    Φ(θ) = (1/N) Σ_paths (1/n_j) Σ_i ( ||x_i − y_i||₂ + ||y_i − y_i⁻||₂ )²
"""
import math
from typing import Dict, Tuple
import numpy as np
import torch
import torch.nn as nn

MODEL_VERSION = "1.0"
FEATURES = ["iat", "bytes", "entropy", "burst"]   # keep in sync with features/


# ----------------------------------------------------------------------
# Building blocks (paper App. F.1)
# ----------------------------------------------------------------------
class ResidualMLP(nn.Module):
    """2-hidden-layer tanh MLP, dropout 0.1; residual shortcut when dims match."""
    def __init__(self, in_dim, out_dim, hidden=50, dropout=0.1):
        super().__init__()
        self.body = nn.Sequential(
            nn.Linear(in_dim, hidden), nn.Tanh(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden), nn.Tanh(), nn.Dropout(dropout),
            nn.Linear(hidden, out_dim),
        )
        self.use_skip = (in_dim == out_dim)

    def forward(self, x):
        y = self.body(x)
        return y + x if self.use_skip else y


class ODEVectorField(nn.Module):
    """f_θ(h, x_last, t_last, Δt) → dh/dt   (paper eq. 29)."""
    def __init__(self, d_x, d_h, hidden=50, dropout=0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_h + d_x + 2, hidden), nn.Tanh(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden), nn.Tanh(), nn.Dropout(dropout),
            nn.Linear(hidden, d_h),
        )

    def forward(self, h, x_last, t_last, dt):
        # tanh-squash h and x (paper App. F.1) to keep inputs bounded
        z = torch.cat([torch.tanh(h), torch.tanh(x_last), t_last, dt], dim=-1)
        return self.net(z)


# ----------------------------------------------------------------------
# NJ-ODE core
# ----------------------------------------------------------------------
class NJODE(nn.Module):
    def __init__(self, d_x=4, d_h=10, hidden=50, dropout=0.1,
                 grid_step=0.01, horizon=1.0):
        super().__init__()
        assert horizon / grid_step == int(horizon / grid_step), "grid must divide horizon"
        self.d_x, self.d_h = d_x, d_h
        self.hidden, self.dropout = hidden, dropout
        self.dt = grid_step
        self.K = int(round(horizon / grid_step))          # grid points 0..K

        self.jumpNN   = ResidualMLP(d_x, d_h, hidden, dropout)
        self.outputNN = ResidualMLP(d_h, d_x, hidden, dropout)
        self.f        = ODEVectorField(d_x, d_h, hidden, dropout)

        # buffers → device-safe & saved in state_dict (threshold starts at
        # inf so an uncalibrated model flags NOTHING instead of everything)
        self.register_buffer("threshold", torch.tensor(float("inf")))
        self.register_buffer("x_mean", torch.zeros(d_x))
        self.register_buffer("x_std",  torch.ones(d_x))
        self._reset_stream()

    # ---- one pass over the time grid (batched, vectorized across paths) ----
    def _sweep(self, values, mask, t_grid, collect_scores=False):
        """
        values : (B, K+1, d_x) standardized features (zeros where unobserved)
        mask   : (B, K+1) bool — packet observed at grid point
        t_grid : (K+1,) normalized times
        returns: objective (eq. 33), per-observation scores (B, K+1, NaN=none)
        """
        if t_grid.dim() == 2:
            t_grid = t_grid[0]
        B, dev = values.size(0), values.device
        h      = torch.zeros(B, self.d_h, device=dev)
        x_last = torch.zeros(B, self.d_x, device=dev)
        t_last = torch.zeros(B, 1,        device=dev)
        seen   = torch.zeros(B, dtype=torch.bool, device=dev)

        term_sum = torch.zeros(B, device=dev)
        obs_cnt  = torch.zeros(B, device=dev)
        scores   = torch.full((B, self.K + 1), float("nan"), device=dev)

        for j in range(self.K + 1):
            obs = mask[:, j]
            if obs.any():
                x = values[:, j]
                y_minus = self.outputNN(h)                 # prediction BEFORE jump
                h_new   = self.jumpNN(x)                   # h_ti = jumpNN(x_i)
                y_new   = self.outputNN(h_new)             # y_ti

                jump_err = (x - y_new).norm(dim=-1)
                cont_err = (y_new - y_minus).norm(dim=-1)
                term = (jump_err + cont_err) ** 2          # eq. (33)
                term = torch.where(seen, term, jump_err ** 2)  # 1st obs: no y⁻

                term_sum += torch.where(obs, term, torch.zeros_like(term))
                obs_cnt  += obs.float()

                if collect_scores:
                    s = ((x - y_minus) ** 2).sum(-1)       # anomaly statistic
                    scores[:, j] = torch.where(obs & seen, s, scores[:, j])

                upd = obs.unsqueeze(-1)
                h      = torch.where(upd, h_new, h)
                x_last = torch.where(upd, x, x_last)
                t_last = torch.where(upd, t_grid[j].view(1, 1).expand(B, 1), t_last)
                seen   = seen | obs

            if j < self.K:                                 # Euler step (Algorithm 1)
                delta = t_grid[j] - t_last                 # t − τ(t)
                h = h + self.dt * self.f(h, x_last, t_last, delta)

        return (term_sum / obs_cnt.clamp(min=1.0)).mean(), scores

    # ---- training / calibration / batch scoring --------------------------
    def fit(self, loader, epochs=200, lr=1e-3, weight_decay=5e-4,
            device="cpu", log_every=10):
        """Adam lr 1e-3, wd 5e-4 — exactly the paper's training recipe."""
        self.to(device)
        opt = torch.optim.Adam(self.parameters(), lr=lr, weight_decay=weight_decay)
        for ep in range(1, epochs + 1):
            self.train()
            tot = 0.0
            for values, mask, t_grid in loader:
                values, mask, t_grid = values.to(device), mask.to(device), t_grid.to(device)
                opt.zero_grad()
                loss, _ = self._sweep(values, mask, t_grid)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.parameters(), 1.0)
                opt.step()
                tot += loss.item()
            if ep == 1 or ep % log_every == 0:
                print(f"    epoch {ep:3d}/{epochs}  Φ = {tot / len(loader):.5f}")
        return self

    @torch.no_grad()
    def calibrate(self, loader, device="cpu", quantile=0.995):
        """τ from held-out BENIGN window-PEAK scores (alert unit = window)."""
        self.to(device).eval()
        chunks = []
        for values, mask, t_grid in loader:
            _, s = self._sweep(values.to(device), mask.to(device),
                               t_grid.to(device), collect_scores=True)
            peaks = torch.nan_to_num(s, nan=float("-inf")).amax(dim=1)
            valid = (peaks != float("-inf")) & torch.isfinite(peaks)
            if valid.any():
                chunks.append(peaks[valid])
        if not chunks:
            raise ValueError("No valid window peaks found during calibration.")
        s = torch.cat(chunks)
        tau_mean, tau_q = s.mean() + 3.0 * s.std(), torch.quantile(s, quantile)
        self.threshold.copy_(torch.maximum(tau_mean, tau_q))
        print(f"[✓] window-peak τ = {self.threshold.item():.4f}  "
              f"(mean+3σ={tau_mean.item():.4f}, q{quantile}={tau_q.item():.4f})")
        return self

    @torch.no_grad()
    def compute_anomaly_scores(self, values, mask, t_grid, device="cpu"):
        self.to(device).eval()
        _, s = self._sweep(values.to(device), mask.to(device),
                           t_grid.to(device), collect_scores=True)
        return s, s > self.threshold

    # ---- streaming mode (live pipeline: diode_tap → features → here) ------
    def _reset_stream(self):
        self._sh = self._sx = self._st = None

    @torch.no_grad()
    def score_packet(self, t_norm, x_std):
        """
        One packet at a time. t_norm ∈ [0, horizon]; x_std = standardized
        features (d_x,). Returns (score, is_anomaly); NaN score on first packet.
        """
        self.eval()
        x = x_std.view(1, -1)
        t = torch.tensor([[t_norm]], dtype=x.dtype, device=x.device)
        if self._sh is None:                       # first packet: initialize
            self._sh, self._sx, self._st = self.jumpNN(x), x, t
            return float("nan"), False
        n = max(int(round((t.item() - self._st.item()) / self.dt)), 0)
        for k in range(n):                         # Euler up to arrival time
            t_cur = self._st.item() + k * self.dt
            delta = torch.tensor([[t_cur - self._st.item()]])
            self._sh = self._sh + self.dt * self.f(self._sh, self._sx, self._st, delta)
        y_minus = self.outputNN(self._sh)
        score = ((x - y_minus) ** 2).sum().item()
        flag = score > self.threshold.item()
        self._sh, self._sx, self._st = self.jumpNN(x), x, t   # jump
        return score, flag

    # ---- persistence ------------------------------------------------------
    def save(self, path):
        from pathlib import Path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save({
            "state_dict": self.state_dict(),
            "config": {
                "version": MODEL_VERSION,
                "features": list(FEATURES),
                "d_x": self.d_x,
                "d_h": self.d_h,
                "hidden": self.hidden,
                "dropout": self.dropout,
                "grid_step": self.dt,
                "horizon": self.dt * self.K,
            }
        }, path)

    @classmethod
    def load(cls, path, device="cpu"):
        ckpt = torch.load(path, map_location=device)
        config = ckpt.get("config", {})
        if "version" not in config or "features" not in config:
            import warnings
            warnings.warn(
                f"Legacy checkpoint '{path}' detected without version/features contract metadata. "
                f"Retrain via `python train.py` to generate a contract-validated v{MODEL_VERSION} artifact.",
                UserWarning,
                stacklevel=2,
            )
        # Feature contract validation to prevent silent data-plane mismatch
        ckpt_features = config.get("features")
        if ckpt_features is not None and ckpt_features != FEATURES:
            raise ValueError(
                f"Feature contract mismatch: checkpoint has {ckpt_features}, model expects {FEATURES}"
            )
        init_kwargs = {
            k: v for k, v in config.items()
            if k in ["d_x", "d_h", "hidden", "dropout", "grid_step", "horizon"]
        }
        m = cls(**init_kwargs)
        m.load_state_dict(ckpt["state_dict"])
        m.to(device)
        m._reset_stream()
        return m


def attribute_error(x, y_minus) -> Tuple[str, str, Dict[str, float]]:
    """Explainable channel attribution heuristic.

    Decomposes prediction error across [iat, bytes, entropy, burst]
    and maps the dominant channel to a threat category without supervised heads.
    """
    diff = ((x - y_minus) ** 2).detach().cpu().numpy()
    if diff.ndim > 1:
        diff = diff.flatten()
    top_idx = int(np.argmax(diff))
    name = FEATURES[top_idx]
    mapping = {
        "iat": "beacon/recon",
        "bytes": "exfil-flood",
        "entropy": "tunnel/encrypted-c2",
        "burst": "exfil-flood",
    }
    threat = mapping.get(name, "unknown")
    errs = {FEATURES[i]: float(diff[i]) for i in range(len(FEATURES))}
    return name, threat, errs


attribute_observation = attribute_error

