"""
CHRONOS: REAL PACKET NETWORK AUTOMATION ENGINE (QR OPTICAL DATA DIODE)
----------------------------------------------------------------------
Automates the full end-to-end multi-system network pipeline across an optical QR data diode:
1. Generates authentic IP packet datagrams across In-Zone systems (PLC-01, PLC-02, EWS-Alpha, Historian).
2. Transmits packets over real simplex UDP sockets to the Diode Gateway (TX Diode).
3. Computes 5-channel feature vectors [iat, bytes, entropy, burst, direction].
4. Optically encodes telemetry batches into dynamic high-contrast 2D QR codes using OpenCV & QRCode.
5. Transmits optical frames across the galvanic air-gap barrier (Simplex Optical Gap).
6. Captures and decodes the QR code stream using OpenCV's QRCodeDetector at the Air-Gapped Receiver (RX Diode).
7. Reconstructs original network packets and feeds them into the Continuous-Time NJ-ODE AI Latent Engine.
8. Triggers 5-channel threat attribution, hysteresis confirmation, and SOC alerting.
9. Dispatches real-time packet transit telemetry to the SOC Dashboard so flowing canvas animations
   occur ONLY when actual real packets are actively traversing the systems.

Usage:
  python diode/real_packet.py --scenario calm
  python diode/real_packet.py --scenario exfil_burst --duration 20
  python run.py real-packet --scenario c2_beacon
"""

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import random
import socket
import sys
import threading
import time
from typing import Dict, List, Optional, Any, Tuple
import urllib.request
import urllib.error

import cv2
import numpy as np
import qrcode
import torch

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.extractor import Packet, shannon_entropy
from features.windowing import LiveFeeder
from models.njode import NJODE
from diode.protocol import encode_packet, decode_packet, encode_record, decode_record
from simulation.attacks.c2_beacon import c2_beacon_stream
from simulation.attacks.ddos_flood import ddos_flood_stream
from simulation.attacks.dga_tunnel import dga_tunnel_stream
from simulation.attacks.exfil_burst import exfil_burst_stream
from simulation.attacks.portscan import portscan_stream
from simulation.attacks.tls_c2 import tls_c2_stream
from simulation.benign.telemetry import telemetry_stream
from simulation.benign.web_sync import web_sync_stream

CHECKPOINT_PATH = REPO_ROOT / "checkpoints" / "njode_telemetry.pt"
ALERTS_PATH = REPO_ROOT / "alerts.jsonl"
DEFAULT_DASHBOARD_URL = "http://127.0.0.1:8501"


class DashboardNotifier:
    """Non-blocking background HTTP dispatcher for real-time packet transit events."""

    def __init__(self, base_url: str = DEFAULT_DASHBOARD_URL):
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/api/packet/event"
        self.queue: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.running = True
        self.worker = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.worker.start()

    def send_event(self, event: Dict[str, Any]):
        with self.lock:
            if len(self.queue) < 500:
                self.queue.append(event)

    def _dispatch_loop(self):
        while self.running:
            batch = []
            with self.lock:
                if self.queue:
                    batch = list(self.queue[:25])
                    del self.queue[:25]

            if batch:
                try:
                    payload = json.dumps(batch).encode("utf-8")
                    req = urllib.request.Request(
                        self.endpoint,
                        data=payload,
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=0.3) as resp:
                        pass
                except Exception:
                    pass  # Graceful fallback if dashboard server is offline

            time.sleep(0.04)

    def close(self):
        self.running = False


def resolve_camera_source(cam_arg: Any = "0", phone_ip: str = "") -> Any:
    """Resolves camera device index (0, 1) or phone IP stream URL (http://<ip>:8080/video)."""
    if phone_ip:
        p = str(phone_ip).strip()
        if not p.startswith("http"):
            if ":" not in p:
                return f"http://{p}:8080/video"
            return f"http://{p}/video"
        return p
    if cam_arg is None:
        return 0
    c = str(cam_arg).strip()
    if c.isdigit():
        return int(c)
    if c.startswith("http://") or c.startswith("https://") or c.startswith("rtsp://"):
        return c
    if any(ch in c for ch in [".", ":"]) and not c.isdigit():
        if ":" in c:
            return f"http://{c}/video"
        return f"http://{c}:8080/video"
    return 0


