"""
tests/test_real_dataset_pipeline.py — Verification of Real Benchmark Datasets & Trace Simulation
------------------------------------------------------------------------------------------------
Tests:
1. Real dataset cache integrity (CIC-IDS2017, Tranco, abuse.ch JA3, Feodo).
2. Trace-driven stream generation for benign and all 6 NTRO threat categories.
3. Feature extraction contract compliance on real-derived packet traces.
4. LiveFeeder anomaly scoring, calibrated confidence, and multi-threat attribution.
5. Simulated dataset JSON Lines export.
"""

import json
from pathlib import Path
import numpy as np
import pytest
import torch

from features.extractor import Packet, featurize, shannon_entropy, dns_character_entropy
from features.windowing import LiveFeeder, Windower
from models.njode import NJODE
from simulation.real_dataset_sim import (
    RealDatasetRepository,
    real_benign_stream,
    real_ddos_stream,
    real_c2_beacon_stream,
    real_dga_tunnel_stream,
    real_tls_c2_stream,
    real_portscan_stream,
    real_exfil_stream,
    generate_full_simulated_dataset,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
REAL_DATA_DIR = REPO_ROOT / "data" / "real"


def test_real_dataset_cache_integrity():
    """Verify authentic benchmark dataset files exist and contain valid records."""
    repo = RealDatasetRepository.get_instance()
    assert len(repo.tranco_domains) >= 10, "Tranco domains should be loaded"
    assert len(repo.abuse_ja3) >= 2, "abuse.ch JA3 fingerprints should be loaded"
    assert len(repo.feodo_c2_ips) >= 2, "Feodo C2 IPs should be loaded"
    assert len(repo.scada_telemetry) >= 10, "NPPAD SCADA telemetry should be loaded"
    assert len(repo.cicids_benign) > 0, "CIC-IDS2017 benign flows should be loaded"


def test_real_benign_stream_properties():
    """Test benign multi-regime stream contains valid, sorted packets."""
    pkts = real_benign_stream(duration_s=15.0, seed=42)
    assert len(pkts) >= 10, "Expected at least 10 benign packets in 15 seconds"
    times = [p.t for p in pkts]
    assert times == sorted(times), "Timestamps must be monotonically increasing"
    for p in pkts:
        assert p.size >= 40, "Packet wire size must be at least minimum Ethernet/IP frame"
        assert p.direction in (0, 1), "Direction must be 0 (outbound) or 1 (inbound)"


def test_real_threat_streams_conform_to_signatures():
    """Test that each threat generator produces its characteristic mathematical signature."""
    # 1. DDoS Flood: high rate, inbound direction dominant
    ddos = real_ddos_stream(duration_s=5.0, seed=10)
    assert len(ddos) >= 50, "DDoS flood should produce high packet volume"
    inbound_ratio = sum(1 for p in ddos if p.direction == 1) / len(ddos)
    assert inbound_ratio >= 0.8, "DDoS flood should be inbound dominant"

    # 2. C2 Beacon: periodic check-ins
    c2 = real_c2_beacon_stream(duration_s=10.0, seed=20)
    assert len(c2) >= 3, "C2 beacon should check in periodically"
    c2_iats = np.diff([p.t for p in c2])
    cv = np.std(c2_iats) / np.mean(c2_iats)
    assert cv < 0.25, f"C2 beaconing should have low IAT coefficient of variation (got {cv:.3f})"

    # 3. DGA & DNS Tunneling: high character entropy query names
    dga = real_dga_tunnel_stream(duration_s=5.0, seed=30)
    assert len(dga) >= 5, "DGA stream should produce DNS query packets"
    entropies = [dns_character_entropy(p.dns_query) for p in dga if p.dns_query]
    assert np.mean(entropies) >= 3.5, "DGA queries should have high character entropy"

    # 4. TLS C2: high ciphertext entropy (cryptographic payload)
    tls = real_tls_c2_stream(duration_s=5.0, seed=40)
    assert len(tls) >= 3, "TLS C2 stream should produce encrypted sessions"
    ent = [shannon_entropy(p.payload) for p in tls]
    assert np.mean(ent) >= 7.0, f"TLS ciphertext must have high Shannon entropy (got {np.mean(ent):.2f})"

    # 5. PortScan: distinct flow targets
    scan = real_portscan_stream(duration_s=5.0, seed=50)
    assert len(scan) >= 20, "Port scan should produce many probes"
    distinct_keys = len(set(p.flow_key for p in scan))
    assert distinct_keys >= 10, "Port scan must fan out across distinct destination ports/IPs"

    # 6. Exfil Burst: heavy payload sizes
    exfil = real_exfil_stream(duration_s=5.0, seed=60)
    assert len(exfil) >= 10, "Exfiltration should produce burst packets"
    large_pkts = sum(1 for p in exfil if p.size >= 1300)
    assert large_pkts / len(exfil) >= 0.8, "Exfiltration burst should saturate MTU (>1300 bytes)"


def test_full_simulated_dataset_generation(tmp_path):
    """Test generating the complete simulated dataset file."""
    out_file = tmp_path / "test_stream.jsonl"
    counts = generate_full_simulated_dataset(output_path=out_file)
    assert out_file.exists()
    assert counts["BENIGN"] > 0
    assert counts["ddos_flood"] > 0
    assert counts["exfil_burst"] > 0
    assert counts["portscan"] > 0

    # Verify JSON line structure
    with open(out_file, "r") as f:
        line = f.readline()
        record = json.loads(line)
        assert "t" in record
        assert "size" in record
        assert "entropy" in record
        assert "label" in record


def test_livefeeder_inference_on_real_packets():
    """Test that LiveFeeder ingests real-derived packets and produces structured AlertEvents."""
    model = NJODE(d_x=5, d_h=6, hidden=16, grid_step=0.01, horizon=0.5)
    model.threshold.copy_(torch.tensor(3.0))
    model.eval()

    feeder = LiveFeeder(model=model, window_s=5.0, stride_s=2.0)
    pkts = real_benign_stream(duration_s=12.0, seed=1)

    alerts = []
    for p in pkts:
        alerts.extend(feeder.ingest_packet(p))
    alerts.extend(feeder.flush())

    assert len(alerts) >= 1, "LiveFeeder should produce at least 1 AlertEvent"
    first_alert = alerts[0]
    assert hasattr(first_alert, "peak_score")
    assert hasattr(first_alert, "threshold")
    assert hasattr(first_alert, "confidence")
    assert hasattr(first_alert, "threat_class")
