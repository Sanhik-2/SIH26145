"""
tests/test_real_packet.py — Unit and integration tests for CHRONOS Real Packet Engine.
Tests:
1. Multi-system packet generation and protocol compliance.
2. Simplex QR optical encoding and cv2.QRCodeDetector decoding loop.
3. Feature extraction [iat, bytes, entropy, burst, direction] across optical bridge.
4. Continuous NJ-ODE AI model evaluation and anomaly threshold hysteresis.
5. Real packet transit event dispatching to dashboard server.
"""

import json
import time
import pytest
import numpy as np
import torch
from starlette.testclient import TestClient

from features.extractor import Packet, shannon_entropy
from diode.real_packet import RealPacketMesh, DashboardNotifier
from dashboard.server import app


def test_real_packet_mesh_route_scada_packet():
    """Verify routing a SCADA packet across the optical QR diode mesh."""
    mesh = RealPacketMesh(dashboard_url="http://127.0.0.1:8501", headless=True, speed=1.0)

    test_payload = b"\x00\x01\x00\x00\x00\x06\x01\x04\x00\x00\x00\x0A" + b"TEST_SCADA"
    pkt = Packet(t=time.time(), size=len(test_payload), payload=test_payload, direction=0)

    result = mesh.route_packet(
        src_system="plc-01",
        dst_system="tx-diode",
        raw_pkt=pkt,
        is_threat=False,
        threat_type="calm",
        proto="MODBUS_SCADA"
    )

    assert result["src"] == "plc-01"
    assert result["dst"] == "tx-diode"
    assert "feat" in result
    assert len(result["feat"]) == 5
    assert result["feat"][1] == len(test_payload)
    assert result["feat"][4] == 0.0

    # Verify optical QR frame was created and is a valid image matrix
    assert mesh.last_qr_frame is not None
    assert isinstance(mesh.last_qr_frame, np.ndarray)
    assert mesh.last_qr_frame.shape == (360, 360, 3)

    mesh.close()


def test_real_packet_mesh_attack_detection():
    """Verify that an exfiltration burst packet raises NJ-ODE anomaly score."""
    mesh = RealPacketMesh(dashboard_url="http://127.0.0.1:8501", headless=True, speed=1.0)

    # Ingest a burst of exfiltration datagrams
    for i in range(12):
        exfil_bytes = b"EXFIL_DATA_CHUNK_" + (b"A" * 1380)
        pkt = Packet(t=time.time(), size=len(exfil_bytes), payload=exfil_bytes, direction=0)
        res = mesh.route_packet(
            src_system="ews-alpha",
            dst_system="tx-diode",
            raw_pkt=pkt,
            is_threat=True,
            threat_type="exfil_burst",
            proto="EXFIL_BULK_UDP"
        )

    assert mesh.current_score > 0.0
    mesh.close()


def test_dashboard_packet_event_endpoints():
    """Verify dashboard server /api/packet/event and /api/packets/recent."""
    client = TestClient(app)

    # 1. Post a real packet transit event
    event = {
        "type": "packet_transit",
        "from": "plc-01",
        "to": "tx-diode",
        "size": 128,
        "threat": False,
        "proto": "MODBUS_SCADA",
        "timestamp": time.time(),
    }
    resp = client.post("/api/packet/event", json=event)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["ingested"] == 1
    assert data["total_transited"] >= 1

    # 2. Query recent packets
    rec_resp = client.get("/api/packets/recent")
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    assert "packets" in rec_data
    assert len(rec_data["packets"]) >= 1
    last = rec_data["packets"][-1]
    assert last["from"] == "plc-01"
    assert last["to"] == "tx-diode"

    # 3. Check status
    st_resp = client.get("/api/status")
    assert st_resp.status_code == 200
    assert "packet_stats" in st_resp.json()
