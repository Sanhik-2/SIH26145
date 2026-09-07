"""DNS tunneling — base64-ish labels at query cadence (entropy-dominant)."""
import string

import numpy as np

from features.extractor import Packet

ALPHABET = np.frombuffer(
    (string.ascii_letters + string.digits + "+/").encode(), dtype=np.uint8)


def dga_tunnel_stream(duration_s=10.0, seed=0, t0=0.0,
                      gap_mean=0.4, label_len=150):
    rng = np.random.default_rng(seed)
    pkts, t = [], t0 + gap_mean
    while t < t0 + duration_s:
        label = rng.choice(ALPHABET, label_len).tobytes()
        payload = b"q." + label + b".exfil.example"
        pkts.append(Packet(t=float(t), size=len(payload) + 42, payload=payload))
        t += float(np.clip(rng.normal(gap_mean, 0.1), 0.1, 1.5))
    return pkts
