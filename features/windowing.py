"""Bridge: FeatureStream → NJ-ODE tensors (values, mask, t_grid).

Owns standardization (mirrored into the model's x_mean/x_std buffers so
checkpoints carry the scaler — kills the preprocessing-drift bug class).
Collision policy per slot: bytes=sum, iat=min, entropy=max, burst=max.
Real time is normalized to the model's [0,1] horizon; window_s is a free
parameter (default 10 s → 10 ms effective slot resolution on a 0.01 grid).

Architectural Rule: ONE windowing implementation, TWO consumers.
  1. Windower: batch consumer for training and evaluation.
  2. LiveFeeder: streaming consumer for live diode tap / QR ingest with sliding stride.
Both route through aggregate_slots to eliminate train/serve skew.
"""
from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

import numpy as np
import torch

from features.extractor import BURST_IAT_S, D_X, FEATURE_NAMES, Packet, shannon_entropy

# Channel attribution heuristic mapping (rule mapping without supervised heads)
ATTRIBUTION_MAP = {
    0: ("iat", "beacon/recon"),
    1: ("bytes", "exfil-flood"),
    2: ("entropy", "tunnel/encrypted-c2"),
    3: ("burst", "exfil-flood"),
    4: ("direction", "volumetric-ddos"),
}


def aggregate_slots(t, F, t0, window_s, K, dt, mean=None, std=None) -> Tuple[np.ndarray, np.ndarray]:
    """Unified slot aggregation for both batch training and live streaming.

    Collision policy per slot:
      - slot 0 (iat): min (tightest inter-arrival gap)
      - slot 1 (bytes): sum (cumulative payload/header volume)
      - slot 2 (entropy): max (peak information surprise)
      - slot 3 (burst): max (micro-burst indicator active)
      - slot 4 (direction): majority rule (inbound >= 50% -> 1.0, else 0.0)

    Args:
        t: array-like of timestamps in seconds
        F: array-like of shape (N, d_x) with natural feature vectors
        t0: window start time in seconds
        window_s: window duration in seconds
        K: number of intervals in time grid (horizon / dt)
        dt: normalized grid step
        mean: optional numpy array of feature means
        std: optional numpy array of feature standard deviations

    Returns:
        values: (K + 1, d_x) float32 array (standardized if mean & std provided)
        mask: (K + 1,) boolean array of observed slot indicators
    """
    d_x = len(mean) if mean is not None else (F.shape[1] if hasattr(F, "shape") and len(F) > 0 else D_X)
    values = np.zeros((K + 1, d_x), dtype=np.float32)
    mask = np.zeros(K + 1, dtype=bool)

    if len(t) > 0:
        t_arr = np.asarray(t, dtype=np.float64)
        F_arr = np.asarray(F, dtype=np.float32)
        m = (t_arr >= t0) & (t_arr < t0 + window_s)
        if m.any():
            t_win, F_win = t_arr[m], F_arr[m]
            j = np.minimum(((t_win - t0) / window_s / dt).astype(np.int64), K)
            order = np.argsort(j, kind="stable")
            j, F_win = j[order], F_win[order]
            starts = np.flatnonzero(np.r_[True, j[1:] != j[:-1]])
            slots = j[starts]
            values[slots, 0] = np.minimum.reduceat(F_win[:, 0], starts)
            values[slots, 1] = np.add.reduceat(F_win[:, 1], starts)
            values[slots, 2] = np.maximum.reduceat(F_win[:, 2], starts)
            values[slots, 3] = np.maximum.reduceat(F_win[:, 3], starts)
            if F_win.shape[1] >= 5 and d_x >= 5:
                inbound = (F_win[:, 4] >= 0.5).astype(np.int32)
                inbound_counts = np.add.reduceat(inbound, starts)
                slot_counts = np.diff(np.r_[starts, len(F_win)])
                values[slots, 4] = (inbound_counts >= ((slot_counts + 1) // 2)).astype(np.float32)
            mask[slots] = True

    if mean is not None and std is not None:
        values = np.clip((values - mean) / std, -30.0, 30.0)  # bound deviations
        values[~mask] = 0.0

    return values, mask


class Windower:
    """Batch consumer: converts a FeatureStream into batched NJ-ODE tensors."""
    def __init__(self, model, window_s=10.0):
        self.model = model
        self.window_s = float(window_s)
        self.K, self.dt = model.K, model.dt     # grid geometry comes from the model
        self.mean_ = self.std_ = None

    @torch.no_grad()
    def fit_standardizer(self, *streams):
        """Fit on BENIGN data only (unsupervised — no labels to leak)."""
        X = np.concatenate([s.F for s in streams if len(s)], axis=0)
        self.mean_ = X.mean(0).astype(np.float32)
        self.std_ = np.maximum(X.std(0), 0.1).astype(np.float32)   # floor: no /1e-8 explosions
        self.model.x_mean.copy_(torch.tensor(self.mean_))
        self.model.x_std.copy_(torch.tensor(self.std_))
        return self.mean_, self.std_

    def _slot(self, stream, t0):
        return aggregate_slots(
            stream.t, stream.F, t0, self.window_s, self.K, self.dt,
            mean=self.mean_, std=self.std_
        )

    def windows(self, stream, stride_s=None):
        """Sliding windows → (values (N,K+1,4), mask (N,K+1) bool, t_grid (K+1,))."""
        if self.mean_ is None:
            if hasattr(self.model, "x_mean") and hasattr(self.model, "x_std"):
                self.mean_ = self.model.x_mean.cpu().numpy()
                self.std_ = self.model.x_std.cpu().numpy()
            else:
                raise RuntimeError("call fit_standardizer() before windows()")
        stride = self.window_s if stride_s is None else stride_s
        vals, masks = [], []
        if len(stream) == 0:
            return (torch.zeros((0, self.K + 1, D_X), dtype=torch.float32),
                    torch.zeros((0, self.K + 1), dtype=torch.bool),
                    torch.linspace(0.0, 1.0, self.K + 1, dtype=torch.float32))

        t0 = float(stream.t[0])
        while t0 < stream.t[-1]:
            v, m = self._slot(stream, t0)
            if m.any():
                vals.append(v)
                masks.append(m)
            t0 += stride

        if not vals:
            return (torch.zeros((0, self.K + 1, D_X), dtype=torch.float32),
                    torch.zeros((0, self.K + 1), dtype=torch.bool),
                    torch.linspace(0.0, 1.0, self.K + 1, dtype=torch.float32))

        return (torch.from_numpy(np.stack(vals)),
                torch.from_numpy(np.stack(masks)),
                torch.linspace(0.0, 1.0, self.K + 1, dtype=torch.float32))


import hashlib
import math
import struct
from collections import Counter


def compute_flow_hash(flow_key: bytes) -> int:
    """Hash flow key (e.g. 5-tuple) to a 16-bit uint."""
    if not flow_key:
        return 0
    digest = hashlib.md5(flow_key).digest()
    return struct.unpack(">H", digest[:2])[0]


@dataclass
class AlertEvent:
    """Standardized structured alert record emitted by LiveFeeder."""
    window_t0: float
    window_t1: float
    peak_score: float
    threshold: float
    is_anomaly: bool
    confirmed: bool
    confidence: float = 0.0
    severity: str = "LOW"
    threat_class: str = "calm-baseline"
    evidence: Optional[Dict] = None
    flow_ids: Optional[List[int]] = None
    attribution: Optional[Dict] = None
    ts: Optional[str] = None


class LiveFeeder:
    """Live streaming consumer for scanner side behind data diode / QR ingest.

    Eliminates train/serve skew by routing streaming ingestion through the exact same
    aggregate_slots collision logic as Windower.
    Evaluates sliding windows of width `window_s` with stride `stride_s` (default 2.0 s).
    Applies optional N-of-M hysteresis (default 2 of 3) to prevent dashboard flicker.
    Attaches flow evidence and calibrated confidence to each emitted alert.
    """
    def __init__(
        self,
        model,
        window_s: float = 10.0,
        stride_s: float = 2.0,
        hysteresis_n: int = 2,
        hysteresis_m: int = 3,
        device: str = "cpu",
    ):
        self.model = model
        self.window_s = float(window_s)
        self.stride_s = float(stride_s)
        self.K, self.dt = model.K, model.dt
        self.device = device
        self.hysteresis_n = hysteresis_n
        self.hysteresis_m = hysteresis_m

        # Read scaler from model buffers (checkpoint = full artifact)
        self.mean_ = model.x_mean.cpu().numpy()
        self.std_ = model.x_std.cpu().numpy()

        # Rolling buffers for feature events: [t, features], flow hashes
        self._t_buf: List[float] = []
        self._F_buf: List[np.ndarray] = []
        self._flow_buf: List[int] = []

        # Streaming state for raw packet ingestion
        self._last_pkt_t: Optional[float] = None

        # Window scheduling state
        self._first_t: Optional[float] = None
        self._next_window_end: Optional[float] = None

        # Hysteresis history deque of recent window anomaly decisions
        self._alert_history: deque = deque(maxlen=hysteresis_m)

    def reset(self):
        """Reset internal buffers and streaming state."""
        self._t_buf.clear()
        self._F_buf.clear()
        self._flow_buf.clear()
        self._last_pkt_t = None
        self._first_t = None
        self._next_window_end = None
        self._alert_history.clear()

    def ingest_feature_frame(self, t: float, features: np.ndarray, flow_hash: int = 0) -> List[AlertEvent]:
        """Ingest a pre-extracted feature frame (e.g. decoded from QR diode)."""
        t = float(t)
        f_vec = np.asarray(features, dtype=np.float32)
        if len(f_vec) < self.model.d_x:
            # Pad with 0.0 (e.g. direction bit if 4-dim passed to 5-dim model)
            f_vec = np.pad(f_vec, (0, self.model.d_x - len(f_vec)), "constant")
        elif len(f_vec) > self.model.d_x:
            f_vec = f_vec[:self.model.d_x]

        if self._first_t is None:
            self._first_t = t
            self._next_window_end = t + self.window_s

        self._t_buf.append(t)
        self._F_buf.append(f_vec)
        self._flow_buf.append(int(flow_hash))

        return self._evaluate_ready_windows(current_t=t)

    def ingest_packet(self, packet: Packet) -> List[AlertEvent]:
        """Ingest a raw Packet, computing streaming features."""
        t = float(packet.t)
        if self._last_pkt_t is None:
            iat = 0.0
            is_burst = 0.0
        else:
            iat = max(0.0, t - self._last_pkt_t)
            is_burst = 1.0 if iat <= BURST_IAT_S else 0.0
        self._last_pkt_t = t

        entropy = shannon_entropy(packet.payload)
        direction = float(getattr(packet, "direction", 0))
        flow_hash = compute_flow_hash(packet.flow_key) if getattr(packet, "flow_key", b"") else 0

        features = np.array([iat, packet.size, entropy, is_burst, direction], dtype=np.float32)
        if self.model.d_x == 4:
            features = features[:4]

        return self.ingest_feature_frame(t, features, flow_hash=flow_hash)

    def _prune_buffer(self, min_t: float):
        """Drop events strictly older than min_t to prevent unbounded buffer growth."""
        idx = 0
        while idx < len(self._t_buf) and self._t_buf[idx] < min_t:
            idx += 1
        if idx > 0:
            del self._t_buf[:idx]
            del self._F_buf[:idx]
            del self._flow_buf[:idx]

    def _evaluate_ready_windows(self, current_t: float) -> List[AlertEvent]:
        """Evaluate any windows that have elapsed up to current_t."""
        alerts: List[AlertEvent] = []
        if self._next_window_end is None:
            return alerts

        while current_t >= self._next_window_end:
            win_end = self._next_window_end
            win_start = win_end - self.window_s

            alert = self._score_window(win_start, win_end)
            alerts.append(alert)

            self._next_window_end += self.stride_s
            self._prune_buffer(self._next_window_end - self.window_s)

        return alerts

    def _score_window(self, t0: float, t1: float) -> AlertEvent:
        """Score a single [t0, t1] window using the shared aggregate_slots function."""
        values, mask = aggregate_slots(
            self._t_buf, self._F_buf, t0, self.window_s, self.K, self.dt,
            mean=self.mean_, std=self.std_
        )

        tau = float(self.model.threshold.item())

        if not mask.any():
            self._alert_history.append(False)
            return AlertEvent(
                window_t0=t0,
                window_t1=t1,
                peak_score=0.0,
                threshold=tau,
                is_anomaly=False,
                confirmed=False,
                confidence=0.0,
                severity="LOW",
                threat_class="calm-baseline",
                evidence=None,
                flow_ids=[],
                attribution=None,
            )

        v_t = torch.from_numpy(values).unsqueeze(0).to(self.device)
        m_t = torch.from_numpy(mask).unsqueeze(0).to(self.device)
        t_grid = torch.linspace(0.0, 1.0, self.K + 1, dtype=torch.float32).unsqueeze(0).to(self.device)

        self.model.eval()
        with torch.no_grad():
            _, s = self.model._sweep(v_t, m_t, t_grid, collect_scores=True)

        scores_valid = s[0, ~torch.isnan(s[0])]
        if len(scores_valid) == 0:
            peak_score = 0.0
        else:
            peak_score = float(scores_valid.max().item())

        is_anomaly = bool(peak_score > tau)
        self._alert_history.append(is_anomaly)
        confirmed = sum(self._alert_history) >= self.hysteresis_n

        # Calibrated confidence calculation
        confidence = self._compute_confidence(peak_score, tau)

        # Flow & Direction evidence layer
        m_win = [i for i, t in enumerate(self._t_buf) if t0 <= t <= t1 + 1e-5]
        w_flows = [self._flow_buf[i] if i < len(self._flow_buf) else 0 for i in m_win]
        w_F = [self._F_buf[i] for i in m_win]
        pkt_count = len(w_flows)

        flow_counts = Counter(w_flows)
        distinct_flows = len(flow_counts)
        if pkt_count > 0:
            probs = np.array(list(flow_counts.values()), dtype=np.float64) / pkt_count
            flow_entropy = float(-(probs * np.log2(probs + 1e-12)).sum())
        else:
            flow_entropy = 0.0

        out_bytes = sum(int(f[1]) for f in w_F if len(f) <= 4 or f[4] < 0.5)
        in_bytes = sum(int(f[1]) for f in w_F if len(f) > 4 and f[4] >= 0.5)
        byte_ratio = float(out_bytes / max(1.0, float(in_bytes))) if in_bytes > 0 else (100.0 if out_bytes > 0 else 1.0)
        top_flow_ids = [int(f) for f, _ in flow_counts.most_common(3)]

        evidence = {
            "distinct_flows": distinct_flows,
            "flow_entropy": round(flow_entropy, 3),
            "outbound_inbound_byte_ratio": round(byte_ratio, 3),
            "outbound_bytes": out_bytes,
            "inbound_bytes": in_bytes,
            "packet_count": pkt_count,
        }

        # Attribution & multi-threat classification
        attribution = None
        threat_class = "calm-baseline"
        if is_anomaly:
            attribution = self._attribute_window(v_t, m_t, t_grid, s)
            threat_class = self._classify_threat(attribution, evidence, w_F)
            attribution["threat_type"] = threat_class

        # Severity level assignment
        if not is_anomaly:
            severity = "LOW"
        elif confidence >= 0.95 or (peak_score > 3.0 * tau):
            severity = "CRITICAL"
        elif confidence >= 0.85 or (peak_score > 1.5 * tau):
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        return AlertEvent(
            window_t0=t0,
            window_t1=t1,
            peak_score=peak_score,
            threshold=tau,
            is_anomaly=is_anomaly,
            confirmed=confirmed,
            confidence=round(confidence, 4),
            severity=severity,
            threat_class=threat_class,
            evidence=evidence,
            flow_ids=top_flow_ids,
            attribution=attribution,
        )

    def _compute_confidence(self, peak_score: float, tau: float) -> float:
        """Compute principled, calibrated confidence score monotonic with peak anomaly score."""
        if peak_score <= 0.0:
            return 0.0
        if hasattr(self.model, "compute_confidence"):
            return float(self.model.compute_confidence(peak_score))

        if peak_score <= tau:
            return float(0.5 * (peak_score / max(1e-4, tau)))
        excess = (peak_score - tau) / max(1e-4, tau)
        return float(min(1.0, 0.5 + 0.5 * (1.0 - math.exp(-0.4 * excess))))

    def _classify_threat(self, attribution: Dict, evidence: Dict, w_F: List[np.ndarray]) -> str:
        """Map Bayesian channel attribution and window evidence to one of the 6 threat classes."""
        top_ch = attribution.get("top_channel", "unknown")
        distinct_flows = evidence.get("distinct_flows", 0)
        in_bytes = evidence.get("inbound_bytes", 0)
        out_bytes = evidence.get("outbound_bytes", 0)
        pkt_count = evidence.get("packet_count", 1)

        # 1. Volumetric / Protocol DDoS: inbound dominant or high source flow entropy with inbound bias
        if top_ch == "direction" or (in_bytes > out_bytes * 1.5 and distinct_flows > 20):
            return "ddos_flood"

        # 2. Reconnaissance / Port Scan: high distinct flow count with low average byte sizes
        avg_pkt_bytes = (out_bytes + in_bytes) / max(1, pkt_count)
        if distinct_flows > 20 and avg_pkt_bytes < 100:
            return "portscan"

        # 3. Data Exfiltration vs Encrypted TLS C2 vs Low/Slow C2
        max_size = max((int(f[1]) for f in w_F), default=0)
        max_ent = max((float(f[2]) for f in w_F), default=0.0)
        mean_ent = float(np.mean([f[2] for f in w_F])) if w_F else 0.0

        if top_ch in ("bytes", "burst"):
            if max_size < 1000 and max_ent >= 7.0:
                return "tls_c2"
            return "exfil_burst"

        # 4. Entropy-related or IAT-related anomalies: DGA Tunnel vs Encrypted TLS C2 vs C2 Beaconing
        if top_ch in ("entropy", "iat"):
            # TLS C2: fixed 512B frames with ciphertext entropy > 7.0
            if max_size >= 400 or max_ent >= 7.0:
                return "tls_c2"

            # DGA Tunnel: sustained high query entropy (mean entropy > 3.8 and many query packets)
            if mean_ent >= 3.8 and pkt_count >= 25:
                return "dga_tunnel"

            # C2 Beacon: periodic check-ins, smaller frame sizes, lower packet count
            return "c2_beacon"

        return attribution.get("threat_type", "unknown")

    @torch.no_grad()
    def _attribute_window(self, v_t, m_t, t_grid, s) -> Dict:
        """Unsupervised channel attribution heuristic across model features."""
        tau = float(self.model.threshold.item())
        scores_row = s[0]
        anom_mask = (scores_row > tau) & torch.isfinite(scores_row)
        if not anom_mask.any():
            anom_mask = torch.isfinite(scores_row)

        anom_indices = anom_mask.nonzero().flatten().tolist()
        if not anom_indices:
            peak_idx = int(torch.nan_to_num(scores_row, nan=float("-inf")).argmax().item())
            anom_indices = [peak_idx]

        B = 1
        h = torch.zeros(B, self.model.d_h, device=self.device)
        x_last = torch.zeros(B, self.model.d_x, device=self.device)
        t_last = torch.zeros(B, 1, device=self.device)
        t_flat = t_grid[0]

        cum_channel_errs = np.zeros(self.model.d_x, dtype=np.float32)
        last_idx = max(anom_indices)

        for j in range(last_idx + 1):
            obs = m_t[:, j]
            if obs.any():
                x = v_t[:, j]
                y_minus = self.model.outputNN(h)
                if j in anom_indices:
                    diff_sq = ((x[0] - y_minus[0]) ** 2).detach().cpu().numpy()
                    cum_channel_errs += diff_sq

                h_new = self.model.jumpNN(x)
                upd = obs.unsqueeze(-1)
                h = torch.where(upd, h_new, h)
                x_last = torch.where(upd, x, x_last)
                t_last = torch.where(upd, t_flat[j].view(1, 1), t_last)

            if j < self.model.K:
                delta = t_flat[j] - t_last
                h = h + self.model.dt * self.model.f(h, x_last, t_last, delta)

        top_idx = int(np.argmax(cum_channel_errs))
        feature_names = FEATURE_NAMES[:self.model.d_x]
        channel_name, threat_type = ATTRIBUTION_MAP.get(top_idx, ("unknown", "unknown"))

        return {
            "top_channel": channel_name,
            "threat_type": threat_type,
            "channel_errors": {
                name: float(cum_channel_errs[i]) for i, name in enumerate(feature_names)
            },
        }

    def flush(self) -> List[AlertEvent]:
        """Flush and score any pending events in the buffer as a final window."""
        if not self._t_buf or self._first_t is None:
            return []
        win_end = self._t_buf[-1] + 1e-5
        win_start = max(self._first_t, win_end - self.window_s)
        return [self._score_window(win_start, win_end)]

    def feed_stream(self, stream) -> Iterator[AlertEvent]:
        """Stream consumer: feeds an entire FeatureStream yielding AlertEvents."""
        self.reset()
        emitted = False
        for t, f in zip(stream.t, stream.F):
            for alert in self.ingest_feature_frame(t, f):
                emitted = True
                yield alert
        if not emitted and len(self._t_buf) > 0:
            for alert in self.flush():
                yield alert



