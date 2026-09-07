"""
simulation/attacks/ddos_flood.py — Volumetric / Protocol DDoS (Threat Class a)

Simulates incoming volumetric / protocol flood (e.g. SYN flood, UDP reflection)
mirrored across the data diode:
  - Inbound direction (direction = 1)
  - High arrival rate (~200 pkts/s, gap ~5ms)
  - Tiny packet wire sizes (~60–68 bytes typical of SYN/UDP reflection headers)
  - Many spoofed source IP/port combinations, yielding high flow entropy
"""
import struct
import numpy as np

from features.extractor import Packet


def ddos_flood_stream(
    duration_s: float = 10.0,
    seed: int = 0,
    t0: float = 0.0,
    pkt_rate: float = 200.0,
    spoofed_sources: int = 256,
) -> list[Packet]:
    """Generate inbound volumetric DDoS packet stream."""
    rng = np.random.default_rng(seed)
    pkts = []
    t = t0
    mean_gap = 1.0 / pkt_rate

    # Generate pool of spoofed flow keys representing random source IPs & ephemeral ports
    flow_pool = [
        struct.pack(">IH", int(rng.integers(1, 0xFFFFFFFF)), int(rng.integers(1024, 65535)))
        for _ in range(spoofed_sources)
    ]

    while t < t0 + duration_s:
        # Micro-gap with small jitter
        gap = float(np.clip(rng.exponential(mean_gap), 0.001, mean_gap * 3.0))
        t += gap

        # Spoofed flow key from large pool (high flow entropy)
        flow_idx = int(rng.integers(0, len(flow_pool)))
        flow_key = flow_pool[flow_idx]

        # Tiny packet: 60-68 bytes (e.g. TCP SYN with minimal options)
        size = int(rng.integers(60, 69))
        payload = b"\x02\x04\x05\xb4\x01\x03\x03\x08" + flow_key  # SYN options dummy

        pkts.append(
            Packet(
                t=float(t),
                size=size,
                payload=payload,
                direction=1,       # INBOUND flood towards protected enclave/target
                flow_key=flow_key,
            )
        )

    return pkts
