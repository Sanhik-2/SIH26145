"""
Test suite for the CHRONOS NJ-ODE anomaly core (models/njode.py).

Run from repo root:
    pytest tests/ -v                  # everything (~30s incl. slow test)
    pytest tests/ -v -m "not slow"    # fast unit tests only
"""
import math

import pytest
import torch

from models.njode import NJODE

# Smaller-than-production config so the suite runs in seconds.
DT = 0.01
K = 50                      # horizon 0.5 s -> 51 grid points
HORIZON = DT * K
D_X = 4
GRID = torch.arange(K + 1) * DT


# ------------------------------------------------------------------ helpers
def make_windows(n, obs_indices_per_path=None, obs_prob=0.1, seed=0):
    """Batch of benign windows (features = 0). t0 always observed, as in pipeline."""
    g = torch.Generator().manual_seed(seed)
    if obs_indices_per_path is None:
        mask = torch.rand(n, K + 1, generator=g) < obs_prob
    else:
        mask = torch.zeros(n, K + 1, dtype=torch.bool)
        for b, idxs in enumerate(obs_indices_per_path):
            mask[b, idxs] = True
    mask[:, 0] = True
    vals = torch.zeros(n, K + 1, D_X)
    return vals, mask, GRID.clone()


def make_attack_windows(n, lo=25, hi=40, level=6.0, seed=1):
    """Benign windows with an exfil-style burst injected on [lo, hi)."""
    vals, mask, t = make_windows(n, obs_prob=0.1, seed=seed)
    vals[:, lo:hi] = level
    mask[:, lo:hi] = True
    return vals, mask, t


@pytest.fixture()
def model():
    torch.manual_seed(7)
    return NJODE(d_x=D_X, d_h=6, hidden=16, grid_step=DT, horizon=HORIZON)


# ------------------------------------------------------------- 1. config
def test_grid_must_divide_horizon():
    with pytest.raises(AssertionError):
        NJODE(d_x=D_X, grid_step=0.03, horizon=1.0)   # 1.0 / 0.03 not integral
    NJODE(d_x=D_X, grid_step=0.01, horizon=0.5)       # valid, no raise


# ------------------------------------------------------------- 2. sweep core
def test_sweep_shapes_and_nan_pattern(model):
    """Scores must exist exactly at observed points, excluding each path's
    first observation (no y⁻ exists yet) — the data contract the dashboard
    and alert engine rely on."""
    model.eval()
    vals, mask, t = make_windows(8, seed=3)
    loss, scores = model._sweep(vals, mask, t, collect_scores=True)
    assert loss.ndim == 0 and torch.isfinite(loss) and loss.item() >= 0
    assert scores.shape == (8, K + 1)
    for b in range(8):
        obs = mask[b].nonzero(as_tuple=True)[0]
        expected = set(obs[1:].tolist())                       # skip first obs
        got = set((~torch.isnan(scores[b])).nonzero(as_tuple=True)[0].tolist())
        assert got == expected


def test_sweep_no_observation_window_is_safe(model):
    """A window with zero packets must not crash or produce NaN loss."""
    model.eval()
    vals = torch.zeros(2, K + 1, D_X)
    mask = torch.zeros(2, K + 1, dtype=torch.bool)
    loss, scores = model._sweep(vals, mask, GRID)
    assert loss.item() == 0.0
    assert torch.isnan(scores).all()


def test_sweep_only_first_observation_gives_no_scores(model):
    model.eval()
    vals, mask, t = make_windows(3, obs_indices_per_path=[[0]] * 3)
    loss, scores = model._sweep(vals, mask, t, collect_scores=True)
    assert torch.isfinite(loss)
    assert torch.isnan(scores).all()


# ------------------------------------------------------------- 3. fail-safe
def test_uncalibrated_model_flags_nothing(model):
    """threshold starts at inf -> an uncalibrated model must flag NOTHING
    (fail-safe), never everything."""
    model.eval()
    vals, mask, t = make_windows(4, seed=5)
    s, flags = model.compute_anomaly_scores(vals, mask, t)
    assert torch.isinf(model.threshold)
    assert not flags.any()
    assert torch.isfinite(s[~torch.isnan(s)]).all()


# ------------------------------------------------------------- 4. calibration
def test_calibration_quantile_guarantee(model):
    """tau >= empirical q-quantile of calibration scores, so in-sample FPR is
    bounded by (1-q) for ANY score distribution — no training needed to verify."""
    model.eval()
    vals, mask, t = make_windows(64, seed=11)
    model.calibrate([(vals, mask, t)], quantile=0.99)
    assert torch.isfinite(model.threshold) and model.threshold.item() > 0
    _, flags = model.compute_anomaly_scores(vals, mask, t)
    assert flags.float().mean().item() < 0.03      # ~1% expected, 3% margin


# ------------------------------------------------------------- 5. streaming == batch
def test_streaming_matches_batch(model):
    """The live path (score_packet, one packet at a time — what diode_tap feeds)
    must reproduce the batched scorer exactly. This is the single most
    important consistency test in the suite."""
    model.eval()                                    # disable dropout -> deterministic
    vals, mask, t = make_windows(16, seed=11)
    model.calibrate([(vals, mask, t)], quantile=0.9)  # low q so some flags fire

    obs_times = [0, 7, 13, 24, 31, 42, 49]
    g = torch.Generator().manual_seed(9)
    vals1 = torch.randn(1, K + 1, D_X, generator=g) * 0.5
    mask1 = torch.zeros(1, K + 1, dtype=torch.bool)
    mask1[0, obs_times] = True
    vals1 = vals1 * mask1.unsqueeze(-1)

    s_batch, f_batch = model.compute_anomaly_scores(vals1, mask1, GRID)

    model._reset_stream()
    s_stream = []
    for j in obs_times:
        sc, _ = model.score_packet(float(j * DT), vals1[0, j])
        s_stream.append(sc)

    assert math.isnan(s_stream[0])
    assert torch.isnan(s_batch[0, obs_times[0]])
    for k in range(1, len(obs_times)):
        j = obs_times[k]
        assert s_stream[k] == pytest.approx(s_batch[0, j].item(), abs=1e-4)
        assert (s_stream[k] > model.threshold.item()) == bool(f_batch[0, j])


