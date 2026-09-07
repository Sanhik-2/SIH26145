"""Asymmetric bulk exfiltration — sustained large-packet flood (burst-dominant)."""
import numpy as np

from features.extractor import Packet


def exfil_burst_stream(duration_s=10.0, seed=0, t0=0.0,
                       gap_mean=0.012, pkt_size=1400):
    rng = np.random.default_rng(seed)
    pkts, t = [], t0
    flow_key = b"10.0.1.25:52001->198.51.100.99:9000"
    while t < t0 + duration_s:
        t += float(np.clip(rng.normal(gap_mean, 0.003), 0.004, 0.05))
        payload = rng.integers(0, 256, pkt_size, dtype=np.uint8).tobytes()
        pkts.append(Packet(t=float(t), size=pkt_size, payload=payload, direction=0, flow_key=flow_key))
    return pkts

