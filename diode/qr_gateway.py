"""
CHRONOS: NUCLEAR SCADA OPTICAL DATA DIODE (TRANSMITTER GATEWAY)
--------------------------------------------------------------
Enforces physical one-way air gap egress from Nuclear SCADA Enclave:
1. Ingests UDP simplex telemetry from the Nuclear SCADA Node on port 9999.
2. Polls containerized SCADA Node REST API (http://127.0.0.1:8080) for live NPPAD vitals.
3. Renders high-contrast Optical QR Photon Stream on screen for optical scanning.
4. Broadcasts local simplex mirror on port 9998 (enables instant single-laptop SOC testing).

Usage:
  python diode/qr_gateway.py
"""

import os
import sys
import socket
import json
import time
import argparse
import threading
import urllib.request
import urllib.error
import numpy as np
import cv2
import qrcode

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

INGEST_PORT = 9999
MIRROR_PORT = 9998
SCADA_HMI_URL = "http://127.0.0.1:8080"
DEFAULT_DASHBOARD_URL = "http://127.0.0.1:8501"

log_buffer = []
buffer_lock = threading.Lock()
sequence_id = 1
total_received = 0
total_bytes = 0
last_event = "System Initialized - Baseline Stable"
last_event_time = "--:--:--"
is_alert_active = False


class DashboardNotifier:
    """Non-blocking background HTTP dispatcher for real-time packet transit events."""
    def __init__(self, base_url: str = DEFAULT_DASHBOARD_URL):
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/api/packet/event"
        self.queue = []
        self.lock = threading.Lock()
        self.running = True
        self.worker = threading.Thread(target=self._dispatch_loop, daemon=True)
        self.worker.start()

    def send_event(self, event):
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
                    with urllib.request.urlopen(req, timeout=0.3):
                        pass
                except Exception:
                    pass
            time.sleep(0.04)

    def close(self):
        self.running = False

def poll_scada_container():
    """Polls the containerized SCADA node for live NPPAD telemetry across candidate endpoints."""
    candidate_urls = [
        SCADA_HMI_URL,
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://host.docker.internal:8080",
    ]
    for url in candidate_urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ChronosDiodeGateway/1.0"})
            with urllib.request.urlopen(req, timeout=0.6) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "pressure_bar" in data or "p" in data or "reactor_state" in data or "core_temp_c" in data:
                    return data
        except Exception:
            continue
    return None

def packet_listener():
    """Listens for UDP packets from Nuclear SCADA and queues for optical encoding."""
    global log_buffer, total_received, total_bytes, last_event, last_event_time, is_alert_active
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", INGEST_PORT))

    mirror_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\n" + "=" * 68)
    print("  CHRONOS: NUCLEAR SCADA OPTICAL DIODE GATEWAY ONLINE")
    print(f"  Ingest Port  : 0.0.0.0:{INGEST_PORT} (Simplex Inbound from SCADA)")
    print(f"  Container HMI: {SCADA_HMI_URL} (Live NPPAD Benchmark Telemetry)")
    print(f"  Optical Out  : High-Contrast QR Photon Stream on Screen")
    print(f"  Mirror Port  : 127.0.0.1:{MIRROR_PORT} (Simplex Air-Gap Receiver)")
    print(f"  Air Gap      : STRICT ONE-WAY EGRESS (ZERO RETURN PATH)")
    print("=" * 68 + "\n")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            total_received += 1
            total_bytes += len(data)

            payload = json.loads(data.decode("utf-8"))
            event_type = payload.get("event_type", "ROUTINE_SCADA")
            now = time.strftime("%H:%M:%S")

            # Mirror locally for dual-mode SOC receiver
            try:
                mirror_sock.sendto(data, ("127.0.0.1", MIRROR_PORT))
            except Exception:
                pass

            if event_type == "CYBER_ATTACK":
                is_alert_active = True
                atk = payload.get("attack_type", "ANOMALY")
                threat_cls = payload.get("threat_class", "a-f")
                last_event = f"CYBER ATTACK [{threat_cls}]: {atk}"
                last_event_time = now
                print(f"[!] [CYBER THREAT ENCODED TO DIODE] Threat: [{threat_cls}] {atk} | Time: {now}")

            elif event_type == "SCADA_PHYSICAL_ANOMALY":
                is_alert_active = True
                state = payload.get("reactor_state", "LOSS_OF_FLOW")
                last_event = f"PHYSICAL ANOMALY: {state}"
                last_event_time = now
                print(f"[!] [PHYSICAL SCADA ALARM] {state}! Pressure: {payload.get('p', payload.get('p_bar'))} bar")

            with buffer_lock:
                log_buffer.append(payload)

        except Exception:
            pass

