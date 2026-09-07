"""
tests/test_live_and_locked.py — Tests for unified windowing & locked design decisions.

Validates:
1. Zero train/serve skew: Windower and LiveFeeder share identical aggregate_slots collision logic.
2. Multi-packet slot collision aggregation: bytes=sum, iat=min, entropy=max, burst=max.
3. LiveFeeder sliding window scheduling with 2.0 s stride.
4. Hysteresis alert confirmation (N-of-M rule).
5. Explainable channel attribution heuristic (rule mapping without supervised heads).
6. Checkpoint as full artifact: versioning + feature contract validation.
7. Multi-regime benign traffic simulation (web_sync + telemetry).
"""
import math
import numpy as np
import pytest
import torch

from features.extractor import FeatureStream, Packet, featurize
from features.windowing import AlertEvent, LiveFeeder, Windower, aggregate_slots
from models.njode import MODEL_VERSION, FEATURES, NJODE, attribute_error
from simulation.attacks.c2_beacon import c2_beacon_stream
from simulation.attacks.dga_tunnel import dga_tunnel_stream
from simulation.attacks.exfil_burst import exfil_burst_stream
from simulation.benign.telemetry import telemetry_stream
from simulation.benign.web_sync import web_sync_stream

DT = 0.01
K = 50
HORIZON = DT * K
D_X = 5


@pytest.fixture()
def small_model():
    torch.manual_seed(42)
    m = NJODE(d_x=D_X, d_h=6, hidden=16, grid_step=DT, horizon=HORIZON)
    m.x_mean.copy_(torch.tensor([0.5, 100.0, 3.0, 0.1, 0.0]))
    m.x_std.copy_(torch.tensor([0.2, 50.0, 1.0, 0.3, 1.0]))
    m.threshold.copy_(torch.tensor(10.0))
    m.eval()
    return m


# ----------------------------------------------------------------------
# 1. Zero train/serve skew: Shared slot aggregation
# ----------------------------------------------------------------------
def test_slot_aggregation_dry(small_model):
    """Windower._slot and direct aggregate_slots must return identical tensors."""
    win = Windower(small_model, window_s=5.0)
    win.mean_ = small_model.x_mean.cpu().numpy()
    win.std_ = small_model.x_std.cpu().numpy()

    # Create dummy stream with known events (5-channel)
    t = np.array([0.1, 0.2, 0.205, 0.8, 1.5, 2.2, 4.9], dtype=np.float64)
    F = np.array([
        [0.10, 64, 1.2, 0.0, 0.0],
        [0.10, 128, 2.0, 0.0, 0.0],
        [0.005, 1400, 7.8, 1.0, 0.0],  # collision with 0.2 on same slot
        [0.60, 96, 1.5, 0.0, 0.0],
        [0.70, 80, 1.4, 0.0, 0.0],
        [0.70, 300, 3.8, 0.0, 0.0],
        [2.70, 64, 1.1, 0.0, 0.0],
    ], dtype=np.float32)
    stream = FeatureStream(t=t, F=F)


    # 1. Batch consumer (Windower)
    v_batch, m_batch = win._slot(stream, t0=0.0)

    # 2. Shared aggregate_slots
    v_shared, m_shared = aggregate_slots(
        stream.t, stream.F, t0=0.0, window_s=win.window_s,
        K=win.K, dt=win.dt, mean=win.mean_, std=win.std_
    )

    np.testing.assert_array_equal(m_batch, m_shared)
    np.testing.assert_allclose(v_batch, v_shared, rtol=1e-5, atol=1e-5)


