"""C2 beaconing — encrypted check-ins at T0 ± jitter. (Low-and-slow variants
with longer periods are a knob for later hardening demos.)"""
import numpy as np

from features.extractor import Packet


def c2_beacon_stream(duration_s=10.0, seed=0, t0=0.0,
                     period=2.5, jitter=0.2, payload_len=48):
    rng = np.random.default_rng(seed)
    pkts, t = [], t0 + period
    flow_key = b"10.0.1.10:49210->203.0.113.50:8443"
    while t < t0 + duration_s:
        payload = rng.integers(0, 256, payload_len, dtype=np.uint8).tobytes()
        pkts.append(Packet(t=float(t), size=payload_len + 56, payload=payload, direction=0, flow_key=flow_key))
        t += period + float(rng.normal(0.0, jitter))
    return pkts