# ------------------------------------------------------------- 6. persistence
def test_save_load_roundtrip(model, tmp_path):
    """Checkpoint must preserve weights AND buffers: threshold tau + the
    per-feature scaler stats (x_mean/x_std) that inference preprocessing needs."""
    model.eval()
    model.x_mean.copy_(torch.linspace(-1.0, 1.0, D_X))
    model.x_std.copy_(torch.linspace(0.5, 2.0, D_X))
    vals, mask, t = make_windows(4, seed=13)
    model.calibrate([(vals, mask, t)])
    path = tmp_path / "njode.pt"
    model.save(str(path))

    loaded = NJODE.load(str(path))
    loaded.eval()
    sd_a, sd_b = model.state_dict(), loaded.state_dict()
    assert sd_a.keys() == sd_b.keys()
    for k in sd_a:
        assert torch.allclose(sd_a[k], sd_b[k]), k

    s1, f1 = model.compute_anomaly_scores(vals, mask, t)
    s2, f2 = loaded.compute_anomaly_scores(vals, mask, t)
    assert torch.allclose(s1, s2, equal_nan=True)
    assert (f1 == f2).all()


# ------------------------------------------------------------- 7. streaming edge cases
def test_score_packet_first_packet_nan_then_finite(model):
    model.eval()
    model._reset_stream()
    sc, flag = model.score_packet(0.0, torch.zeros(D_X))
    assert math.isnan(sc) and flag is False          # no prediction possible yet
    sc2, _ = model.score_packet(DT, torch.zeros(D_X))
    assert math.isfinite(sc2)


def test_score_packet_threshold_decision_is_consistent(model):
    model.eval()
    model.threshold.fill_(0.0)
    model._reset_stream()
    model.score_packet(0.0, torch.zeros(D_X))        # first packet: NaN -> False
    sc, flag = model.score_packet(DT, torch.zeros(D_X))
    assert flag == (sc > 0.0)


# ------------------------------------------------------------- 8. training wiring
def test_fit_reduces_objective(model):
    torch.manual_seed(0)
    vals, mask, t = make_windows(32, seed=17)
    loader = [(vals, mask, t)]
    model.eval()
    loss0, _ = model._sweep(vals, mask, t)
    model.fit(loader, epochs=15, log_every=1000)
    model.eval()
    loss1, _ = model._sweep(vals, mask, t)
    assert loss1 < loss0, f"loss did not decrease: {loss0:.4f} -> {loss1:.4f}"


# ------------------------------------------------------------- 9. end-to-end (slow)
@pytest.mark.slow
def test_end_to_end_detection():
    """Full pipeline: train on benign telemetry -> calibrate tau on held-out
    benign -> detect injected exfil bursts. Deterministic seeds, generous
    margins so it is CI-safe."""
    torch.manual_seed(0)
    model = NJODE(d_x=D_X, d_h=8, hidden=24, grid_step=DT, horizon=HORIZON)

    n = 160
    Xb, Mb, T = make_windows(n, obs_prob=0.1, seed=23)
    n_tr = 128
    model.fit([(Xb[:n_tr], Mb[:n_tr], T)], epochs=40, log_every=1000)
    model.calibrate([(Xb[n_tr:], Mb[n_tr:], T)])

    # benign false-positive rate
    s_ben, f_ben = model.compute_anomaly_scores(Xb[n_tr:], Mb[n_tr:], T)
    fpr = f_ben.float().mean().item()
    assert fpr < 0.05, f"benign FPR too high: {fpr:.2%}"

    # attack detection: exfil burst on grid [25, 40)
    Xa, Ma, _ = make_attack_windows(40, lo=25, hi=40, level=6.0, seed=31)
    s_att, f_att = model.compute_anomaly_scores(Xa, Ma, T)
    detected = f_att.any(dim=1).float().mean().item()
    separation = (s_att[~torch.isnan(s_att)].mean()
                  / s_ben[~torch.isnan(s_ben)].mean()).item()
    assert detected > 0.9, f"attack window detection too low: {detected:.1%}"
    assert separation > 5, f"score separation too weak: {separation:.1f}x"


# ------------------------------------------------------------- 10. CUDA (optional)
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_cuda_device_safety():
    """Buffers, t_grid, and the streaming path must all stay on-device."""
    dev = "cuda"
    model = NJODE(d_x=D_X, d_h=6, hidden=16, grid_step=DT, horizon=HORIZON).to(dev)
    vals, mask, t = make_windows(4, seed=19)
    s, f = model.compute_anomaly_scores(vals, mask, t, device=dev)
    assert s.device.type == dev
    model._reset_stream()
    sc, _ = model.score_packet(0.0, torch.zeros(D_X, device=dev))
    assert math.isnan(sc)
    sc2, _ = model.score_packet(DT, torch.randn(D_X, device=dev))
    assert math.isfinite(sc2)