def test_windower_vs_livefeeder_identical_tensors(small_model):
    """Windower vs LiveFeeder fed the exact same packet stream.
    Tensors are compared with torch.equal, ensuring real non-zero payload comparison."""
    win = Windower(small_model, window_s=5.0)
    win.mean_ = small_model.x_mean.cpu().numpy()
    win.std_ = small_model.x_std.cpu().numpy()

    feeder = LiveFeeder(small_model, window_s=5.0, stride_s=5.0)

    # Real packets with varied sizes, intervals, and a multi-packet slot collision
    packets = [
        Packet(t=0.10, size=64, payload=b"syn_init"),
        Packet(t=0.20, size=128, payload=b"http_request_get"),
        Packet(t=0.205, size=1400, payload=b"large_payload_burst_chunk"),  # Collision in slot 2
        Packet(t=0.80, size=96, payload=b"keepalive_ping"),
        Packet(t=1.50, size=80, payload=b"scada_telemetry"),
        Packet(t=2.20, size=300, payload=b"report_status_data"),
        Packet(t=4.90, size=64, payload=b"fin_ack"),
    ]

    # 1. Online feeder ingestion (packet by packet)
    for pkt in packets:
        feeder.ingest_packet(pkt)

    # Extract the live feeder window tensor for [0.10, 5.10]
    t0 = 0.10
    v_live, m_live = aggregate_slots(
        feeder._t_buf, feeder._F_buf, t0, feeder.window_s, feeder.K, feeder.dt,
        mean=feeder.mean_, std=feeder.std_
    )
    t_vals_live = torch.from_numpy(v_live)
    t_mask_live = torch.from_numpy(m_live)

    # 2. Batch Windower ingestion on the exact same packets
    stream = featurize(packets)
    v_win, m_win = win._slot(stream, t0=t0)
    t_vals_win = torch.from_numpy(v_win)
    t_mask_win = torch.from_numpy(m_win)

    # Non-negotiable check: ensure real, non-zero data (not zero stubs)
    assert (t_vals_win != 0).any(), "Windower tensor must contain non-zero standardized values"
    assert (t_vals_live != 0).any(), "LiveFeeder tensor must contain non-zero standardized values"
    assert t_mask_win.any(), "Mask must contain true observations"
    assert t_mask_win.sum().item() >= 5, "At least 5 slots must be observed"

    # Strict bit-identical tensor equality across both pipelines
    assert torch.equal(t_mask_win, t_mask_live), "Observation masks must be bit-identical"
    assert torch.equal(t_vals_win, t_vals_live), "Slotted feature values must be bit-identical"


def test_slot_collision_aggregation_semantics():
    """Verify that multiple packets colliding in a slot aggregate correctly:
    bytes=sum, iat=min, entropy=max, burst=max."""
    window_s = 10.0
    K = 100
    dt = 0.01  # slot size = 10.0 * 0.01 = 0.1s
    t0 = 0.0

    # Three packets in slot index 2 (t in [0.20, 0.30))
    # Two inbound (1.0) and one outbound (0.0) -> majority rule = 1.0
    t = np.array([0.21, 0.24, 0.28], dtype=np.float64)
    F = np.array([
        [0.05, 100.0, 2.0, 0.0, 0.0],
        [0.03, 500.0, 4.5, 0.0, 1.0],
        [0.01, 800.0, 7.2, 1.0, 1.0],
    ], dtype=np.float32)

    values, mask = aggregate_slots(t, F, t0, window_s, K, dt, mean=None, std=None)

    slot_idx = 2
    assert mask[slot_idx] is True or mask[slot_idx] == 1
    assert mask.sum() == 1  # only that slot observed

    # iat min = 0.01
    assert values[slot_idx, 0] == pytest.approx(0.01)
    # bytes sum = 100 + 500 + 800 = 1400
    assert values[slot_idx, 1] == pytest.approx(1400.0)
    # entropy max = 7.2
    assert values[slot_idx, 2] == pytest.approx(7.2)
    # burst max = 1.0
    assert values[slot_idx, 3] == pytest.approx(1.0)
    # direction majority (2 of 3 inbound) = 1.0
    assert values[slot_idx, 4] == pytest.approx(1.0)



