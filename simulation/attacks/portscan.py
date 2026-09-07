"""
simulation/attacks/portscan.py — Reconnaissance & Port Scanning (Threat Class e)

Simulates active horizontal / vertical port scanning:
  - Single source host initiating connection attempts to many destination ports/hosts.
  - Generates multiple distinct flow keys with asymmetric fan-out.
  - Small packet sizes (44–60 bytes SYN probes with no payload data).
  - Outbound direction (direction = 0).
  - Rapid probe bursts (gap ~10–30 ms) yielding distinct flow count elevation.
"""
import struct
import numpy as np

from features.extractor import Packet


def portscan_stream(
    duration_s: float = 10.0,
    seed: int = 0,
    t0: float = 0.0,
    scan_rate: float = 50.0,
    target_ports: int = 128,
) -> list[Packet]:
    """Generate reconnaissance port scan packet stream."""
    rng = np.random.default_rng(seed)
    pkts = []
    t = t0
    mean_gap = 1.0 / scan_rate
    src_ip = b"10.0.1.99"

    # Pool of target ports/hosts being probed
    dest_pool = [
        src_ip + b"->" + struct.pack(">IH", 0xC0A80100 + int(i % 16), int(rng.integers(1, 1024)))
        for i in range(target_ports)
    ]

    while t < t0 + duration_s:
        t += float(np.clip(rng.exponential(mean_gap), 0.005, mean_gap * 2.5))
        flow_idx = int(rng.integers(0, len(dest_pool)))
        flow_key = dest_pool[flow_idx]

        # Standard minimal TCP SYN packet with empty payload
        payload = b"\x00" * 8
        size = int(rng.integers(44, 60))

        pkts.append(
            Packet(
                t=float(t),
                size=size,
                payload=payload,
                direction=0,       # OUTBOUND scan probes
                flow_key=flow_key,
            )
        )

    return pkts
