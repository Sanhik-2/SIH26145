"""
simulation/attacks/tls_c2.py — Malware inside Encrypted Sessions (Threat Class d)

Simulates encrypted C2 communications over TLS/QUIC:
  - High payload entropy ≈ 7.85–7.95 bits (cryptographically indistinguishable
    from legitimate TLS 1.3 ApplicationData ciphertexts).
  - Outbound direction (direction = 0) over a persistent session flow key.
  - Periodic timing cadence: regular heartbeats at T0 ± jitter.
  - Strict packet size sequences (e.g. 512B fixed TLS record framing).
  - Critical Property: Cannot be separated by payload entropy alone.
    Detection relies strictly on timing regularity and size metadata.
"""
import numpy as np

from features.extractor import Packet


def tls_c2_stream(
    duration_s: float = 10.0,
    seed: int = 0,
    t0: float = 0.0,
    period: float = 3.0,
    jitter: float = 0.15,
    record_size: int = 512,
) -> list[Packet]:
    """Generate encrypted TLS C2 beacon stream with ciphertext-level entropy."""
    rng = np.random.default_rng(seed)
    pkts = []
    t = t0 + period
    # Persistent TLS session flow key (e.g. internal host to external C2 IP/443)
    c2_flow_key = b"10.0.1.25:49812->198.51.100.44:443"

    while t < t0 + duration_s:
        # High-entropy encrypted ciphertext: uniform byte distribution (entropy ~ 7.9 bits)
        ciphertext = rng.integers(0, 256, record_size - 5, dtype=np.uint8).tobytes()
        # Prepend standard TLS 1.3 ApplicationData record header: 0x17, 0x03, 0x03, [len]
        header = b"\x17\x03\x03" + int(len(ciphertext)).to_bytes(2, "big")
        payload = header + ciphertext

        pkts.append(
            Packet(
                t=float(t),
                size=record_size,
                payload=payload,
                direction=0,            # OUTBOUND towards external C2 server
                flow_key=c2_flow_key,
            )
        )
        t += period + float(rng.normal(0.0, jitter))

    return pkts
