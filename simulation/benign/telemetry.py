"""SCADA/PLC-style benign telemetry — small frames, steady ~1 s cadence,
low-entropy fixed-format payloads. First benign regime; web_sync comes later."""
import struct
import numpy as np

from features.extractor import Packet


def telemetry_stream(duration_s=600.0, seed=0, t0=0.0):
    rng = np.random.default_rng(seed)
    pkts, t, counter = [], t0, 0
    flow_key = b"10.0.1.10:502->10.0.1.50:502"
    while t < t0 + duration_s:
        t += float(np.clip(rng.normal(1.0, 0.05), 0.2, 2.0))
        payload = (b"\xa5\x5a"                                # fixed header
                   + struct.pack("<Hd", counter % 65536, round(rng.uniform(50.0, 60.0), 1))
                   + b"\x00" * 8)                             # fixed padding
        pkts.append(
            Packet(
                t=t,
                size=64 + int(rng.integers(0, 33)),
                payload=payload,
                direction=0,
                flow_key=flow_key,
            )
        )
        counter += 1
    return pkts

