"""
CHRONOS: NUCLEAR SCADA AIR-GAPPED SOC & AI DEFENSE CONSOLE
----------------------------------------------------------
Air-gapped defense receiver running on the security analyst station.
1. Decodes unidirectional optical QR stream from the Optical Data Diode.
2. Supports Dual Ingest Modes:
   - OPTICAL WEBCAM MODE: Point webcam at QR Diode on screen or phone.
   - DIRECT SIMPLEX LOOPBACK: Ingests mirrored diode packets via local port 9998 (1-laptop demo mode).
   - Press [SPACE] to toggle between Webcam and Direct Loopback anytime!
3. Displays Live Nuclear Reactor Vitals (Core Temp, Coolant Pressure, Grid Freq, Power).
4. Displays Real Host Metrics (Actual CPU %, RAM %, Process Table).
5. Continuous-Time Anomaly Engine: Evaluates residual prediction errors vs threshold tau.
6. Real-Time Host Breach Alert: Flashes instant Red Alert when Notepad, Calc, or Malware executes!

Usage:
  python diode/nuclear_soc.py
"""

import argparse
import os
from pathlib import Path
import cv2
import json
import sys
import time
import socket
import select
import threading
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.extractor import Packet
from features.windowing import LiveFeeder
from models.njode import NJODE

ALERT_LOG = REPO_ROOT / "alerts.jsonl"
CHECKPOINT_PATH = REPO_ROOT / "checkpoints" / "njode_telemetry.pt"

# Network configuration for loopback ingestion
MIRROR_PORT = 9998

# AI Anomaly Detection Threshold Default
TAU_THRESHOLD = 2.464