# ----------------------------------------------------------------------
# 2. LiveFeeder sliding window stride and scheduling
# ----------------------------------------------------------------------
def test_live_feeder_sliding_stride(small_model):
    """Verify that LiveFeeder emits windows at every stride_s (2.0s) boundary."""
    feeder = LiveFeeder(small_model, window_s=10.0, stride_s=2.0)

    # Ingest 15 seconds of sparse packets (one per second)
    all_alerts = []
    for sec in range(16):
        pkt = Packet(t=float(sec), size=80, payload=b"sample_payload")
        alerts = feeder.ingest_packet(pkt)
        all_alerts.extend(alerts)

    # Window starts at 0, first window ends at 10.0s, then 12.0s, 14.0s
    assert len(all_alerts) == 3
    assert all_alerts[0].window_t0 == pytest.approx(0.0)
    assert all_alerts[0].window_t1 == pytest.approx(10.0)
    assert all_alerts[1].window_t0 == pytest.approx(2.0)
    assert all_alerts[1].window_t1 == pytest.approx(12.0)
    assert all_alerts[2].window_t0 == pytest.approx(4.0)
    assert all_alerts[2].window_t1 == pytest.approx(14.0)


# ----------------------------------------------------------------------
# 3. Hysteresis alert confirmation
# ----------------------------------------------------------------------
def test_live_feeder_hysteresis():
    """Verify N-of-M hysteresis prevents single transient spikes from confirming."""
    class MockModel(NJODE):
        def __init__(self):
            super().__init__(d_x=D_X, d_h=4, hidden=8, grid_step=DT, horizon=HORIZON)
            self.x_mean.copy_(torch.zeros(D_X))
            self.x_std.copy_(torch.ones(D_X))
            self.threshold.copy_(torch.tensor(5.0))
            self.forced_scores = []

        def _sweep(self, values, mask, t_grid, collect_scores=False):
            # Return forced peak score
            score_val = self.forced_scores.pop(0) if self.forced_scores else 1.0
            scores = torch.full((1, self.K + 1), float("nan"))
            scores[0, 1] = score_val
            scores[0, 2] = score_val
            return torch.tensor(0.0), scores

    mock_m = MockModel()
    # Sequence of window peak scores: [6.0 (alert), 2.0 (clean), 6.0 (alert), 7.0 (alert)]
    mock_m.forced_scores = [6.0, 2.0, 6.0, 7.0]

    # 2 of 3 hysteresis
    feeder = LiveFeeder(mock_m, window_s=2.0, stride_s=1.0, hysteresis_n=2, hysteresis_m=3)
    # Populate buffer with timestamps covering windows [0, 5]
    feeder._t_buf = [0.5, 1.5, 2.5, 3.5, 4.5]
    feeder._F_buf = [np.zeros(D_X, dtype=np.float32) for _ in range(5)]

    # Window 1: score 6.0 -> is_anomaly=True, history=[True], confirmed=False (1 < 2)
    ev1 = feeder._score_window(0.0, 2.0)
    assert ev1.is_anomaly is True
    assert ev1.confirmed is False

    # Window 2: score 2.0 -> is_anomaly=False, history=[True, False], confirmed=False
    ev2 = feeder._score_window(1.0, 3.0)
    assert ev2.is_anomaly is False
    assert ev2.confirmed is False

    # Window 3: score 6.0 -> is_anomaly=True, history=[True, False, True], confirmed=True (2 of 3!)
    ev3 = feeder._score_window(2.0, 4.0)
    assert ev3.is_anomaly is True
    assert ev3.confirmed is True

    # Window 4: score 7.0 -> is_anomaly=True, history=[False, True, True], confirmed=True (2 of 3!)
    ev4 = feeder._score_window(3.0, 5.0)
    assert ev4.is_anomaly is True
    assert ev4.confirmed is True


