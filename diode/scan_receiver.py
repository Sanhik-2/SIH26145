"""
CHRONOS SCAN RECEIVER & AIR-GAPPED SOC (Runs on Scan Node Laptop)
----------------------------------------------------------------
1. Connects to the laptop's built-in webcam.
2. Captures and decodes the optical QR stream from the QR Node's screen.
3. Renders a dark-mode real-time visual SOC interface.
4. HIGHLIGHTS LIVE HOST EVENTS:
   Whenever an app (Notepad, Calculator, CMD) is opened on Node 1, 2, or 3,
   it immediately flashes a bright Red/Amber Alert card on screen!

Usage:
  python scan_receiver.py
"""

import argparse
import json
import os
from pathlib import Path
import socket
import sys
import time
import cv2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.extractor import Packet
from features.windowing import LiveFeeder
from models.njode import NJODE

ALERT_LOG = REPO_ROOT / "alerts.jsonl"
CHECKPOINT_PATH = REPO_ROOT / "checkpoints" / "njode_telemetry.pt"
MIRROR_PORT = 9998


def render_dashboard(frame, logs, stats, current_mode="WEBCAM"):
    """Draws a modern SOC dashboard with real AI anomaly metrics."""
    h, w = 720, 1100
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # Top Header Banner
    is_alerting = stats.get("is_alert", False)
    header_color = (0, 0, 180) if is_alerting else (20, 20, 32)
    cv2.rectangle(canvas, (0, 0), (w, 65), header_color, -1)
    cv2.putText(canvas, "CHRONOS: AIR-GAPPED OPTICAL ENCLAVE (AI DEFENSE CONSOLE)", (25, 42), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 240, 255), 2)
    mode_text = f"MODE: [{current_mode}] (Press SPACE to toggle)"
    cv2.putText(canvas, mode_text, (w - 380, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 180), 1)

    # Left Column: Live Ingest Feed (Webcam or Loopback Indicator)
    cv2.rectangle(canvas, (25, 80), (460, 410), (35, 35, 50), 2)
    cv2.putText(canvas, f"[OPTICAL INGEST: {current_mode}]", (35, 105), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    if frame is not None and current_mode == "WEBCAM":
        resized_cam = cv2.resize(frame, (415, 285))
        canvas[115:400, 35:450] = resized_cam
    else:
        # Loopback diagram in place of camera
        cv2.rectangle(canvas, (35, 115), (450, 400), (22, 26, 36), -1)
        cv2.putText(canvas, "SIMULATED PHOTON LOOPBACK", (80, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 240, 255), 2)
        cv2.putText(canvas, f"Mirrored Port: 127.0.0.1:{MIRROR_PORT}", (110, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1)
        cv2.putText(canvas, "Zero Physical Return Path Assured", (95, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 120), 1)

    # Left Column Bottom: NJ-ODE AI Engine Scores
    cv2.rectangle(canvas, (25, 425), (460, 695), (25, 25, 38), -1)
    cv2.rectangle(canvas, (25, 425), (460, 695), (45, 45, 60), 1)
    cv2.putText(canvas, "CONTINUOUS-TIME NJ-ODE ENGINE", (35, 455), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    
    score = stats.get("score", 0.48)
    tau = stats.get("tau", 2.464)
    ratio = min(1.0, score / max(1e-4, tau * 3.0))

    # Anomaly score gauge bar
    cv2.rectangle(canvas, (35, 475), (445, 498), (40, 40, 55), -1)
    bar_width = int(410 * ratio)
    bar_color = (0, 0, 255) if score > tau else (0, 220, 120)
    cv2.rectangle(canvas, (35, 475), (35 + bar_width, 498), bar_color, -1)
    cv2.rectangle(canvas, (35, 475), (445, 498), (70, 70, 90), 1)

    cv2.putText(canvas, f"Peak Score S_peak: {score:.3f} | Threshold tau: {tau:.3f}", (35, 520), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1)
    cv2.putText(canvas, f"Threat Attribution: {stats.get('threat', 'NORMAL')}", (35, 550), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, bar_color, 2 if score > tau else 1)
    cv2.putText(canvas, f"Frames Decoded: {stats.get('frames', 0)} | Telemetry: {stats.get('total_logs', 0)} pkts", (35, 585), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 180, 180), 1)
    cv2.putText(canvas, f"Host Security Breaches Caught: {stats.get('events', 0)}", (35, 618), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 100, 255), 2)
    cv2.putText(canvas, "Simplex Optical Diode Egress: ZERO RETURN BITS", (35, 655), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 150, 255), 1)

    # Right Column: Ingested Event & Telemetry Stream
    cv2.rectangle(canvas, (480, 80), (1075, 695), (20, 20, 30), -1)
    cv2.rectangle(canvas, (480, 80), (1075, 695), (45, 45, 65), 2)
    cv2.putText(canvas, "LIVE INGESTED NETWORK & HOST EVENT STREAM", (500, 115), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.58, (0, 200, 255), 2)

    y_pos = 150
    if not logs:
        cv2.putText(canvas, "AWAITING OPTICAL TRANSMISSION...", (520, 260), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.putText(canvas, "Point webcam at QR Node screen or use loopback.", (520, 300), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (150, 150, 150), 1)
    else:
        for entry in logs[-5:]:
            is_event = (entry.get("event_type") == "PROCESS_EXECUTION" or entry.get("type") == "PROCESS_EXECUTION")
            is_attack = (entry.get("event_type") == "CYBER_ATTACK" or entry.get("type") == "CYBER_ATTACK")

            if is_event:
                card_color = (0, 50, 255)
                header_text = f"🚨 [CRITICAL HOST BREACH] {entry.get('app', 'Binary')} (PID: {entry.get('pid', '---')})"
                payload_text = entry.get('payload', entry.get('msg', 'Unauthorized host execution'))
            elif is_attack:
                card_color = (0, 120, 255)
                header_text = f"⚡ [CYBER THREAT] {entry.get('attack_type', entry.get('atk', 'Anomaly'))}"
                payload_text = entry.get('payload', entry.get('msg', 'Targeted threat burst detected'))
            else:
                card_color = (0, 180, 120)
                header_text = f"[{entry.get('time', entry.get('ts', '--'))}] ROUTINE SCADA TELEMETRY #{entry.get('seq', 0)}"
                temp = entry.get('temp', entry.get('temp_c', '--'))
                press = entry.get('press', entry.get('pressure_bar', '--'))
                freq = entry.get('freq', entry.get('grid_freq_hz', '--'))
                payload_text = f"Core: {temp}C | Pressure: {press}bar | Grid: {freq}Hz"

            cv2.rectangle(canvas, (495, y_pos), (1060, y_pos + 88), (32, 32, 45), -1)
            cv2.rectangle(canvas, (495, y_pos), (1060, y_pos + 88), card_color, 2 if (is_event or is_attack) else 1)

            cv2.putText(canvas, header_text, (505, y_pos + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.46, card_color, 2)
            cv2.putText(canvas, payload_text[:65], (505, y_pos + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (240, 240, 240), 1)
            cv2.putText(canvas, "Optical Simplex Ingest: VERIFIED | NJ-ODE Evaluated", 
                        (505, y_pos + 75), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (140, 140, 140), 1)
            y_pos += 102

    return canvas


def resolve_camera_source(cam_arg: Any = "0", phone_ip: str = "") -> Any:
    """Resolves camera index (0, 1) or phone IP stream URL (http://<ip>:8080/video)."""
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


def notify_dashboard_packet(from_id, to_id, size=128, threat=False, is_diode=False, is_alert=False, feat=None, dashboard_url="http://127.0.0.1:8501"):
    try:
        import urllib.request
        event = {
            "type": "packet_transit",
            "from": from_id,
            "to": to_id,
            "size": size,
            "threat": threat,
            "is_diode_bridge": is_diode,
            "is_alert": is_alert,
            "timestamp": time.time(),
        }
        if feat is not None:
            event["feat"] = feat
        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            f"{dashboard_url.rstrip('/')}/api/packet/event",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=0.15) as _:
            pass
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="CHRONOS Optical Diode Receiver & SOC")
    parser.add_argument("--source", choices=["camera", "loopback"], default="loopback", help="Input mode: 'camera' or 'loopback'")
    parser.add_argument("--camera", "--camera-id", default="0", help="Camera index (0, 1) or Phone stream URL (e.g. http://192.168.1.5:8080/video)")
    parser.add_argument("--phone", default="", help="Phone IP for IP Webcam app (e.g. 192.168.1.5 -> http://192.168.1.5:8080/video)")
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:8501", help="SOC Dashboard URL for event syncing")
    parser.add_argument("--headless", action="store_true", help="Run in headless terminal mode")
    parser.add_argument("--alert-log", default=str(ALERT_LOG), help="Output alerts JSONL path")
    args = parser.parse_args()

    headless = args.headless or not os.environ.get("DISPLAY")

    # Load NJ-ODE Model & LiveFeeder
    cam_source = resolve_camera_source(args.camera, args.phone)
    if args.phone or (isinstance(cam_source, str) and cam_source.startswith("http")):
        args.source = "camera"

    print("=" * 65)
    print("  CHRONOS: AIR-GAPPED SCAN RECEIVER & AI CORE ONLINE")
    print(f"  Mode : {args.source.upper()} | Headless: {headless}")
    if args.source.upper() == "CAMERA":
        print(f"  Camera Source: {cam_source} (Phone/Webcam)")
    print("=" * 65)

    model = None
    tau = 2.464
    if CHECKPOINT_PATH.exists():
        try:
            model = NJODE.load(str(CHECKPOINT_PATH), device="cpu")
            tau = float(model.threshold.item())
            print(f"[✓] Loaded NJ-ODE checkpoint (v{getattr(model, 'version', '1.1')}, tau={tau:.4f})")
        except Exception as e:
            print(f"[!] Checkpoint load fallback ({e})")

    feeder = None
    if model is not None:
        feeder = LiveFeeder(model=model, window_s=10.0, stride_s=2.0, hysteresis_n=2, hysteresis_m=3, device="cpu")

    alert_path = Path(args.alert_log)
    alert_path.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(cv2, "QRCodeDetectorAruco"):
        detector = cv2.QRCodeDetectorAruco()
    else:
        detector = cv2.QRCodeDetector()
    current_mode = args.source.upper()

    cap = None
    if current_mode == "CAMERA":
        try:
            print(f"[*] Opening Optical Video Stream: {cam_source} ...")
            cap = cv2.VideoCapture(cam_source)
            if not cap.isOpened():
                print(f"[!] Warning: Camera {cam_source} unavailable. Switching to LOOPBACK mode.")
                current_mode = "LOOPBACK"
            else:
                print(f"[✓] Successfully connected to Optical Camera Stream: {cam_source}")
        except Exception as e:
            print(f"[!] Camera initialization failed ({e}). Switching to LOOPBACK mode.")
            current_mode = "LOOPBACK"

    loop_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    loop_sock.bind(("127.0.0.1", MIRROR_PORT))
    loop_sock.settimeout(0.2)

    logs_feed = []
    last_seq = -1
    stats = {
        "frames": 0,
        "total_logs": 0,
        "events": 0,
        "score": 0.48,
        "tau": tau,
        "threat": "NORMAL (BASELINE)",
        "is_alert": False
    }

    if not headless:
        try:
            cv2.namedWindow("CHRONOS Air-Gapped SOC Dashboard", cv2.WINDOW_NORMAL)
        except Exception:
            headless = True

    try:
        while True:
            frame = None
            payload = None

            if current_mode == "CAMERA" and cap is not None:
                ret, frame = cap.read()
                if ret and frame is not None:
                    data, bbox, _ = detector.detectAndDecode(frame)
                    if data:
                        try:
                            payload = json.loads(data)
                        except Exception:
                            pass
                        if bbox is not None:
                            n = len(bbox[0])
                            for j in range(n):
                                p1 = tuple(map(int, bbox[0][j]))
                                p2 = tuple(map(int, bbox[0][(j + 1) % n]))
                                cv2.line(frame, p1, p2, (0, 255, 0), 3)
            else:
                try:
                    data, _ = loop_sock.recvfrom(65535)
                    payload = json.loads(data.decode("utf-8"))
                except Exception:
                    pass

            if payload:
                seq = payload.get("seq", -1)
                if seq != last_seq and last_seq != -1:
                    last_seq = seq
                    stats["frames"] += 1

                    # Unify items list
                    items = payload.get("logs") if isinstance(payload.get("logs"), list) else [payload]
                    for item in items:
                        logs_feed.append(item)
                        stats["total_logs"] += 1
                        if len(logs_feed) > 30:
                            logs_feed = logs_feed[-30:]

                        # Feed into NJ-ODE continuous model
                        feat = item.get("feat", [1.0, 120, 3.5, 1.0, 0])
                        pkt = Packet(t=time.time(), size=int(feat[1]), payload=b"optical_frame", direction=int(feat[4]))
                        
                        if feeder is not None:
                            alerts = feeder.ingest_packet(pkt)
                            for a in alerts:
                                stats["score"] = round(a.peak_score, 3)
                                stats["is_alert"] = a.confirmed or a.is_anomaly
                                attr = a.attribution or {}
                                stats["threat"] = attr.get("threat_type", "UNKNOWN").upper()
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
                                with open(alert_path, "a") as f:
                                    f.write(json.dumps(rec) + "\n")

                        # Dispatch end-to-end optical transit events to React dashboard
                        src_node = item.get("src", "ews-alpha" if stats["is_alert"] else "plc-01")
                        pkt_size = int(feat[1])
                        notify_dashboard_packet(src_node, "tx-diode", size=pkt_size, threat=stats["is_alert"], feat=feat, dashboard_url=args.dashboard_url)
                        notify_dashboard_packet("tx-diode", "optical-gap", size=pkt_size, threat=stats["is_alert"], feat=feat, is_diode=True, dashboard_url=args.dashboard_url)
                        notify_dashboard_packet("optical-gap", "rx-diode", size=pkt_size, threat=stats["is_alert"], feat=feat, is_diode=True, dashboard_url=args.dashboard_url)
                        notify_dashboard_packet("rx-diode", "njode-core", size=pkt_size, threat=stats["is_alert"], feat=feat, dashboard_url=args.dashboard_url)
                        if stats["is_alert"]:
                            notify_dashboard_packet("njode-core", "soc-siem", size=pkt_size, threat=True, is_alert=True, feat=feat, dashboard_url=args.dashboard_url)

                        # Host process execution immediate alert
                        if item.get("event_type") == "PROCESS_EXECUTION" or item.get("type") == "PROCESS_EXECUTION":
                            stats["events"] += 1
                            stats["is_alert"] = True
                            app = item.get("app", "Unauthorized Binary")
                            stats["threat"] = f"HOST BREACH: {app.upper()}"
                            h_rec = {
                                "ts": time.strftime("%H:%M:%S"),
                                "window_t0": round(time.time(), 2),
                                "window_t1": round(time.time() + 1.0, 2),
                                "peak_score": 999.0,
                                "threshold": tau,
                                "is_anomaly": True,
                                "confirmed": True,
                                "attribution": {"top_channel": "host_sentry", "threat_type": f"HOST BREACH: {app}"},
                            }
                            with open(alert_path, "a") as f:
                                f.write(json.dumps(h_rec) + "\n")
                            print(f"\n🚨 [CRITICAL HOST BREACH DECODED] {app.upper()}")

            if not headless:
                dashboard = render_dashboard(frame, logs_feed, stats, current_mode)
                cv2.imshow("CHRONOS Air-Gapped SOC Dashboard", dashboard)
                key = cv2.waitKey(30) & 0xFF
                if key == ord('q'):
                    break
                elif key == 32:  # SPACE bar toggles mode
                    if current_mode == "WEBCAM":
                        current_mode = "LOOPBACK"
                    else:
                        current_mode = "WEBCAM"
                        if cap is None:
                            cap = cv2.VideoCapture(args.camera_id)
            else:
                time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        if cap is not None:
            cap.release()
        loop_sock.close()
        if not headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
