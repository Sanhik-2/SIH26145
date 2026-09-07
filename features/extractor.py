"""CHRONOS feature extraction — packets → the 4-feature contract (natural units)."""
from dataclasses import dataclass
import numpy as np

FEATURE_NAMES = ["iat", "bytes", "entropy", "burst", "direction"]
D_X = 5
BURST_IAT_S = 0.02          # gap ≤ 20 ms = burst


@dataclass
class Packet:
    t: float                # seconds (any monotonic clock)
    size: int               # wire bytes
    payload: bytes = b""
    direction: int = 0      # 0 = outbound, 1 = inbound
    flow_key: bytes = b""   # optional flow identifier (e.g. 5-tuple hash)


@dataclass
class FeatureStream:
    t: np.ndarray           # (n,) float64, sorted
    F: np.ndarray           # (n, 5) float32 = [iat, bytes, entropy, burst, direction]
    def __len__(self):
        return len(self.t)


def shannon_entropy(payload: bytes) -> float:
    """Bits (0–8) of the byte-value distribution; 0.0 for empty payload."""
    if not payload:
        return 0.0
    counts = np.bincount(np.frombuffer(payload, dtype=np.uint8), minlength=256)
    p = counts[counts > 0] / len(payload)
    return float(-(p * np.log2(p)).sum())


def featurize(packets, sort=True) -> FeatureStream:
    """
    Stream-relative features:
      0: iat = gap to previous packet in whole stream (first packet -> 0.0)
      1: size = wire bytes
      2: entropy = Shannon entropy of payload (bits 0..8)
      3: burst = indicator (iat <= BURST_IAT_S)
      4: direction = 0.0 for outbound, 1.0 for inbound
    """
    pkts = sorted(packets, key=lambda p: p.t) if sort else list(packets)
    n = len(pkts)
    t = np.array([p.t for p in pkts], dtype=np.float64)
    F = np.zeros((n, D_X), dtype=np.float32)
    if n == 0:
        return FeatureStream(t, F)
    iat = np.zeros(n, dtype=np.float32)
    iat[1:] = np.diff(t).astype(np.float32)
    F[:, 0] = iat
    F[:, 1] = [p.size for p in pkts]
    F[:, 2] = [shannon_entropy(p.payload) for p in pkts]
    F[1:, 3] = (iat[1:] <= BURST_IAT_S)
    F[:, 4] = [float(getattr(p, "direction", 0)) for p in pkts]
    return FeatureStream(t, F)