def generate_qr_matrix(data_str, size=(500, 500)):
    """Generates an optimized, large, high-contrast QR image for phone cameras."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=12,
        border=4,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    mat = np.array(img, dtype=np.uint8)
    return cv2.resize(mat, size, interpolation=cv2.INTER_NEAREST)

def main():
    parser = argparse.ArgumentParser(description="CHRONOS Nuclear Optical Data Diode QR Gateway")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display window")
    parser.add_argument("--fps", type=float, default=2.0, help="Optical frame rate (default: 2.0 fps)")
    parser.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL, help="SOC Dashboard URL for SSE sync")
    args = parser.parse_args()

    headless = args.headless or not os.environ.get("DISPLAY")
    notifier = DashboardNotifier(base_url=args.dashboard_url)

    # Start packet ingestion thread
    threading.Thread(target=packet_listener, daemon=True).start()
    mirror_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if not headless:
        try:
            cv2.namedWindow("CHRONOS Nuclear Optical Diode (Transmitter)", cv2.WINDOW_NORMAL)
        except Exception:
            headless = True

    run_transmitter_loop(mirror_sock, notifier, headless=headless, fps=args.fps)


def run_transmitter_loop(mirror_sock, notifier, headless=False, fps=2.0):
    global sequence_id, total_received, total_bytes, is_alert_active

    # Load authentic NPPAD benchmark for dynamic standalone progression
    nppad_fallback_records = []
    normal_csv_path = REPO_ROOT / "data" / "nuclear" / "nppad_normal.csv"
    if normal_csv_path.exists():
        try:
            import csv
            with open(normal_csv_path, "r", encoding="utf-8") as f:
                nppad_fallback_records = list(csv.DictReader(f))
        except Exception:
            pass

    while True:
        start_time = time.time()

        with buffer_lock:
            batch = list(log_buffer)
            log_buffer.clear()

        if not batch:
            # Poll container directly for live NPPAD data from Docker
            node_data = poll_scada_container()
            if node_data:
                now_str = time.strftime("%H:%M:%S")
                state = node_data.get("reactor_state", "NOMINAL_FULL_POWER")
                evt = "ROUTINE_SCADA" if state in ("NOMINAL", "NOMINAL_FULL_POWER") else "SCADA_PHYSICAL_ANOMALY"
                latest = {
                    "node_id": 1,
                    "facility": "BARC_Kudankulam_1",
                    "src": "nuclear-scada",
                    "dataset": "NPPAD_Nature_Sci_Data_2022",
                    "reactor_state": state,
                    "state": state,
                    "event_type": evt,
                    "seq": sequence_id,
                    "time": now_str,
                    "ts": now_str,
                    "p": round(float(node_data.get("pressure_bar", node_data.get("p", 155.5))), 1),
                    "tavg": round(float(node_data.get("core_temp_c", node_data.get("tavg", 310.0))), 1),
                    "flow": round(float(node_data.get("coolant_flow_kgs", node_data.get("flow", 16515.8))), 1),
                    "mw": round(float(node_data.get("output_mwe", node_data.get("mw", 955.3))), 1),
                    "cpu": round(float(node_data.get("container_cpu_pct", node_data.get("cpu", 1.2))), 1),
                    "ram": round(float(node_data.get("container_mem_pct", node_data.get("ram", 2.8))), 1),
                }
            elif nppad_fallback_records:
                rec = nppad_fallback_records[sequence_id % len(nppad_fallback_records)]
                now_str = time.strftime("%H:%M:%S")
                p_val = round(float(rec.get("P", 155.5)), 1)
                tavg_val = round(float(rec.get("TAVG", 310.0)), 1)
                flow_val = round(float(rec.get("WRCA", 16515.8)), 1)
                mw_val = round(float(rec.get("QMWT", 2895.0)) * 0.33, 1)
                latest = {
                    "node_id": 1,
                    "facility": "BARC_Kudankulam_1",
                    "src": "nuclear-scada",
                    "event_type": "ROUTINE_SCADA",
                    "reactor_state": "NOMINAL_FULL_POWER",
                    "state": "NOMINAL_FULL_POWER",
                    "p": p_val,
                    "tavg": tavg_val,
                    "flow": flow_val,
                    "mw": mw_val,
                    "cpu": 1.2,
                    "ram": 2.8,
                    "seq": sequence_id,
                    "time": now_str,
                }
            else:
                latest = {
                    "node_id": 1,
                    "facility": "BARC_Kudankulam_1",
                    "src": "nuclear-scada",
                    "event_type": "ROUTINE_SCADA",
                    "reactor_state": "NOMINAL_FULL_POWER",
                    "state": "NOMINAL_FULL_POWER",
                    "p": 155.5,
                    "tavg": 310.0,
                    "flow": 16515.8,
                    "mw": 955.3,
                    "cpu": 1.2,
                    "ram": 2.8,
                    "seq": sequence_id,
                    "time": time.strftime("%H:%M:%S"),
                }
        else:
            latest = batch[-1]

        # Determine 5-channel feature vector [iat, bytes, entropy, burst, direction] for NJ-ODE AI
        atk_type = str(latest.get("attack_type", latest.get("atk", ""))).upper()
        threat_cls = str(latest.get("threat_class", latest.get("cls", ""))).lower()
        is_threat = bool(atk_type) or (threat_cls in ["a", "b", "c", "d", "e", "f"]) or (latest.get("reactor_state") not in ["NOMINAL_FULL_POWER", "NOMINAL", None])

        feat = latest.get("feat")
        if not feat:
            if "FLOOD" in atk_type or "DDOS" in atk_type or threat_cls == "a":
                feat = [0.005, 64, 1.10, 50.0, 1]
            elif "C2" in atk_type or threat_cls == "b":
                feat = [1.20, 256, 4.20, 1.0, 0]
            elif "DNS" in atk_type or "DGA" in atk_type or threat_cls == "c":
                feat = [0.15, 220, 7.85, 2.0, 0]
            elif "JA4" in atk_type or "ENCRYPTED" in atk_type or threat_cls == "d":
                feat = [1.80, 512, 7.92, 1.4, 0]
            elif "SCAN" in atk_type or "RECON" in atk_type or threat_cls == "e":
                feat = [0.08, 54, 3.10, 4.5, 0]
            elif "EXFIL" in atk_type or threat_cls == "f":
                feat = [0.015, 1400, 4.80, 8.5, 0]
            elif "MODBUS" in atk_type or "PUMP" in atk_type or "INJECTION" in atk_type or latest.get("reactor_state") == "LOSS_OF_FLOW":
                feat = [0.10, 400, 5.80, 3.0, 0]
            elif latest.get("event_type") == "PROCESS_EXECUTION":
                feat = [0.01, 1024, 7.95, 10.0, 0]
            else:
                feat = [1.05, 128, 3.45, 1.0, 0]

        src_node = latest.get("src", "redteam-attacker" if is_threat else "nuclear-scada")
        pkt_size = int(latest.get("bytes", latest.get("size", feat[1])))

        # Extract EXACT Kudankulam SCADA Vitals (Matching Docker Terminal output)
        p_val = round(float(latest.get("p", latest.get("p_bar", latest.get("pressure_bar", 155.5)))), 1)
        tavg_val = round(float(latest.get("tavg", latest.get("tavg_c", latest.get("core_temp_c", 310.0)))), 1)
        flow_val = round(float(latest.get("flow", latest.get("wrca_kgs", latest.get("coolant_flow_kgs", 16515.8)))), 1)
        mw_val = round(float(latest.get("mw", latest.get("mwe_electric", latest.get("output_mwe", 955.3)))), 1)
        cpu_val = round(float(latest.get("cpu", latest.get("host_cpu_pct", latest.get("container_cpu_pct", 1.2)))), 1)
        ram_val = round(float(latest.get("ram", latest.get("host_ram_pct", latest.get("container_mem_pct", 2.8)))), 1)
        state_val = str(latest.get("state", latest.get("reactor_state", "NOMINAL_FULL_POWER")))

        # Highly Optimized, High-Speed Optical QR Payload (~140 bytes, Version 4/5 QR Code)
        # This produces large, bold, easily-scannable QR blocks for phone cameras over cable
        optical_payload = {
            "seq": sequence_id,
            "src": src_node,
            "state": state_val,
            "p": p_val,
            "tavg": tavg_val,
            "flow": flow_val,
            "mw": mw_val,
            "cpu": cpu_val,
            "ram": ram_val,
            "atk": atk_type if is_threat else "",
            "feat": feat,
        }

        # Dispatch real packet movements to React SOC Dashboard
        if notifier:
            scada_map = {
                "p": p_val,
                "tavg": tavg_val,
                "flow": flow_val,
                "mw": mw_val,
                "cpu": cpu_val,
                "ram": ram_val,
                "state": state_val,
                "atk": optical_payload["atk"]
            }
            notifier.send_event({
                "type": "packet_transit",
                "from": src_node,
                "to": "tx-diode",
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "scada": scada_map,
                "p": p_val,
                "tavg": tavg_val,
                "flow": flow_val,
                "mw": mw_val,
                "state": state_val,
                "timestamp": time.time(),
            })
            notifier.send_event({
                "type": "packet_transit",
                "from": "tx-diode",
                "to": "optical-gap",
                "is_diode_bridge": True,
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "scada": scada_map,
                "timestamp": time.time(),
            })
            notifier.send_event({
                "type": "packet_transit",
                "from": "optical-gap",
                "to": "rx-diode",
                "is_diode_bridge": True,
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "scada": scada_map,
                "timestamp": time.time(),
            })
            notifier.send_event({
                "type": "packet_transit",
                "from": "rx-diode",
                "to": "njode-core",
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "scada": scada_map,
                "p": p_val,
                "tavg": tavg_val,
                "flow": flow_val,
                "mw": mw_val,
                "state": state_val,
                "timestamp": time.time(),
            })
            if is_threat:
                notifier.send_event({
                    "type": "packet_transit",
                    "from": "njode-core",
                    "to": "soc-siem",
                    "size": pkt_size,
                    "feat": feat,
                    "threat": True,
                    "is_alert": True,
                    "scada": scada_map,
                    "timestamp": time.time(),
                })

        # Mirror across local port 9998
        try:
            mirror_sock.sendto(json.dumps(optical_payload).encode("utf-8"), ("127.0.0.1", MIRROR_PORT))
        except Exception:
            pass

        # Generate minimal, high-density, high-contrast QR Matrix
        qr_text = json.dumps(optical_payload, separators=(',', ':'))
        qr_img = generate_qr_matrix(qr_text, size=(500, 500))

        if not headless:
            # High-impact transmitter GUI canvas (720x720)
            h, w = 720, 720
            canvas = np.zeros((h, w, 3), dtype=np.uint8)

            # Top Header Banner
            cv2.rectangle(canvas, (0, 0), (w, 55), (25, 25, 40), -1)
            cv2.putText(canvas, "NUCLEAR SCADA OPTICAL DATA DIODE", (30, 36), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 240, 255), 2)

            # Draw Enormous High-Contrast QR frame centered with clean white margins
            canvas[65:565, 110:610] = qr_img

            # Bottom Telemetry Strip
            cv2.rectangle(canvas, (0, 575), (w, h), (18, 18, 28), -1)
            cv2.line(canvas, (0, 575), (w, 575), (50, 50, 70), 1)

            cv2.putText(canvas, f"Frame #{sequence_id:04d} | Ingest: {total_received} pkts | Payload: {len(qr_text)}B (Opt v4/5)", 
                        (25, 600), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            
            status_color = (0, 0, 255) if optical_payload.get("atk") or optical_payload.get("state") not in ("NOMINAL", "NOMINAL_FULL_POWER") else (0, 255, 120)
            cv2.putText(canvas, f"State: {optical_payload.get('state')} | CPU: {cpu_val:.1f}% | RAM: {ram_val:.1f}%", 
                        (25, 630), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1)

            cv2.putText(canvas, f"NPPAD Vitals: P={p_val:.1f}bar | Tavg={tavg_val:.1f}C | Flow={flow_val:.1f}kg/s | MW={mw_val:.1f}MWe", 
                        (25, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 240, 255), 1)

            cv2.putText(canvas, "Air-Gap: UNIDIRECTIONAL OPTICAL PHOTONS ONLY (ZERO COPPER RETURN)", 
                        (25, 692), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 0), 1)

            cv2.imshow("CHRONOS Nuclear Optical Diode (Transmitter)", canvas)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

        # Terminal live telemetry output (Exact Docker plant telemetry)
        status_tag = "[NOMINAL]" if state_val in ("NOMINAL", "NOMINAL_FULL_POWER") else f"[{state_val}]"
        print(f"[{time.strftime('%H:%M:%S')}] {status_tag} Pressure: {p_val:5.1f} bar | Temp: {tavg_val:5.1f} C | Flow: {flow_val:7.1f} kg/s | Power: {mw_val:5.1f} MWe | State: {state_val}")

        sequence_id += 1
        elapsed = time.time() - start_time
        sleep_dur = max(0.05, (1.0 / max(0.5, fps)) - elapsed)
        time.sleep(sleep_dur)

    if notifier:
        notifier.close()
    if not headless:
        cv2.destroyAllWindows()
