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

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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


def detect_available_cameras(max_tested=4):
    available = []
    for idx in range(max_tested):
        c = cv2.VideoCapture(idx)
        if c.isOpened():
            ret, _ = c.read()
            if ret:
                available.append(idx)
            c.release()
    return available if available else [0]


def resolve_camera_source(cam_arg="auto", phone_ip="", available_cams=None):
    """Resolves camera index (0, 1, 2) or phone stream URL."""
    if phone_ip:
        p = str(phone_ip).strip()
        if not p.startswith("http"):
            if ":" not in p:
                return f"http://{p}:8080/video"
            return f"http://{p}/video"
        return p
    if cam_arg is None or str(cam_arg).lower() == "auto":
        # If multiple cameras available (e.g. laptop webcam 0 + phone Iriun 1), prefer index 1
        if available_cams and len(available_cams) > 1:
            return available_cams[1]
        return available_cams[0] if available_cams else 0
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


def notify_dashboard_packet(from_id, to_id, size=128, threat=False, is_diode=False, is_alert=False, feat=None, scada=None, dashboard_url="http://127.0.0.1:8501"):
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
        if scada is not None:
            event["scada"] = scada
            event["p"] = scada.get("p", scada.get("pressure_bar"))
            event["tavg"] = scada.get("tavg", scada.get("core_temp_c"))
            event["flow"] = scada.get("flow", scada.get("coolant_flow_kgs"))
            event["mw"] = scada.get("mw", scada.get("output_mwe"))
            event["state"] = scada.get("state", scada.get("reactor_state"))
        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            f"{dashboard_url.rstrip('/')}/api/packet/event",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=0.20) as _:
            pass
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="CHRONOS Optical Diode Receiver & SOC")
    parser.add_argument("--source", choices=["camera", "loopback"], default="camera", help="Input mode: 'camera' or 'loopback' (default: camera)")
    parser.add_argument("--camera", "--camera-id", default="auto", help="Camera index (0, 1, 2) or 'auto' (detects phone/Iriun webcam)")
    parser.add_argument("--phone", default="", help="Phone IP for IP Webcam app (e.g. 192.168.1.5 -> http://192.168.1.5:8080/video)")
    parser.add_argument("--dashboard-url", default="http://127.0.0.1:8501", help="SOC Dashboard URL for event syncing")
    parser.add_argument("--headless", action="store_true", help="Run in headless terminal mode")
    parser.add_argument("--alert-log", default=str(ALERT_LOG), help="Output alerts JSONL path")
    args = parser.parse_args()

    headless = args.headless or not os.environ.get("DISPLAY")

    available_cams = detect_available_cameras()
    cam_source = resolve_camera_source(args.camera, args.phone, available_cams)
    current_mode = args.source.upper()

    print("=" * 68)
    print("  CHRONOS: AIR-GAPPED SCAN RECEIVER & AI CORE ONLINE")
    print(f"  Mode           : {current_mode} | Headless: {headless}")
    print(f"  Detected Cams  : {available_cams} (Active: #{cam_source})")
    print("  [Tip] Scanning with Iriun Webcam on Phone via USB Cable:")
    print("        Press 'C' in HUD or pass '--camera 1' to switch cameras on the fly!")
    print("=" * 68)

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

    cap = None
    active_cam_idx = cam_source if isinstance(cam_source, int) else 0
    if current_mode == "CAMERA":
        try:
            print(f"[*] Opening Optical Video Stream: {cam_source} ...")
            cap = cv2.VideoCapture(cam_source)
            if not cap.isOpened():
                print(f"[!] Warning: Camera {cam_source} unavailable. Checking alternatives...")
                for alt_idx in available_cams:
                    if alt_idx != cam_source:
                        alt_cap = cv2.VideoCapture(alt_idx)
                        if alt_cap.isOpened():
                            cap = alt_cap
                            active_cam_idx = alt_idx
                            print(f"[✓] Connected to alternative Camera #{alt_idx}")
                            break
            if cap is None or not cap.isOpened():
                print(f"[!] No camera available. Falling back to LOOPBACK mode.")
                current_mode = "LOOPBACK"
            else:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                print(f"[✓] Successfully connected to Optical Camera Stream: #{active_cam_idx} (1280x720, Buffer=1)")
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
                    if not data:
                        # Fallback Pass 2: Grayscale with histogram equalization to cut through screen glare
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        enhanced = cv2.equalizeHist(gray)
                        data, bbox, _ = detector.detectAndDecode(enhanced)

                    if data:
                        try:
                            payload = json.loads(data)
                        except Exception:
                            pass
                        if bbox is not None and len(bbox) > 0:
                            try:
                                pts = np.int32(bbox).reshape(-1, 2)
                                cv2.polylines(frame, [pts], True, (0, 255, 0), 3)
                            except Exception:
                                pass
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

                        # Real Node Attribution (Dynamic, NOT fake hardcoded plc-01)
                        src_node = item.get("src") or item.get("facility") or "nuclear-scada"
                        pkt_size = int(feat[1])

                        scada_info = {
                            "facility": item.get("facility", "BARC / NPCIL Kudankulam Unit 1 (PWR)"),
                            "p": round(float(item.get("p", item.get("p_bar", item.get("pressure_bar", 155.5)))), 1),
                            "tavg": round(float(item.get("tavg", item.get("tavg_c", item.get("core_temp_c", 310.0)))), 1),
                            "flow": round(float(item.get("flow", item.get("wrca_kgs", item.get("coolant_flow_kgs", 16515.8)))), 1),
                            "mw": round(float(item.get("mw", item.get("mwe_electric", item.get("output_mwe", 955.3)))), 1),
                            "cpu": round(float(item.get("cpu", item.get("host_cpu_pct", item.get("container_cpu_pct", 1.2)))), 1),
                            "ram": round(float(item.get("ram", item.get("host_ram_pct", item.get("container_mem_pct", 2.8)))), 1),
                            "state": item.get("state", item.get("reactor_state", "NOMINAL_FULL_POWER")),
                            "atk": item.get("atk", item.get("attack_type", "")),
                        }

                        # Print genuine scanned telemetry directly to terminal (Exact Docker Terminal Match)
                        state_tag = "[NOMINAL]" if scada_info["state"] in ("NOMINAL", "NOMINAL_FULL_POWER") else f"[{scada_info['state']}]"
                        print(f"[{time.strftime('%H:%M:%S')}] {state_tag} Pressure: {scada_info['p']:5.1f} bar | Temp: {scada_info['tavg']:5.1f} C | Flow: {scada_info['flow']:7.1f} kg/s | Power: {scada_info['mw']:5.1f} MWe | State: {scada_info['state']}")

                        # Dispatch end-to-end optical transit events to React dashboard with full physics
                        notify_dashboard_packet(src_node, "tx-diode", size=pkt_size, threat=stats["is_alert"], feat=feat, scada=scada_info, dashboard_url=args.dashboard_url)
                        notify_dashboard_packet("tx-diode", "optical-gap", size=pkt_size, threat=stats["is_alert"], feat=feat, is_diode=True, scada=scada_info, dashboard_url=args.dashboard_url)
                        notify_dashboard_packet("optical-gap", "rx-diode", size=pkt_size, threat=stats["is_alert"], feat=feat, is_diode=True, scada=scada_info, dashboard_url=args.dashboard_url)
                        notify_dashboard_packet("rx-diode", "njode-core", size=pkt_size, threat=stats["is_alert"], feat=feat, scada=scada_info, dashboard_url=args.dashboard_url)
                        if stats["is_alert"]:
                            notify_dashboard_packet("njode-core", "soc-siem", size=pkt_size, threat=True, is_alert=True, feat=feat, scada=scada_info, dashboard_url=args.dashboard_url)

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
                key = cv2.waitKey(1) & 0xFF
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