# ----------------------------------------------------------------------
# 4. Explainable channel attribution heuristic
# ----------------------------------------------------------------------
def test_channel_attribution_heuristic():
    """Verify channel attribution maps dominant residuals without supervised heads:
    bytes/burst -> exfil-flood, entropy -> tunnel/encrypted-c2, iat -> beacon/recon."""
    # 1. High bytes residual
    x1 = torch.tensor([0.0, 25.0, 0.5, 0.0])
    y1 = torch.tensor([0.0, 0.0, 0.5, 0.0])
    name1, threat1, _ = attribute_error(x1, y1)
    assert name1 == "bytes"
    assert threat1 == "exfil-flood"

    # 2. High burst residual
    x2 = torch.tensor([0.0, 1.0, 0.5, 15.0])
    y2 = torch.tensor([0.0, 1.0, 0.5, 0.0])
    name2, threat2, _ = attribute_error(x2, y2)
    assert name2 == "burst"
    assert threat2 == "exfil-flood"

    # 3. High entropy residual
    x3 = torch.tensor([0.0, 1.0, 20.0, 0.0])
    y3 = torch.tensor([0.0, 1.0, 1.0, 0.0])
    name3, threat3, _ = attribute_error(x3, y3)
    assert name3 == "entropy"
    assert threat3 == "tunnel/encrypted-c2"

    # 4. High iat (timing jitter) residual
    # 4. High iat (timing jitter) residual
    x4 = torch.tensor([18.0, 1.0, 1.0, 0.0])
    y4 = torch.tensor([0.0, 1.0, 1.0, 0.0])
    name4, threat4, _ = attribute_error(x4, y4)
    assert name4 == "iat"
    assert threat4 == "beacon/recon"

    # 5. High direction (inbound flood) residual
    x5 = torch.tensor([0.0, 1.0, 0.5, 0.0, 12.0])
    y5 = torch.tensor([0.0, 1.0, 0.5, 0.0, 0.0])
    name5, threat5, _ = attribute_error(x5, y5)
    assert name5 == "direction"
    assert threat5 == "volumetric-ddos"


# ----------------------------------------------------------------------
# 5. Checkpoint full artifact (versioning + feature contract)
# ----------------------------------------------------------------------
def test_checkpoint_full_artifact(small_model, tmp_path):
    """Checkpoint must save MODEL_VERSION and FEATURES, and reject mismatched features."""
    ckpt_path = tmp_path / "test_model.pt"
    small_model.save(str(ckpt_path))

    # Verify saved metadata
    data = torch.load(str(ckpt_path), map_location="cpu")
    assert "version" in data["config"]
    assert data["config"]["version"] == MODEL_VERSION
    assert "features" in data["config"]
    assert data["config"]["features"] == FEATURES

    # Successful load
    loaded = NJODE.load(str(ckpt_path))
    assert loaded.d_x == small_model.d_x
    assert torch.allclose(loaded.x_mean, small_model.x_mean)
    assert torch.allclose(loaded.x_std, small_model.x_std)

    # Incompatible feature contract must raise ValueError
    data["config"]["features"] = ["iat", "bytes", "entropy", "WRONG_FEATURE"]
    bad_path = tmp_path / "bad_model.pt"
    torch.save(data, str(bad_path))

    with pytest.raises(ValueError, match="Feature contract mismatch"):
        NJODE.load(str(bad_path))


# ----------------------------------------------------------------------
# 6. Multi-regime benign traffic generator
# ----------------------------------------------------------------------
def test_web_sync_stream_properties():
    """Verify web_sync_stream produces benign periodic sync packets with expected characteristics."""
    pkts = web_sync_stream(duration_s=60.0, seed=42)
    assert len(pkts) >= 4  # ~6-9s cadence in 60s
    sizes = [p.size for p in pkts]
    assert all(150 <= s <= 450 for s in sizes)

    # Shannon entropy should be moderate (~3.0 to ~5.0 bits)
    from features.extractor import shannon_entropy
    entropies = [shannon_entropy(p.payload) for p in pkts]
    assert all(2.5 <= e <= 5.5 for e in entropies)


# ----------------------------------------------------------------------
# 7. Campaign factory smoke test across all 6 threat classes
# ----------------------------------------------------------------------
def test_campaign_factory_smoke():
    """Every attack entry in the campaign factory must actually build —
    catches copy-paste kwarg drift across all 6 attack classes."""
    from evaluate_campaign import ATTACK_FACTORIES, build_continuous_campaign
    six_threats = ("c2_beacon", "exfil_burst", "dga_tunnel", "ddos_flood", "tls_c2", "portscan")
    for name in six_threats:
        assert name in ATTACK_FACTORIES, f"Missing attack factory: {name}"
        pkts, phases = build_continuous_campaign(
            attack_name=name, seed=1,
            t_phase1=2.0, t_phase2=2.0, t_phase3=4.0, t_phase4=2.0
        )
        assert len(pkts) > 0, f"{name} produced no packets"
        assert len(phases) == 4, f"{name} phases missing"