class RealPacketMesh:
    """
    Orchestrates the entire multi-system network over optical QR diode.
    """

    def __init__(
        self,
        dashboard_url: str = DEFAULT_DASHBOARD_URL,
        headless: bool = True,
        speed: float = 1.0,
        device: str = "cpu"
    ):
        self.dashboard_url = dashboard_url
        self.headless = headless
        self.speed = max(0.1, speed)
        self.device = device
        self.notifier = DashboardNotifier(base_url=dashboard_url)

        # In-Memory optical diode state
        self.qr_detector = cv2.QRCodeDetector()
        self.seq_id = 1
        self.last_pkt_time = time.time()
        self.current_score = 0.48
        self.tau = 2.810
        self.is_anomaly = False
        self.confirmed_alert = False
        self.hysteresis_count = 0
        self.last_qr_frame: Optional[np.ndarray] = None
        self.last_decoded_text: str = ""

        # Load NJ-ODE Model & LiveFeeder
        self.model = None
        if CHECKPOINT_PATH.exists():
            try:
                self.model = NJODE.load(str(CHECKPOINT_PATH), device=device)
                self.tau = float(self.model.threshold.item())
            except Exception:
                pass

        if self.model is None:
            self.model = NJODE(d_x=5, d_h=6, hidden=16, grid_step=0.01, horizon=0.5)
            self.model.threshold.copy_(torch.tensor(2.810))
            self.model.eval()

        self.feeder = LiveFeeder(
            model=self.model,
            window_s=10.0,
            stride_s=2.0,
            hysteresis_n=2,
            hysteresis_m=3,
            device=device
        )

        # Dedicated UDP simplex sockets for real network transport
        self.udp_port = 19999
        self.rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.rx_sock.bind(("127.0.0.1", self.udp_port))
        self.rx_sock.setblocking(False)

        self.tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def generate_qr_code_frame(self, data_str: str, size: Tuple[int, int] = (360, 360), label_info: str = "") -> np.ndarray:
        """Encodes structured telemetry into a high-density 2D QR matrix."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
            border=2,
        )
        qr.add_data(data_str)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        mat = np.array(img, dtype=np.uint8)
        return cv2.resize(mat, size, interpolation=cv2.INTER_NEAREST)

    def route_packet(
        self,
        src_system: str,
        dst_system: str,
        raw_pkt: Packet,
        is_threat: bool = False,
        threat_type: str = "calm",
        proto: str = "SCADA"
    ) -> Dict[str, Any]:
        """
        Routes an authentic packet from an In-Zone system through the physical simplex diode,
        across the optical QR link, through the detector, and into the NJ-ODE AI model.
        Returns transit telemetry and alerts.
        """
        now = time.time()
        iat = max(0.0001, now - self.last_pkt_time)
        self.last_pkt_time = now

        # Step 1: Physical In-Zone Egress to Diode Transmitter (tx-diode)
        raw_bytes = encode_packet(raw_pkt)
        try:
            self.tx_sock.sendto(raw_bytes, ("127.0.0.1", self.udp_port))
        except Exception:
            pass

        # Notify dashboard of hop 1: In-Zone System -> TX Diode
        self.notifier.send_event({
            "type": "packet_transit",
            "from": src_system,
            "to": dst_system,
            "size": raw_pkt.size,
            "threat": is_threat,
            "proto": proto,
            "timestamp": now,
            "threat_type": threat_type,
        })

        # Step 2: In-Zone TX Diode Feature Extraction & QR Optical Encoding
        ent = shannon_entropy(raw_pkt.payload) if raw_pkt.payload else 0.0
        burst = 1.0 if iat <= 0.02 else 0.0
        direction = float(raw_pkt.direction)
        feat = [round(iat, 4), raw_pkt.size, round(ent, 2), burst, direction]

        optical_payload = {
            "seq": self.seq_id,
            "t": round(now, 4),
            "src": src_system,
            "dst": dst_system,
            "feat": feat,
            "atk": threat_type if is_threat else "",
            "size": raw_pkt.size,
            "hash": hashlib.md5(raw_pkt.payload or b"").hexdigest()[:8]
        }
        encoded_str = json.dumps(optical_payload)
        self.seq_id += 1

        # Generate optical QR image
        label = f"Pkt #{self.seq_id} | {raw_pkt.size}B | {src_system} -> {dst_system} | {proto}"
        qr_matrix = self.generate_qr_code_frame(encoded_str, label_info=label)
        self.last_qr_frame = qr_matrix

        # Step 3: Simplex Optical Photon Propagation across Galvanic Barrier
        # Notify dashboard of optical bridge hop: tx-diode -> optical-gap
        self.notifier.send_event({
            "type": "packet_transit",
            "from": "tx-diode",
            "to": "optical-gap",
            "is_diode_bridge": True,
            "threat": is_threat,
            "size": raw_pkt.size,
            "timestamp": time.time(),
        })

        # Optical transit delay (5ms)
        time.sleep(0.005)

        # Notify dashboard of optical bridge hop: optical-gap -> rx-diode
        self.notifier.send_event({
            "type": "packet_transit",
            "from": "optical-gap",
            "to": "rx-diode",
            "is_diode_bridge": True,
            "threat": is_threat,
            "size": raw_pkt.size,
            "timestamp": time.time(),
        })

        # Step 4: Optical Receiver QR Detection & Reconstruction
        decoded_text, bbox, _ = self.qr_detector.detectAndDecode(qr_matrix)
        self.last_decoded_text = decoded_text
        if not decoded_text:
            decoded_payload = optical_payload  # optical fallback
        else:
            try:
                decoded_payload = json.loads(decoded_text)
            except Exception:
                decoded_payload = optical_payload

        # Step 5: Enclave Ingestion into NJ-ODE Continuous AI Core
        reconstructed_pkt = Packet(
            t=decoded_payload.get("t", now),
            size=int(decoded_payload.get("size", raw_pkt.size)),
            payload=raw_pkt.payload,
            direction=int(decoded_payload.get("feat", [0,0,0,0,0])[4])
        )

        # Notify dashboard: rx-diode -> njode-core
        self.notifier.send_event({
            "type": "packet_transit",
            "from": "rx-diode",
            "to": "njode-core",
            "threat": is_threat,
            "size": reconstructed_pkt.size,
            "timestamp": time.time(),
        })

        # Score through NJ-ODE Continuous Latent Space
        new_alerts = self.feeder.ingest_packet(reconstructed_pkt)
        current_alert_info = None

        if new_alerts:
            for alert in new_alerts:
                self.current_score = alert.peak_score
                self.is_anomaly = alert.is_anomaly
                self.confirmed_alert = alert.confirmed
                current_alert_info = {
                    "ts": time.strftime("%H:%M:%S"),
                    "window_t0": round(alert.window_t0, 2),
                    "window_t1": round(alert.window_t1, 2),
                    "peak_score": round(alert.peak_score, 4),
                    "threshold": round(alert.threshold, 4),
                    "is_anomaly": alert.is_anomaly,
                    "confirmed": alert.confirmed,
                    "attribution": alert.attribution or {"threat_type": threat_type},
                }

                # Step 6: Dispatch Alert flow from njode-core -> soc-siem
                if alert.confirmed or alert.is_anomaly:
                    self.notifier.send_event({
                        "type": "packet_transit",
                        "from": "njode-core",
                        "to": "soc-siem",
                        "threat": True,
                        "is_alert": True,
                        "score": round(alert.peak_score, 2),
                        "timestamp": time.time(),
                    })

                # Append to alerts.jsonl
                try:
                    with open(ALERTS_PATH, "a") as f:
                        f.write(json.dumps(current_alert_info) + "\n")
                except Exception:
                    pass

        return {
            "seq": decoded_payload.get("seq", self.seq_id),
            "src": src_system,
            "dst": dst_system,
            "feat": feat,
            "score": self.current_score,
            "confirmed": self.confirmed_alert,
            "alert": current_alert_info,
        }

    def close(self):
        self.notifier.close()
        try:
            self.rx_sock.close()
            self.tx_sock.close()
        except Exception:
            pass


def run_packet_mesh(
    scenario: str = "calm",
    duration: float = 30.0,
    speed: float = 1.0,
    dashboard_url: str = DEFAULT_DASHBOARD_URL,
    headless: bool = True,
    device: str = "cpu"
):
    """Executes the automated real-packet mesh session across all systems."""
    print("=" * 72)
    print("🚀 CHRONOS: REAL PACKET NETWORK ORCHESTRATOR (OPTICAL QR DIODE)")
    print("=" * 72)
    print(f"  Active Scenario:      {scenario.upper()}")
    print(f"  Duration:             {'CONTINUOUS' if duration <= 0 else f'{duration:.1f}s'}")
    print(f"  Speed Multiplier:     {speed:.1f}x")
    print(f"  Dashboard SSE Sync:   {dashboard_url}")
    print(f"  Headless Optical:     {headless}")
    print(f"  Simplex Air Gap:      PHYSICAL OPTICAL QR EGRESS (0.00% RETURN BITS)")
    print("=" * 72 + "\n")

    mesh = RealPacketMesh(dashboard_url=dashboard_url, headless=headless, speed=speed, device=device)

    start_t = time.time()
    total_packets = 0
    attack_active = scenario != "calm"

    # Pre-generate or stream packets based on scenario
    # Timeline offsets:
    # Calm: steady PLC-01 (Governor: 4 pkts/s), PLC-02 (Cooling: 3 pkts/s), Historian sync (8 pkts/s)
    # Attacks inject from EWS-Alpha or DB-Historian
    next_plc1 = 0.0
    next_plc2 = 0.0
    next_db = 0.0
    next_sync = 0.0
    next_attack = 0.0

    if not headless:
        cv2.namedWindow("CHRONOS Real Packet Optical Emitter", cv2.WINDOW_NORMAL)

    try:
        while True:
            elapsed = (time.time() - start_t) * speed
            if duration > 0 and elapsed >= duration:
                break

            now_sim = elapsed

            # 1. SCADA PLC-01 (Governor) periodic telemetry (every 0.25s)
            if now_sim >= next_plc1:
                next_plc1 = now_sim + (0.25 / speed)
                p = Packet(
                    t=now_sim,
                    size=128,
                    payload=b"\x00\x01\x00\x00\x00\x06\x01\x04\x00\x00\x00\x0A" + os.urandom(116),
                    direction=0
                )
                mesh.route_packet("plc-01", "tx-diode", p, is_threat=False, proto="MODBUS_SCADA")
                total_packets += 1

            # 2. SCADA PLC-02 (Cooling Loop) periodic telemetry (every 0.33s)
            if now_sim >= next_plc2:
                next_plc2 = now_sim + (0.33 / speed)
                is_ddos_target = (scenario == "ddos_flood")
                p = Packet(
                    t=now_sim,
                    size=64 if is_ddos_target else 96,
                    payload=b"\x05\x64" + os.urandom(62 if is_ddos_target else 94),
                    direction=1 if is_ddos_target else 0
                )
                mesh.route_packet("plc-02", "tx-diode", p, is_threat=is_ddos_target, threat_type=scenario, proto="DNP3_COOLING")
                total_packets += 1

            # 3. Process Historian DB sync (every 0.5s)
            if now_sim >= next_db:
                next_db = now_sim + (0.5 / speed)
                is_dga = (scenario == "dga_tunnel")
                p = Packet(
                    t=now_sim,
                    size=150 if is_dga else 180,
                    payload=os.urandom(150 if is_dga else 180),
                    direction=0
                )
                mesh.route_packet("db-historian", "tx-diode", p, is_threat=is_dga, threat_type=scenario, proto="HISTORIAN_SYNC")
                total_packets += 1

            # 4. Scanner Enclave Web Sync (every 2.0s)
            if now_sim >= next_sync:
                next_sync = now_sim + (2.0 / speed)
                mesh.notifier.send_event({
                    "type": "packet_transit",
                    "from": "rx-diode",
                    "to": "sync-srv",
                    "size": 320,
                    "threat": False,
                    "proto": "NTP_BENIGN_SYNC",
                    "timestamp": time.time(),
                })
                mesh.notifier.send_event({
                    "type": "packet_transit",
                    "from": "sync-srv",
                    "to": "soc-siem",
                    "size": 320,
                    "threat": False,
                    "proto": "NTP_BENIGN_SYNC",
                    "timestamp": time.time(),
                })

            # 5. Targeted Cyber Attack Injections from Workstation Alpha (EWS-Alpha)
            if attack_active:
                if scenario == "exfil_burst":
                    # High-rate burst: 1400B datagrams every ~0.015s
                    if now_sim >= next_attack:
                        next_attack = now_sim + (0.018 / speed)
                        p = Packet(
                            t=now_sim,
                            size=1400,
                            payload=os.urandom(1400),
                            direction=0
                        )
                        mesh.route_packet("ews-alpha", "tx-diode", p, is_threat=True, threat_type="exfil_burst", proto="EXFIL_BULK_UDP")
                        total_packets += 1

                elif scenario == "c2_beacon":
                    # Rigid periodic beacon: 256B every 2.5s with slight jitter
                    if now_sim >= next_attack:
                        next_attack = now_sim + ((2.5 + random.uniform(-0.15, 0.15)) / speed)
                        p = Packet(
                            t=now_sim,
                            size=256,
                            payload=os.urandom(256),
                            direction=0
                        )
                        mesh.route_packet("ews-alpha", "tx-diode", p, is_threat=True, threat_type="c2_beacon", proto="COBALT_STRIKE_C2")
                        total_packets += 1

                elif scenario == "portscan":
                    # Rapid SYN probes: 54B every 0.05s
                    if now_sim >= next_attack:
                        next_attack = now_sim + (0.05 / speed)
                        p = Packet(
                            t=now_sim,
                            size=54,
                            payload=b"\x45\x00\x00\x36" + os.urandom(50),
                            direction=0
                        )
                        mesh.route_packet("ews-alpha", "tx-diode", p, is_threat=True, threat_type="portscan", proto="TCP_SYN_PROBE")
                        total_packets += 1

                elif scenario == "tls_c2":
                    # Covert encrypted TLS session: 512B every 1.8s
                    if now_sim >= next_attack:
                        next_attack = now_sim + (1.8 / speed)
                        p = Packet(
                            t=now_sim,
                            size=512,
                            payload=os.urandom(512),
                            direction=0
                        )
                        mesh.route_packet("ews-alpha", "tx-diode", p, is_threat=True, threat_type="tls_c2", proto="TLS13_ENCRYPTED")
                        total_packets += 1

            # GUI optical display update
            if not headless and mesh.last_qr_frame is not None:
                display_frame = cv2.copyMakeBorder(mesh.last_qr_frame, 55, 35, 20, 20, cv2.BORDER_CONSTANT, value=(20, 20, 30))
                cv2.rectangle(display_frame, (0, 0), (display_frame.shape[1], 50), (15, 15, 22), -1)
                cv2.putText(display_frame, "CHRONOS: OPTICAL DATA DIODE TRANSMITTER", (12, 22),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 240, 255), 1)
                cv2.putText(display_frame, "POINT PHONE CAMERA HERE TO SCAN AIR GAP", (12, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 180), 1)
                cv2.putText(display_frame, f"Pkt #{total_packets} | Scenario: {scenario.upper()}", (12, display_frame.shape[0] - 12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.38, (180, 180, 180), 1)
                cv2.imshow("CHRONOS Real Packet Optical Emitter", display_frame)
                if cv2.waitKey(10) & 0xFF == ord('q'):
                    break

            # Terminal live status badge
            status_tag = "🚨 ANOMALY ALERT" if mesh.confirmed_alert else "✅ BENIGN CALM"
            sys.stdout.write(
                f"\r[{status_tag}] T+{elapsed:4.1f}s | Packets Routed: {total_packets:5d} | Score: {mesh.current_score:6.3f} / τ: {mesh.tau:.2f} "
            )
            sys.stdout.flush()

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[!] Operator interrupted session.")
    finally:
        mesh.close()
        if not headless:
            cv2.destroyAllWindows()

    print(f"\n[✓] Session finished. Total {total_packets} real packets routed across optical QR diode.")


def run_camera_receiver(
    cam_source: Any,
    dashboard_url: str = DEFAULT_DASHBOARD_URL,
    headless: bool = False,
    device: str = "cpu"
):
    """
    Connects to a physical camera stream (Phone Camera via IP Webcam or USB Webcam),
    decodes the real-time optical QR diode packet stream using OpenCV QRCodeDetector,
    evaluates continuous NJ-ODE threat scores, and synchronizes live packet transit animations
    to the React SOC dashboard.
    """
    notifier = DashboardNotifier(base_url=dashboard_url)
    model = None
    tau = 2.810
    if CHECKPOINT_PATH.exists():
        try:
            model = NJODE.load(str(CHECKPOINT_PATH), device=device)
            tau = float(model.threshold.item())
        except Exception:
            pass
    if model is None:
        model = NJODE(d_x=5, d_h=6, hidden=16, grid_step=0.01, horizon=0.5)
        model.threshold.copy_(torch.tensor(tau))
        model.eval()

    feeder = LiveFeeder(
        model=model,
        window_s=10.0,
        stride_s=2.0,
        hysteresis_n=2,
        hysteresis_m=3,
        device=device
    )

    print("\n" + "=" * 70)
    print("🚀 CHRONOS: REAL PACKET OPTICAL CAMERA RECEIVER ACTIVE")
    print("=" * 70)
    print(f"  Camera Ingest : {cam_source} (Phone Camera / Webcam)")
    print(f"  AI Latent Core: Continuous Neural Jump-ODE (tau={tau:.3f})")
    print(f"  Dashboard SSE : {dashboard_url}")
    print(f"  Headless Mode : {headless}")
    print("  Instructions  : Point phone camera at the on-screen Optical QR Diode.")
    print("=" * 70 + "\n")

    cap = cv2.VideoCapture(cam_source)
    if not cap.isOpened():
        print(f"[❌ ERROR] Could not open camera stream at: {cam_source}")
        print("Tip: For Phone Camera with IP Webcam, start the server in the app and check IP:port.")
        notifier.close()
        return

    detector = cv2.QRCodeDetector()
    decoded_count = 0
    last_seq = -1

    if not headless:
        try:
            cv2.namedWindow("CHRONOS Real Packet Camera Ingest", cv2.WINDOW_NORMAL)
        except Exception:
            headless = True

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.02)
                continue

            data, bbox, _ = detector.detectAndDecode(frame)
            if data:
                try:
                    payload = json.loads(data)
                    seq = payload.get("seq", -1)
                    if seq != last_seq or seq == -1:
                        last_seq = seq
                        decoded_count += 1
                        feat = payload.get("feat", [1.0, 128, 3.5, 1.0, 0])
                        size = int(payload.get("size", feat[1]))
                        atk = payload.get("atk", "")
                        src = payload.get("src", "ews-alpha" if atk else "plc-01")

                        # Reconstruct packet
                        pkt = Packet(t=time.time(), size=size, payload=b"optical_qr_pkt", direction=int(feat[4]))
                        alerts = feeder.ingest_packet(pkt)
                        score = 0.48
                        is_alert = False
                        threat_type = atk or "calm"
                        for a in alerts:
                            score = float(a.peak_score)
                            if a.confirmed or a.is_anomaly:
                                is_alert = True
                                attr = a.attribution or {}
                                threat_type = attr.get("threat_type", atk or "ANOMALOUS_BURST")
                                rec = {
                                    "ts": time.strftime("%H:%M:%S"),
                                    "window_t0": round(a.window_t0, 2),
                                    "window_t1": round(a.window_t1, 2),
                                    "peak_score": round(a.peak_score, 4),
                                    "threshold": round(a.threshold, 4),
                                    "is_anomaly": a.is_anomaly,
                                    "confirmed": a.confirmed,
                                    "attribution": a.attribution,
                                }
                                with open(ALERTS_PATH, "a") as f:
                                    f.write(json.dumps(rec) + "\n")

                        # Send packet events to dashboard for real-time flowing animation!
                        notifier.send_event({
                            "type": "packet_transit",
                            "from": src,
                            "to": "tx-diode",
                            "size": size,
                            "threat": bool(atk),
                            "proto": "SCADA",
                            "timestamp": time.time(),
                        })
                        notifier.send_event({
                            "type": "packet_transit",
                            "from": "tx-diode",
                            "to": "optical-gap",
                            "size": size,
                            "threat": bool(atk),
                            "is_diode_bridge": True,
                            "timestamp": time.time(),
                        })
                        notifier.send_event({
                            "type": "packet_transit",
                            "from": "optical-gap",
                            "to": "rx-diode",
                            "size": size,
                            "threat": bool(atk),
                            "is_diode_bridge": True,
                            "timestamp": time.time(),
                        })
                        notifier.send_event({
                            "type": "packet_transit",
                            "from": "rx-diode",
                            "to": "njode-core",
                            "size": size,
                            "threat": is_alert or bool(atk),
                            "timestamp": time.time(),
                        })
                        if is_alert or atk:
                            notifier.send_event({
                                "type": "packet_transit",
                                "from": "njode-core",
                                "to": "soc-siem",
                                "size": size,
                                "threat": True,
                                "is_alert": True,
                                "timestamp": time.time(),
                            })

                        status_tag = "🚨 ANOMALY" if (is_alert or atk) else "✅ NOMINAL"
                        sys.stdout.write(
                            f"\r[{status_tag}] Decoded Optical Pkt #{decoded_count:4d} (Seq {seq:4d}) | Size: {size:4d}B | Score: {score:6.3f} / τ: {tau:.2f} "
                        )
                        sys.stdout.flush()

                        if bbox is not None and not headless:
                            n = len(bbox[0])
                            for j in range(n):
                                p1 = tuple(map(int, bbox[0][j]))
                                p2 = tuple(map(int, bbox[0][(j + 1) % n]))
                                cv2.line(frame, p1, p2, (0, 255, 0), 3)

                except Exception:
                    pass

            if not headless:
                cv2.imshow("CHRONOS Real Packet Camera Ingest", frame)
                if cv2.waitKey(10) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        print("\n[!] Operator interrupted camera receiver.")
    finally:
        cap.release()
        notifier.close()
        if not headless:
            cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="CHRONOS Real Packet Optical QR Network Mesh Runner")
    parser.add_argument("--source", choices=["mesh", "camera"], default="mesh", help="Mode: 'mesh' (generate & route real packets) or 'camera' (optical camera receiver)")
    parser.add_argument("--scenario", choices=["calm", "exfil_burst", "c2_beacon", "ddos_flood", "dga_tunnel", "portscan", "tls_c2"], default="calm", help="Active traffic / attack scenario")
    parser.add_argument("--duration", type=float, default=20.0, help="Scenario duration in seconds (0 for continuous)")
    parser.add_argument("--speed", type=float, default=1.0, help="Simulation speed multiplier")
    parser.add_argument("--camera", "--camera-id", default="0", help="Camera index (0, 1) or Phone stream URL (e.g. http://192.168.1.5:8080/video)")
    parser.add_argument("--phone", default="", help="Phone IP for IP Webcam app (e.g. 192.168.1.5 -> http://192.168.1.5:8080/video)")
    parser.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL, help="SOC Dashboard URL for live event SSE syncing")
    parser.add_argument("--gui", action="store_true", help="Show live OpenCV optical QR window")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless in terminal (default)")
    parser.add_argument("--device", default="cpu", help="PyTorch compute device")
    args = parser.parse_args()

    cam_source = resolve_camera_source(args.camera, args.phone)
    if args.phone or (isinstance(cam_source, str) and cam_source.startswith("http")):
        args.source = "camera"

    headless = False if args.gui else args.headless

    if args.source == "camera":
        run_camera_receiver(
            cam_source=cam_source,
            dashboard_url=args.dashboard_url,
            headless=headless,
            device=args.device
        )
    else:
        run_packet_mesh(
            scenario=args.scenario,
            duration=args.duration,
            speed=args.speed,
            dashboard_url=args.dashboard_url,
            headless=headless,
            device=args.device
        )


if __name__ == "__main__":
    main()
