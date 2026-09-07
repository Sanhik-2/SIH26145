"""Unidirectional NTP / HTTP sync traffic simulator (second benign regime).

Simulates routine, periodic synchronization events in air-gapped or critical OT
networks (e.g. clock sync, health beacons, status poll responses).
Cadence: ~5–10 s intervals.
Packet sizes: ~200–380 bytes (distinct from ~64–96 B telemetry).
Payloads: ASCII/structured sync headers with modest Shannon entropy (~3.5–4.2 bits),
readily distinguishable from high-entropy ciphertext (>7.5 bits) or zero-padded SCADA.
"""
import string
import numpy as np

from features.extractor import Packet

SYNC_HOSTS = [b"timesync.corp.internal", b"ntp.scada.zone", b"health.telemetry.mesh"]
SYNC_HEADERS = [
    b"GET /api/v1/sync HTTP/1.1\r\nHost: %b\r\nUser-Agent: ChronosSync/2.1\r\nX-Sync-Epoch: %d\r\n\r\n",
    b"POST /status/poll HTTP/1.1\r\nHost: %b\r\nContent-Type: application/json\r\nSeq: %d\r\n\r\n",
    b"\x1b\x02\x04\xec" + b"\x00" * 8 + b"%b\x00",  # NTP-style timestamp frame
]


def web_sync_stream(duration_s=600.0, seed=0, t0=0.0):
    """Generate benign web/NTP sync packets across duration_s."""
    rng = np.random.default_rng(seed)
    pkts = []
    t = t0 + float(rng.uniform(1.0, 4.0))
    counter = 0

    while t < t0 + duration_s:
        host = rng.choice(SYNC_HOSTS)
        template = rng.choice(SYNC_HEADERS)
        if b"%d" in template:
            payload = template % (host, counter)
        else:
            payload = template % (host[:8],)

        # Pad with structured repeated sync parameters to reach ~200-380 B
        target_size = int(rng.integers(200, 381))
        pad_len = max(0, target_size - len(payload))
        if pad_len > 0:
            params = b"&status=nominal&zone=diode_tap&node_id=mesh_gw_01&mode=standby&epoch=" + str(counter).encode()
            repeated = (params * ((pad_len // len(params)) + 2))[:pad_len]
            payload += repeated

        pkts.append(
            Packet(
                t=float(t),
                size=len(payload),
                payload=payload,
                direction=0,
                flow_key=host,
            )
        )
        counter += 1
        # Sync intervals are around 6-9s with small jitter
        t += float(np.clip(rng.normal(7.5, 1.2), 3.0, 14.0))

    return pkts