# ----------------------------------------------------------------------
# 8. Calibrated confidence monotonicity
# ----------------------------------------------------------------------
def test_calibrated_confidence_monotonicity(small_model):
    """Confidence score must be strictly non-decreasing with peak anomaly score."""
    small_model.calibration_quantiles.copy_(torch.tensor([1.5, 3.0, 6.0, 12.0]))
    small_model.threshold.copy_(torch.tensor(3.0))

    test_scores = np.linspace(0.0, 50.0, 100)
    confidences = [small_model.compute_confidence(float(s)) for s in test_scores]

    # Monotonicity check: c[i] <= c[i+1] for all i
    for i in range(len(confidences) - 1):
        assert confidences[i] <= confidences[i + 1] + 1e-7, (
            f"Confidence decreased from s={test_scores[i]} (c={confidences[i]}) "
            f"to s={test_scores[i+1]} (c={confidences[i+1]})"
        )
    # Boundedness
    assert all(0.0 <= c <= 1.0 for c in confidences)
    assert confidences[0] == 0.0
    assert confidences[-1] > 0.95


# ----------------------------------------------------------------------
# 9. Hardware Data Diode protocol roundtrip (Protocol v1.1)
# ----------------------------------------------------------------------
def test_diode_protocol_roundtrip():
    """Verify 15-byte record and packet frames encode/decode faithfully across diode."""
    from diode.protocol import (
        encode_record, decode_record, encode_packet, decode_packet, compute_flow_hash
    )

    # 1. 15-byte record roundtrip
    raw_rec = encode_record(
        t_s=12.345, iat_s=0.025, size=1400, entropy=7.8, direction=1, flow_hash=0x1234
    )
    assert len(raw_rec) == 15
    dec = decode_record(raw_rec)
    assert dec is not None
    t_dec, iat_dec, size_dec, ent_dec, dir_dec, flow_dec = dec
    assert abs(t_dec - (int(12.345 * 1000) / 1000.0)) < 0.002
    assert abs(iat_dec - 0.025) < 0.001
    assert size_dec == 1400
    assert abs(ent_dec - 7.8) < 0.1
    assert dir_dec == 1
    assert flow_dec == 0x1234

    # 2. Packet frame roundtrip
    p_orig = Packet(
        t=100.5, size=512, payload=b"optical_airgap_diode_test", direction=1, flow_key=b"flow_a"
    )
    p_enc = encode_packet(p_orig)
    p_dec = decode_packet(p_enc)
    assert p_dec is not None
    assert abs(p_dec.t - p_orig.t) < 1e-5
    assert p_dec.size == p_orig.size
    assert p_dec.payload == p_orig.payload
    assert p_dec.direction == p_orig.direction


# ----------------------------------------------------------------------
# 10. Evidence layer calculation
# ----------------------------------------------------------------------
def test_evidence_layer_metrics(small_model):
    """Verify LiveFeeder calculates distinct flows, flow entropy, and direction byte ratios."""
    feeder = LiveFeeder(small_model, window_s=5.0, stride_s=5.0)

    # Ingest diverse stream: 10 outbound packets on flow A, 10 inbound packets on flow B
    flow_a = b"src_a:1000->dst:80"
    flow_b = b"src_b:2000->dst:80"

    packets = [
        Packet(t=0.1 * i, size=100, payload=b"\x00" * 20, direction=0, flow_key=flow_a)
        for i in range(1, 11)
    ] + [
        Packet(t=1.5 + 0.1 * i, size=200, payload=b"\x00" * 20, direction=1, flow_key=flow_b)
        for i in range(1, 11)
    ]

    for p in packets:
        feeder.ingest_packet(p)

    alerts = feeder.flush()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert.evidence is not None
    ev = alert.evidence

    assert ev["distinct_flows"] == 2
    assert ev["flow_entropy"] > 0.9     # 50/50 split -> H ~ 1.0 bit
    assert ev["outbound_bytes"] == 1000 # 10 * 100
    assert ev["inbound_bytes"] == 2000  # 10 * 200
    assert ev["outbound_inbound_byte_ratio"] == pytest.approx(0.5, rel=1e-2)


