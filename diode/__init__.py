"""Hardware data diode ingestion package."""
from diode.protocol import (
    PROTOCOL_VERSION,
    encode_record,
    decode_record,
    encode_packet,
    decode_packet,
    compute_flow_hash,
)

__all__ = [
    "PROTOCOL_VERSION",
    "encode_record",
    "decode_record",
    "encode_packet",
    "decode_packet",
    "compute_flow_hash",
]
