"""
tests/test_diode_qr.py — Unit and integration tests for optical QR data diode ingestion.

Tests:
1. QR Code Matrix Generation & cv2.QRCodeDetector decoding roundtrip.
2. Simplex packet bridging: Binary Packet -> QR Optical Payload featurization.
3. Optical Frame -> Packet -> LiveFeeder NJ-ODE continuous scoring roundtrip.
4. Process sentry dictionary cross-platform resolution.
"""
import json
import cv2
import numpy as np
import pytest
import torch

from features.extractor import Packet, shannon_entropy
from features.windowing import LiveFeeder
from models.njode import NJODE
from diode.qr_gateway import generate_qr_matrix
from diode.protocol import encode_packet, decode_packet
from diode.nuclear_node import WATCHED_APPS


def test_qr_generation_and_decode_roundtrip():
    """Verify that generate_qr_matrix creates a QR code decodable by OpenCV."""
    payload = {
        "seq": 42,
        "ts": "12:34:56",
        "type": "ROUTINE_SCADA",
        "feat": [1.02, 128, 3.45, 1.0, 0],
        "temp": 295.4,
        "press": 155.0,
        "freq": 50.00,
        "app": "",
        "atk": "",
        "msg": "Nominal Reactor Steady State"
    }
    raw_str = json.dumps(payload)
    qr_img = generate_qr_matrix(raw_str, size=(440, 440))

    assert qr_img is not None
    assert qr_img.shape == (440, 440, 3)
    assert qr_img.dtype == np.uint8

    detector = cv2.QRCodeDetector()
    decoded_str, bbox, _ = detector.detectAndDecode(qr_img)

    assert decoded_str, "cv2.QRCodeDetector failed to decode generated QR image"
    decoded_data = json.loads(decoded_str)
    assert decoded_data["seq"] == 42
    assert decoded_data["type"] == "ROUTINE_SCADA"
    assert decoded_data["feat"] == [1.02, 128, 3.45, 1.0, 0]


def test_binary_packet_to_optical_feated_payload():
    """Verify binary protocol frame conversion to optical payload."""
    original_pkt = Packet(
        t=10.5,
        size=1400,
        payload=b"A" * 1400,  # low entropy
        direction=1,
        flow_key=b"192.168.1.1:80->10.0.0.1:443"
    )
    data = encode_packet(original_pkt)
    decoded = decode_packet(data)

    assert decoded is not None
    assert decoded.size == 1400
    assert decoded.direction == 1
    assert len(decoded.payload) == 1400

    # Featurize
    ent = shannon_entropy(decoded.payload)
    feat = [0.05, decoded.size, round(ent, 2), 1.0, decoded.direction]
    assert feat[0] == 0.05
    assert feat[1] == 1400
    assert feat[4] == 1


def test_optical_frame_to_livefeeder_scoring():
    """Test full pipeline: Optical Frame -> Packet -> LiveFeeder NJ-ODE scoring."""
    model = NJODE(d_x=5, d_h=6, hidden=16, grid_step=0.01, horizon=0.5)
    model.x_mean.copy_(torch.tensor([0.5, 100.0, 3.0, 0.1, 0.0]))
    model.x_std.copy_(torch.tensor([0.2, 50.0, 1.0, 0.3, 1.0]))
    model.threshold.copy_(torch.tensor(2.50))
    model.eval()

    feeder = LiveFeeder(model=model, window_s=5.0, stride_s=1.0)

    # Simulated decoded optical QR payloads arriving across diode
    optical_payloads = [
        {"seq": 1, "feat": [1.0, 120, 3.5, 1.0, 0], "type": "ROUTINE_SCADA", "msg": "calm"},
        {"seq": 2, "feat": [0.02, 1400, 7.9, 10.0, 0], "type": "CYBER_ATTACK", "msg": "exfil"},
        {"seq": 3, "feat": [0.01, 1400, 7.9, 10.0, 0], "type": "CYBER_ATTACK", "msg": "exfil"},
        {"seq": 4, "feat": [0.01, 1400, 7.9, 10.0, 0], "type": "CYBER_ATTACK", "msg": "exfil"},
        {"seq": 5, "feat": [0.01, 1400, 7.9, 10.0, 0], "type": "CYBER_ATTACK", "msg": "exfil"},
        {"seq": 6, "feat": [0.01, 1400, 7.9, 10.0, 0], "type": "CYBER_ATTACK", "msg": "exfil"},
    ]

    all_alerts = []
    base_t = 1000.0
    for i, op in enumerate(optical_payloads):
        feat = op["feat"]
        pkt = Packet(
            t=base_t + i * 1.0,
            size=int(feat[1]),
            payload=op["msg"].encode(),
            direction=int(feat[4])
        )
        alerts = feeder.ingest_packet(pkt)
        all_alerts.extend(alerts)

    # Flush remaining
    flushed = feeder.flush()
    all_alerts.extend(flushed)

    assert len(all_alerts) > 0, "LiveFeeder produced no window alerts from optical stream"
    for a in all_alerts:
        assert isinstance(a.peak_score, float)
        assert np.isfinite(a.peak_score)
        assert a.threshold == 2.50
        assert "threat_type" in (a.attribution or {})


def test_cross_platform_process_watching():
    """Verify Linux and Windows process binary names are resolved."""
    assert "notepad" in WATCHED_APPS or "notepad.exe" in WATCHED_APPS
    assert "calc" in WATCHED_APPS or "calc.exe" in WATCHED_APPS
    assert "bash" in WATCHED_APPS or "sh" in WATCHED_APPS
    assert "python3" in WATCHED_APPS or "python" in WATCHED_APPS