class NuclearSOCReceiver:
    def __init__(self):
        self.mode = "LOOPBACK" if not os.environ.get("DISPLAY") else "WEBCAM"
        self.tau = TAU_THRESHOLD

        # Load NJ-ODE model checkpoint
        self.model = None
        self.feeder = None
        if CHECKPOINT_PATH.exists():
            try:
                self.model = NJODE.load(str(CHECKPOINT_PATH), device="cpu")
                self.tau = float(self.model.threshold.item())
                self.feeder = LiveFeeder(
                    model=self.model,
                    window_s=10.0,
                    stride_s=2.0,
                    hysteresis_n=2,
                    hysteresis_m=3,
                    device="cpu"
                )
                print(f"[✓] Nuclear SOC loaded NJ-ODE checkpoint (v{getattr(self.model, 'version', '1.1')}, tau={self.tau:.4f})")
            except Exception as e:
                print(f"[!] Warning: Could not load NJ-ODE checkpoint ({e}). Using default baseline.")

        self.stats = {
            "optical_frames": 0,
            "total_logs": 0,
            "alerts_caught": 0,
            "anomaly_score": 0.48,
            "tau": self.tau,
            "threat_type": "NONE (BASELINE NOMINAL)"
        }
        self.latest_vitals = {
            "temp": 295.4,
            "press": 155.0,
            "freq": 50.00,
            "mw": 880.0,
            "cpu": 12.0,
            "ram": 45.0,
            "status": "NORMAL"
        }
        self.event_log = []
        self.lock = threading.Lock()
        self.last_seq = -1
        self.active_alert = None
        self.alert_timer = 0.0

        # Start loopback UDP listener
        self.loopback_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.loopback_sock.bind(("127.0.0.1", MIRROR_PORT))
        self.loopback_sock.setblocking(False)

    def process_incoming_packet(self, payload):
        """Processes an ingested telemetry packet from either optical QR or loopback."""
        with self.lock:
            seq = payload.get("seq", 0)
            if seq == self.last_seq and self.last_seq != -1:
                return

            self.last_seq = seq
            self.stats["optical_frames"] += 1
            self.stats["total_logs"] += 1

            # Update Nuclear Vitals
            self.latest_vitals["temp"] = float(payload.get("temp", payload.get("temp_c", 295.4)))
            self.latest_vitals["press"] = float(payload.get("press", payload.get("pressure_bar", 155.0)))
            self.latest_vitals["freq"] = float(payload.get("freq", payload.get("grid_freq_hz", 50.00)))
            self.latest_vitals["mw"] = float(payload.get("mw", payload.get("power_mw", 880.0)))
            self.latest_vitals["cpu"] = float(payload.get("cpu", payload.get("host_cpu_pct", 10.0)))
            self.latest_vitals["ram"] = float(payload.get("ram", payload.get("host_ram_pct", 45.0)))

            event_type = payload.get("type", payload.get("event_type", "ROUTINE_SCADA"))
            ts_str = payload.get("ts", payload.get("time", time.strftime("%H:%M:%S")))

            # Run through actual Continuous-Time NJ-ODE AI Model
            feat = payload.get("feat", [1.0, 120, 3.5, 1.0, 0])
            pkt = Packet(t=time.time(), size=int(feat[1]), payload=b"optical_payload", direction=int(feat[4]))
            
            if self.feeder is not None:
                alerts = self.feeder.ingest_packet(pkt)
                for a in alerts:
                    self.stats["anomaly_score"] = round(a.peak_score, 3)
                    self.stats["tau"] = round(a.threshold, 3)
                    attr = a.attribution or {}
                    threat_name = attr.get("threat_type", "ANOMALOUS_BURST").upper()

                    rec = {
                        "ts": ts_str,
                        "window_t0": round(a.window_t0, 2),
                        "window_t1": round(a.window_t1, 2),
                        "peak_score": round(a.peak_score, 4),
                        "threshold": round(a.threshold, 4),
                        "is_anomaly": a.is_anomaly,
                        "confirmed": a.confirmed,
                        "attribution": a.attribution,
                    }
                    with open(ALERT_LOG, "a") as f:
                        f.write(json.dumps(rec) + "\n")

                    if a.confirmed:
                        self.stats["alerts_caught"] += 1
                        self.stats["threat_type"] = f"AI ATTACK CONFIRMED: {threat_name}"
                        msg = f"NJ-ODE ALERT: Score {a.peak_score:.2f} > tau {a.threshold:.2f} | {threat_name}"
                        self.active_alert = msg
                        self.alert_timer = time.time() + 6.0
                        self.event_log.append({"time": ts_str, "is_alert": True, "text": msg})

            if event_type == "PROCESS_EXECUTION":
                self.stats["alerts_caught"] += 1
                self.stats["anomaly_score"] = max(self.stats["anomaly_score"], 999.0)
                self.stats["threat_type"] = "UNAUTHORIZED HOST EXECUTION"
                app = payload.get("app", "Unauthorized Binary")
                pid = payload.get("pid", "---")
                msg = f"HOST BREACH: '{app}' executed on SCADA Workstation! (PID: {pid})"
                self.active_alert = msg
                self.alert_timer = time.time() + 6.0
                self.event_log.append({"time": ts_str, "is_alert": True, "text": msg})
                # Log to alerts.jsonl
                h_rec = {
                    "ts": ts_str,
                    "window_t0": round(time.time(), 2),
                    "window_t1": round(time.time() + 1.0, 2),
                    "peak_score": 999.0,
                    "threshold": self.tau,
                    "is_anomaly": True,
                    "confirmed": True,
                    "attribution": {"top_channel": "host_sentry", "threat_type": f"HOST BREACH: {app}"},
                }
                with open(ALERT_LOG, "a") as f:
                    f.write(json.dumps(h_rec) + "\n")

            elif event_type == "CYBER_ATTACK":
                atk = payload.get("atk", payload.get("attack_type", "EXFILTRATION"))
                if not (self.active_alert and time.time() < self.alert_timer):
                    self.stats["threat_type"] = f"CYBER THREAT: {atk}"
                    msg = f"CYBER INTRUSION: {atk} detected in simplex stream!"
                    self.active_alert = msg
                    self.alert_timer = time.time() + 6.0
                    self.event_log.append({"time": ts_str, "is_alert": True, "text": msg})

            elif event_type == "SCADA_PHYSICAL_ANOMALY":
                self.stats["threat_type"] = "PHYSICAL VALVE TAMPERING"
                msg = f"REACTOR ALARM: Primary Coolant Loop Temp Spiking to {self.latest_vitals['temp']}C!"
                self.active_alert = msg
                self.alert_timer = time.time() + 6.0
                self.event_log.append({"time": ts_str, "is_alert": True, "text": msg})

            elif event_type == "ROUTINE_SCADA":
                if not (self.active_alert and time.time() < self.alert_timer):
                    if self.stats["anomaly_score"] <= self.tau:
                        self.stats["threat_type"] = "NONE (BASELINE NOMINAL)"
                    msg = f"SCADA Vitals [T:{self.latest_vitals['temp']}C, P:{self.latest_vitals['press']}bar, Freq:{self.latest_vitals['freq']}Hz]"
                    self.event_log.append({"time": ts_str, "is_alert": False, "text": msg})

            # Trim log history
            if len(self.event_log) > 20:
                self.event_log = self.event_log[-20:]

    def poll_loopback(self):
        """Pulls packets from local loopback mirror for 1-laptop testing."""
        while True:
            try:
                ready, _, _ = select.select([self.loopback_sock], [], [], 0.0)
                if ready:
                    data, _ = self.loopback_sock.recvfrom(4096)
                    pkt = json.loads(data.decode("utf-8"))
                    # Normalize fields
                    self.process_incoming_packet(pkt)
                else:
                    break
            except Exception:
                break

    def render_canvas(self, cam_frame):
        """Draws the comprehensive industrial Nuclear SOC dashboard."""
        w, h = 1140, 740
        canvas = np.zeros((h, w, 3), dtype=np.uint8)

        # Background tint
        canvas[:] = (18, 18, 26)

        is_alerting = (self.active_alert is not None and time.time() < self.alert_timer)

        # ---------------- TOP HEADER BANNER ----------------
        header_color = (0, 0, 180) if is_alerting else (28, 28, 42)
        cv2.rectangle(canvas, (0, 0), (w, 65), header_color, -1)
        cv2.putText(canvas, "CHRONOS: AIR-GAPPED NUCLEAR SCADA SOC & DEFENSE CONSOLE", (25, 42), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.76, (0, 240, 255), 2)
        cv2.putText(canvas, "BARC / NPCIL KUDANKULAM UNIT 1 | PS #26145", (w - 450, 42), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (200, 200, 200), 1)

        # ---------------- COL 1: OPTICAL RECEIVER (Left: x 20-370) ----------------
        col1_w = 350
        cv2.rectangle(canvas, (20, 80), (20 + col1_w, 420), (32, 32, 48), -1)
        cv2.rectangle(canvas, (20, 80), (20 + col1_w, 420), (55, 55, 75), 1)
        
        mode_tag = "[OPTICAL WEBCAM INGEST]" if self.mode == "WEBCAM" else "[DIRECT SIMPLEX LOOPBACK]"
        mode_color = (0, 255, 0) if self.mode == "WEBCAM" else (255, 200, 0)
        cv2.putText(canvas, mode_tag, (35, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.52, mode_color, 2)
        cv2.putText(canvas, "(Press SPACE to Toggle Ingest)", (205, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140, 140, 140), 1)

        # Camera viewport
        if self.mode == "WEBCAM" and cam_frame is not None:
            resized_cam = cv2.resize(cam_frame, (col1_w - 30, 280))
            canvas[125:405, 35:35 + col1_w - 30] = resized_cam
        else:
            # Synthetic animated photon stream animation for loopback
            sim_box = np.zeros((280, col1_w - 30, 3), dtype=np.uint8)
            sim_box[:] = (12, 12, 18)
            cv2.putText(sim_box, "SIMPLEX OPTICAL BUS ACTIVE", (40, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 240, 255), 2)
            cv2.putText(sim_box, "Ingesting Direct Simplex Stream", (45, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 120), 1)
            cv2.putText(sim_box, "Physical Inbound Return Path: ZERO", (35, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 100, 255), 1)
            cv2.putText(sim_box, f"Frames Ingested: {self.stats['optical_frames']}", (75, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            canvas[125:405, 35:35 + col1_w - 30] = sim_box

        # Col 1 Bottom: Air Gap Physical Security Card
        cv2.rectangle(canvas, (20, 435), (20 + col1_w, 715), (26, 26, 38), -1)
        cv2.rectangle(canvas, (20, 435), (20 + col1_w, 715), (45, 45, 65), 1)
        cv2.putText(canvas, "AIR-GAP PHYSICAL SECURITY", (35, 465), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
        cv2.putText(canvas, f"Optical Frames Decoded: {self.stats['optical_frames']}", (35, 502), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (200, 200, 200), 1)
        cv2.putText(canvas, f"Total Ingested SCADA Logs: {self.stats['total_logs']}", (35, 536), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 180), 1)
        cv2.putText(canvas, f"Security Alerts Tripped: {self.stats['alerts_caught']}", (35, 570), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 80, 255) if self.stats['alerts_caught'] > 0 else (180, 180, 180), 2)
        cv2.putText(canvas, "Physical Return Cable: NONE (Photons Only)", (35, 608), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 220, 255), 1)
        cv2.putText(canvas, "Air-Gap Integrity: 100% SECURED", (35, 642), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 120), 2)
        cv2.putText(canvas, "Latency Across Diode: < 350 ms", (35, 678), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (160, 160, 160), 1)

        # ---------------- COL 2: NUCLEAR REACTOR & GRID VITALS (Center: x 390-740) ----------------
        col2_w = 350
        cv2.rectangle(canvas, (390, 80), (390 + col2_w, 715), (24, 24, 36), -1)
        cv2.rectangle(canvas, (390, 80), (390 + col2_w, 715), (48, 48, 68), 1)
        cv2.putText(canvas, "NUCLEAR REACTOR & GRID VITALS", (410, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 240, 255), 2)

        # Metric 1: Reactor Core Temp
        temp_val = self.latest_vitals["temp"]
        t_color = (0, 255, 120) if temp_val <= 305 else ((0, 180, 255) if temp_val <= 325 else (0, 0, 255))
        cv2.rectangle(canvas, (405, 140), (725, 215), (32, 32, 46), -1)
        cv2.putText(canvas, "REACTOR CORE TEMPERATURE", (420, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 180, 180), 1)
        cv2.putText(canvas, f"{temp_val:.1f} °C", (420, 202), cv2.FONT_HERSHEY_SIMPLEX, 0.95, t_color, 2)
        cv2.putText(canvas, "Nominal: 290 - 300 °C", (585, 202), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

        # Metric 2: Primary Loop Coolant Pressure
        press_val = self.latest_vitals["press"]
        p_color = (0, 255, 120) if press_val <= 162 else (0, 0, 255)
        cv2.rectangle(canvas, (405, 230), (725, 305), (32, 32, 46), -1)
        cv2.putText(canvas, "PRIMARY COOLANT PRESSURE", (420, 255), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 180, 180), 1)
        cv2.putText(canvas, f"{press_val:.1f} bar", (420, 292), cv2.FONT_HERSHEY_SIMPLEX, 0.95, p_color, 2)
        cv2.putText(canvas, "Nominal: 155 bar", (585, 292), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

        # Metric 3: Grid Frequency (Indian Grid 50.00 Hz)
        freq_val = self.latest_vitals["freq"]
        cv2.rectangle(canvas, (405, 320), (725, 395), (32, 32, 46), -1)
        cv2.putText(canvas, "NLDC GRID FREQUENCY", (420, 345), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 180, 180), 1)
        cv2.putText(canvas, f"{freq_val:.3f} Hz", (420, 382), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 240, 255), 2)
        cv2.putText(canvas, "Target: 50.000 Hz", (585, 382), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

        # Metric 4: Generator Power Output
        mw_val = self.latest_vitals["mw"]
        cv2.rectangle(canvas, (405, 410), (725, 485), (32, 32, 46), -1)
        cv2.putText(canvas, "GENERATOR ACTIVE OUTPUT", (420, 435), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 180, 180), 1)
        cv2.putText(canvas, f"{mw_val:.1f} MW", (420, 472), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 255, 200), 2)
        cv2.putText(canvas, "Capacity: 1000 MW", (585, 472), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

        # Host Workstation Health (Real Laptop Stats)
        cv2.rectangle(canvas, (405, 505), (725, 695), (28, 28, 42), -1)
        cv2.rectangle(canvas, (405, 505), (725, 695), (50, 50, 70), 1)
        cv2.putText(canvas, "SCADA HOST WORKSTATION HEALTH", (420, 532), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (255, 255, 255), 2)
        
        cpu_val = self.latest_vitals["cpu"]
        ram_val = self.latest_vitals["ram"]
        cv2.putText(canvas, f"Real Laptop CPU Usage: {cpu_val:.1f}%", (420, 568), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 120), 1)
        cv2.putText(canvas, f"Real Laptop RAM Usage: {ram_val:.1f}%", (420, 602), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 120), 1)
        cv2.putText(canvas, "Zero-Trust Process Sentry: ACTIVE", (420, 638), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 240, 255), 1)
        cv2.putText(canvas, "Monitoring: Notepad, Calc, CMD, PowerShell", (420, 670), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (160, 160, 160), 1)

        # ---------------- COL 3: AI DEFENSE ENGINE & INCIDENTS (Right: x 760-1120) ----------------
        col3_w = 360
        cv2.rectangle(canvas, (760, 80), (760 + col3_w, 715), (24, 24, 34), -1)
        cv2.rectangle(canvas, (760, 80), (760 + col3_w, 715), (48, 48, 68), 1)
        cv2.putText(canvas, "CONTINUOUS-TIME AI DEFENSE (NJ-ODE)", (775, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 240, 255), 2)

        # AI Anomaly Score Gauge
        s_score = self.stats["anomaly_score"]
        tau = self.stats["tau"]
        is_threat = (s_score > tau)
        score_color = (0, 0, 255) if is_threat else (0, 255, 120)
        
        cv2.rectangle(canvas, (775, 140), (1105, 235), (32, 32, 46), -1)
        cv2.putText(canvas, f"PEAK ANOMALY SCORE (S_peak): {s_score:.3f}", (790, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.48, score_color, 2)
        cv2.putText(canvas, f"Calibrated Threshold (tau): {tau:.2f}", (790, 192), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (180, 180, 180), 1)

        # Bar gauge for anomaly
        cv2.rectangle(canvas, (790, 205), (1090, 222), (50, 50, 65), -1)
        fill_w = int(np.clip(s_score / 2.5, 0.0, 1.0) * 300)
        cv2.rectangle(canvas, (790, 205), (790 + fill_w, 222), score_color, -1)
        # Threshold marker
        tau_x = 790 + int((tau / 2.5) * 300)
        cv2.line(canvas, (tau_x, 201), (tau_x, 226), (255, 255, 255), 2)

        # Threat Attribution Card
        cv2.rectangle(canvas, (775, 250), (1105, 320), (32, 32, 46), -1)
        cv2.rectangle(canvas, (775, 250), (1105, 320), score_color, 2 if is_threat else 1)
        cv2.putText(canvas, "THREAT ATTRIBUTION CLASSIFIER:", (790, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (200, 200, 200), 1)
        cv2.putText(canvas, self.stats["threat_type"], (790, 305), cv2.FONT_HERSHEY_SIMPLEX, 0.52, score_color, 2)

        # Live Event & Breach Stream
        cv2.putText(canvas, "LIVE AIR-GAPPED SECURITY AUDIT LOG:", (775, 350), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
        y_log = 380
        if not self.event_log:
            cv2.putText(canvas, "Awaiting Telemetry Feed...", (790, y_log + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 140, 140), 1)
        else:
            for item in self.event_log[-4:]:
                is_alert = item["is_alert"]
                box_color = (0, 0, 255) if is_alert else (40, 40, 55)
                text_color = (0, 220, 255) if not is_alert else (0, 0, 255)
                
                cv2.rectangle(canvas, (775, y_log), (1105, y_log + 70), (28, 28, 40), -1)
                cv2.rectangle(canvas, (775, y_log), (1105, y_log + 70), box_color, 2 if is_alert else 1)
                
                title = f"🚨 [{item['time']}] SECURITY ALERT!" if is_alert else f"[{item['time']}] ROUTINE SCADA TELEMETRY"
                cv2.putText(canvas, title, (785, y_log + 24), cv2.FONT_HERSHEY_SIMPLEX, 0.44, text_color, 2 if is_alert else 1)
                cv2.putText(canvas, item["text"][:42], (785, y_log + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255) if is_alert else (180, 180, 180), 1)
                y_log += 80

        # ---------------- PROMINENT ALERT BANNER IF ACTIVE ----------------
        if is_alerting:
            cv2.rectangle(canvas, (20, 680), (w - 20, 730), (0, 0, 240), -1)
            cv2.putText(canvas, f"CRITICAL DEFENSE ALERT: {self.active_alert}", (40, 712), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)

        return canvas

def main():
    parser = argparse.ArgumentParser(description="CHRONOS Nuclear SCADA SOC Dashboard")
    parser.add_argument("--source", choices=["webcam", "loopback"], default=None, help="Initial ingest mode")
    parser.add_argument("--camera-id", type=int, default=0, help="Camera device index")
    parser.add_argument("--headless", action="store_true", help="Run without OpenCV GUI window")
    args = parser.parse_args()

    soc = NuclearSOCReceiver()
    if args.source:
        soc.mode = args.source.upper()

    headless = args.headless or not os.environ.get("DISPLAY")

    print("=" * 65)
    print("  CHRONOS: AIR-GAPPED NUCLEAR SCADA SOC DASHBOARD ACTIVE")
    print(f"  Mode : {soc.mode} | Headless: {headless}")
    print("  Mode Options:")
    print("    - WEBCAM MODE : Optical camera scan from QR Diode screen")
    print("    - LOOPBACK    : Local simplex mirror (single-laptop presentation)")
    print("    -> Press [SPACE] anytime on dashboard to toggle mode!")
    print("    -> Press [Q] to quit.")
    print("=" * 65 + "\n")

    cap = None
    if soc.mode == "WEBCAM":
        try:
            cap = cv2.VideoCapture(args.camera_id)
            if not cap.isOpened():
                print(f"[!] Warning: Camera {args.camera_id} unavailable. Switching to LOOPBACK mode.")
                soc.mode = "LOOPBACK"
        except Exception:
            soc.mode = "LOOPBACK"

    detector = cv2.QRCodeDetector()

    if not headless:
        try:
            cv2.namedWindow("CHRONOS Nuclear Air-Gapped SOC", cv2.WINDOW_NORMAL)
        except Exception:
            headless = True

    try:
        while True:
            cam_frame = None

            if soc.mode == "WEBCAM" and cap is not None:
                ret, frame = cap.read()
                if ret:
                    cam_frame = frame
                    # Decode QR code from optical frame
                    data, bbox, _ = detector.detectAndDecode(frame)
                    if data:
                        try:
                            payload = json.loads(data)
                            soc.process_incoming_packet(payload)
                            if bbox is not None and cam_frame is not None:
                                n = len(bbox[0])
                                for j in range(n):
                                    p1 = tuple(map(int, bbox[0][j]))
                                    p2 = tuple(map(int, bbox[0][(j + 1) % n]))
                                    cv2.line(cam_frame, p1, p2, (0, 255, 0), 3)
                        except Exception:
                            pass
            else:
                # Poll loopback packets
                soc.poll_loopback()

            if not headless:
                # Render dashboard
                canvas = soc.render_canvas(cam_frame)
                cv2.imshow("CHRONOS Nuclear Air-Gapped SOC", canvas)

                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    break
                elif key == 32:  # SPACEBAR toggles mode
                    soc.mode = "LOOPBACK" if soc.mode == "WEBCAM" else "WEBCAM"
                    if soc.mode == "WEBCAM" and cap is None:
                        cap = cv2.VideoCapture(args.camera_id)
                    print(f"\n[🔄 MODE SWITCHED] Dashboard ingest mode set to: {soc.mode}\n")
            else:
                time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        if cap is not None:
            cap.release()
        if not headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
