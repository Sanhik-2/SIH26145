"""
diode/protocol.py — Simplex Hardware Data Diode Ingestion Protocol (v1.1)

Defines the physical / link-level one-way transmission frame contract across
the optical or serial hardware data diode into the monitoring enclave.
No return path exists (0.00% reverse bit transmission).

Feature Contract Version: 1.1
Protocol Wire Format:
  - Header: MAGIC (5B: b"DIODE") + VERSION (2B: 0x01, 0x01 = v1.1)
  - Record (15 Bytes):
      [0:4]   t_ms      (uint32, milliseconds timestamp % 2^32)
      [4:8]   iat_us    (uint32, microsecond inter-arrival time)
      [8:10]  bytes     (uint16, wire frame bytes)
      [10:11] ent100    (uint8,  Shannon entropy * 10, range 0..80)
      [11:12] flags     (uint8,  bit 0 = direction: 0=outbound, 1=inbound)
      [12:14] flow_hash (uint16, 16-bit anonymized flow identifier)
      [14:15] crc8      (uint8,  simple 8-bit checksum for transmission fidelity)
"""
import hashlib
import struct
from typing import Optional, Tuple

from features.extractor import Packet, shannon_entropy

PROTOCOL_VERSION = "1.1"
DIODE_MAGIC = b"DIODE\x01\x01"  # 7-byte header
RECORD_SIZE = 15
RECORD_FORMAT = ">IIHBBHB"      # 4 + 4 + 2 + 1 + 1 + 2 + 1 = 15 bytes


def compute_crc8(data: bytes) -> int:
    """Fast 8-bit XOR checksum for transmission integrity."""
    val = 0
    for b in data:
        val = (val ^ b) & 0xFF
    return val


def compute_flow_hash(flow_key: bytes) -> int:
    """Hash flow key (e.g. 5-tuple) to a 16-bit uint."""
    if not flow_key:
        return 0
    digest = hashlib.md5(flow_key).digest()
    return struct.unpack(">H", digest[:2])[0]


def encode_record(
    t_s: float,
    iat_s: float,
    size: int,
    entropy: float,
    direction: int,
    flow_hash: int = 0
) -> bytes:
    """Encode a 15-byte telemetry feature record for simplex diode transmission."""
    t_ms = int(round(t_s * 1000.0)) & 0xFFFFFFFF
    iat_us = int(round(max(0.0, iat_s) * 1_000_000.0)) & 0xFFFFFFFF
    wire_bytes = min(int(size), 65535)
    ent100 = min(int(round(max(0.0, entropy) * 10.0)), 255)
    flags = 1 if direction else 0
    f_hash = flow_hash & 0xFFFF

    body = struct.pack(">IIHBBH", t_ms, iat_us, wire_bytes, ent100, flags, f_hash)
    crc8 = compute_crc8(body)
    return body + struct.pack("B", crc8)


def decode_record(data: bytes) -> Optional[Tuple[float, float, int, float, int, int]]:
    """Decode a 15-byte record. Returns (t_ms/1000, iat_s, size, entropy, direction, flow_hash) or None."""
    if len(data) < RECORD_SIZE:
        return None
    raw = data[:RECORD_SIZE]
    body, crc8_exp = raw[:14], raw[14]
    if compute_crc8(body) != crc8_exp:
        return None  # Checksum mismatch
    t_ms, iat_us, wire_bytes, ent100, flags, flow_hash = struct.unpack(">IIHBBH", body)
    direction = flags & 0x01
    entropy = ent100 / 10.0
    return (t_ms / 1000.0, iat_us / 1_000_000.0, wire_bytes, entropy, direction, flow_hash)


def encode_packet(p: Packet) -> bytes:
    """
    Encode full raw packet frame across diode:
    [8B float t][4B uint size][1B direction][2B flow_hash][payload]
    """
    flow_hash = compute_flow_hash(p.flow_key)
    direction = 1 if getattr(p, "direction", 0) else 0
    header = struct.pack(">dIBH", p.t, p.size, direction, flow_hash)
    return header + (p.payload or b"")


def decode_packet(data: bytes) -> Optional[Packet]:
    """Decode raw packet frame from simplex diode transmission."""
    if len(data) < 15:
        # Fallback for legacy 12-byte frames [8B t][4B size][payload]
        if len(data) >= 12:
            t, size = struct.unpack(">dI", data[:12])
            payload = data[12:]
            return Packet(t=t, size=size, payload=payload, direction=0, flow_key=b"")
        return None
    t, size, direction, flow_hash = struct.unpack(">dIBH", data[:15])
    payload = data[15:]
    flow_bytes = struct.pack(">H", flow_hash)
    return Packet(t=t, size=size, payload=payload, direction=direction, flow_key=flow_bytes)
