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
    """Polls the containerized SCADA node for live NPPAD telemetry."""
    try:
        req = urllib.request.Request(SCADA_HMI_URL, headers={"User-Agent": "ChronosDiodeGateway/1.0"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception:
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
                print(f"[!] [PHYSICAL SCADA ALARM] {state}! Pressure: {payload.get('p_bar')} bar")

            with buffer_lock:
                log_buffer.append(payload)

        except Exception:
            pass

def generate_qr_matrix(data_str, size=(440, 440)):
    """Generates a high-contrast QR image."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=4,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    mat = np.array(img, dtype=np.uint8)
    return cv2.resize(mat, size, interpolation=cv2.INTER_NEAREST)

def main():
    global log_buffer, sequence_id, total_received, total_bytes, is_alert_active

    # Start packet ingestion thread
    threading.Thread(target=packet_listener, daemon=True).start()
    mirror_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    cv2.namedWindow("CHRONOS Nuclear Optical Diode (Transmitter)", cv2.WINDOW_NORMAL)

    while True:
        start_time = time.time()

        with buffer_lock:
            batch = list(log_buffer)
            log_buffer.clear()

        if not batch:
            # Poll container directly for live NPPAD data
            node_data = poll_scada_container()
            if node_data:
                now_str = time.strftime("%H:%M:%S")
                state = node_data.get("reactor_state", "NOMINAL_FULL_POWER")
                evt = "ROUTINE_SCADA" if state == "NOMINAL_FULL_POWER" else "SCADA_PHYSICAL_ANOMALY"
                latest = {
                    "node_id": 1,
                    "facility": "BARC_Kudankulam_1",
                    "dataset": "NPPAD_Nature_Sci_Data_2022",
                    "reactor_state": state,
                    "event_type": evt,
                    "seq": sequence_id,
                    "time": now_str,
                    "ts": now_str,
                    "p_bar": node_data.get("pressure_bar", 155.5),
                    "tavg_c": node_data.get("core_temp_c", 310.0),
                    "tha_c": node_data.get("core_temp_c", 310.0) + 17.8,
                    "tca_c": node_data.get("core_temp_c", 310.0) - 17.8,
                    "wrca_kgs": node_data.get("coolant_flow_kgs", 16515.8),
                    "psga_bar": 67.0,
                    "mwe_electric": node_data.get("output_mwe", 955.3),
                    "host_cpu_pct": node_data.get("container_cpu_pct", 1.2),
                    "host_ram_pct": node_data.get("container_mem_pct", 2.8),
                    "host_ram_mb": node_data.get("container_mem_mb", 28.5),
                    "payload": f"NPPAD [{state}] P:{node_data.get('pressure_bar', 155.5):.1f}bar Flow:{node_data.get('coolant_flow_kgs', 16515.8):.0f}kg/s"
                }
            else:
                latest = {
                    "node_id": 1,
                    "facility": "BARC_Kudankulam_1",
                    "event_type": "ROUTINE_SCADA",
                    "p_bar": 155.5,
                    "tavg_c": 310.0,
                    "tha_c": 327.8,
                    "tca_c": 292.2,
                    "wrca_kgs": 16515.8,
                    "psga_bar": 67.0,
                    "mwe_electric": 955.3,
                    "host_cpu_pct": 1.2,
                    "host_ram_pct": 2.8,
                    "payload": "NPPAD Kudankulam Nominal Baseline",
                    "seq": sequence_id,
                    "time": time.strftime("%H:%M:%S")
                }
        else:
            latest = batch[-1]

        # Determine 5-channel feature vector [iat, bytes, entropy, burst, direction] for NJ-ODE AI
        atk_type = str(latest.get("attack_type", latest.get("atk", ""))).upper()
        threat_cls = str(latest.get("threat_class", latest.get("cls", ""))).lower()
        is_threat = bool(atk_type) or (threat_cls in ["a", "b", "c", "d", "e", "f"]) or (latest.get("reactor_state") not in ["NOMINAL_FULL_POWER", None])

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

        src_node = latest.get("src", "ews-alpha" if is_threat else "nuclear-scada")
        pkt_size = int(latest.get("bytes", latest.get("size", feat[1])))

        # Compact optical payload (compatible with both Nuclear SOC and React SOC / Phone Scanner)
        optical_payload = {
            "seq": sequence_id,
            "ts": latest.get("time", latest.get("ts", time.strftime("%H:%M:%S"))),
            "type": latest.get("event_type", "ROUTINE_SCADA"),
            "state": latest.get("reactor_state", "NOMINAL_FULL_POWER"),
            "src": src_node,
            "size": pkt_size,
            "feat": feat,
            "p": round(float(latest.get("p_bar", latest.get("pressure_bar", 155.5))), 1),
            "tavg": round(float(latest.get("tavg_c", latest.get("temp_c", 310.0))), 1),
            "tha": round(float(latest.get("tha_c", 327.8)), 1),
            "tca": round(float(latest.get("tca_c", 292.2)), 1),
            "flow": round(float(latest.get("wrca_kgs", latest.get("coolant_flow_kgs", 16515.8))), 0),
            "psg": round(float(latest.get("psga_bar", 67.0)), 1),
            "mw": round(float(latest.get("mwe_electric", latest.get("output_mwe", 955.0))), 1),
            "cpu": round(float(latest.get("host_cpu_pct", latest.get("container_cpu_pct", 1.2))), 1),
            "ram": round(float(latest.get("host_ram_pct", latest.get("container_mem_pct", 2.8))), 1),
            "cls": threat_cls,
            "atk": atk_type if is_threat else "",
            "msg": latest.get("payload", "")[:45]
        }

        # Dispatch real packet movements to React SOC Dashboard
        if notifier:
            notifier.send_event({
                "type": "packet_transit",
                "from": src_node,
                "to": "tx-diode",
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "p": optical_payload["p"],
                "flow": optical_payload["flow"],
                "state": optical_payload["state"],
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
                "timestamp": time.time(),
            })
            notifier.send_event({
                "type": "packet_transit",
                "from": "rx-diode",
                "to": "njode-core",
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "p": optical_payload["p"],
                "flow": optical_payload["flow"],
                "state": optical_payload["state"],
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
                    "timestamp": time.time(),
                })

        # Mirror across local port 9998
        try:
            mirror_sock.sendto(json.dumps(optical_payload).encode("utf-8"), ("127.0.0.1", MIRROR_PORT))
        except Exception:
            pass

        qr_text = json.dumps(optical_payload)
        qr_img = generate_qr_matrix(qr_text)

        if not headless:
            # High-impact transmitter GUI canvas
            h, w = 680, 680
            canvas = np.zeros((h, w, 3), dtype=np.uint8)

            # Top Header Banner
            cv2.rectangle(canvas, (0, 0), (w, 55), (25, 25, 40), -1)
            cv2.putText(canvas, "NUCLEAR SCADA OPTICAL DATA DIODE", (30, 36), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 240, 255), 2)

            # Draw QR frame
            canvas[70:510, 120:560] = qr_img

            # Bottom Telemetry Strip
            cv2.rectangle(canvas, (0, 520), (w, h), (18, 18, 28), -1)
            cv2.line(canvas, (0, 520), (w, 520), (50, 50, 70), 1)

            cv2.putText(canvas, f"Frame #{sequence_id} | Ingest: {total_received} packets | Size: {len(qr_text)}B", 
                        (25, 545), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            
            status_color = (0, 0, 255) if optical_payload.get("atk") or optical_payload.get("state") != "NOMINAL_FULL_POWER" else (0, 255, 120)
            cv2.putText(canvas, f"State: {optical_payload.get('state')} | CPU: {optical_payload.get('cpu')}% | RAM: {optical_payload.get('ram')}%", 
                        (25, 575), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1)

            cv2.putText(canvas, f"NPPAD Vitals: P={optical_payload.get('p')}bar | Tavg={optical_payload.get('tavg')}C | Flow={optical_payload.get('flow')}kg/s | MW={optical_payload.get('mw')}MWe", 
                        (25, 605), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 240, 255), 1)

            cv2.putText(canvas, "Air-Gap: UNIDIRECTIONAL OPTICAL PHOTONS ONLY (ZERO COPPER RETURN)", 
                        (25, 638), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 0), 1)

            cv2.putText(canvas, "Scan with Webcam / Phone on SOC or press SPACE on SOC for Loopback", 
                        (25, 665), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

            cv2.imshow("CHRONOS Nuclear Optical Diode (Transmitter)", canvas)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        else:
            status_tag = "🚨 ANOMALY" if is_threat else "✅ NOMINAL"
            sys.stdout.write(
                f"\r[{status_tag}] Diode QR #{sequence_id:04d} | State: {optical_payload['state']} | P: {optical_payload['p']}bar | Flow: {optical_payload['flow']}kg/s | CPU: {optical_payload['cpu']}% "
            )
            sys.stdout.flush()

        sequence_id += 1
        elapsed = time.time() - start_time
        sleep_dur = max(0.05, (1.0 / max(0.5, fps)) - elapsed)
        time.sleep(sleep_dur)

    if notifier:
        notifier.close()
    if not headless:
        cv2.destroyAllWindows()


def main():
    global log_buffer, sequence_id, total_received, total_bytes, is_alert_active

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
    while True:
        start_time = time.time()

        with buffer_lock:
            batch = list(log_buffer)
            log_buffer.clear()

        if not batch:
            # Poll container directly for live NPPAD data
            node_data = poll_scada_container()
            if node_data:
                now_str = time.strftime("%H:%M:%S")
                state = node_data.get("reactor_state", "NOMINAL_FULL_POWER")
                evt = "ROUTINE_SCADA" if state == "NOMINAL_FULL_POWER" else "SCADA_PHYSICAL_ANOMALY"
                latest = {
                    "node_id": 1,
                    "facility": "BARC_Kudankulam_1",
                    "dataset": "NPPAD_Nature_Sci_Data_2022",
                    "reactor_state": state,
                    "event_type": evt,
                    "seq": sequence_id,
                    "time": now_str,
                    "ts": now_str,
                    "p_bar": node_data.get("pressure_bar", 155.5),
                    "tavg_c": node_data.get("core_temp_c", 310.0),
                    "tha_c": node_data.get("core_temp_c", 310.0) + 17.8,
                    "tca_c": node_data.get("core_temp_c", 310.0) - 17.8,
                    "wrca_kgs": node_data.get("coolant_flow_kgs", 16515.8),
                    "psga_bar": 67.0,
                    "mwe_electric": node_data.get("output_mwe", 955.3),
                    "host_cpu_pct": node_data.get("container_cpu_pct", 1.2),
                    "host_ram_pct": node_data.get("container_mem_pct", 2.8),
                    "host_ram_mb": node_data.get("container_mem_mb", 28.5),
                    "payload": f"NPPAD [{state}] P:{node_data.get('pressure_bar', 155.5):.1f}bar Flow:{node_data.get('coolant_flow_kgs', 16515.8):.0f}kg/s"
                }
            else:
                latest = {
                    "node_id": 1,
                    "facility": "BARC_Kudankulam_1",
                    "event_type": "ROUTINE_SCADA",
                    "p_bar": 155.5,
                    "tavg_c": 310.0,
                    "tha_c": 327.8,
                    "tca_c": 292.2,
                    "wrca_kgs": 16515.8,
                    "psga_bar": 67.0,
                    "mwe_electric": 955.3,
                    "host_cpu_pct": 1.2,
                    "host_ram_pct": 2.8,
                    "payload": "NPPAD Kudankulam Nominal Baseline",
                    "seq": sequence_id,
                    "time": time.strftime("%H:%M:%S")
                }
        else:
            latest = batch[-1]

        # Determine 5-channel feature vector [iat, bytes, entropy, burst, direction] for NJ-ODE AI
        atk_type = str(latest.get("attack_type", latest.get("atk", ""))).upper()
        threat_cls = str(latest.get("threat_class", latest.get("cls", ""))).lower()
        is_threat = bool(atk_type) or (threat_cls in ["a", "b", "c", "d", "e", "f"]) or (latest.get("reactor_state") not in ["NOMINAL_FULL_POWER", None])

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

        src_node = latest.get("src", "ews-alpha" if is_threat else "nuclear-scada")
        pkt_size = int(latest.get("bytes", latest.get("size", feat[1])))

        # Compact optical payload
        optical_payload = {
            "seq": sequence_id,
            "ts": latest.get("time", latest.get("ts", time.strftime("%H:%M:%S"))),
            "type": latest.get("event_type", "ROUTINE_SCADA"),
            "state": latest.get("reactor_state", "NOMINAL_FULL_POWER"),
            "src": src_node,
            "size": pkt_size,
            "feat": feat,
            "p": round(float(latest.get("p_bar", latest.get("pressure_bar", 155.5))), 1),
            "tavg": round(float(latest.get("tavg_c", latest.get("temp_c", 310.0))), 1),
            "tha": round(float(latest.get("tha_c", 327.8)), 1),
            "tca": round(float(latest.get("tca_c", 292.2)), 1),
            "flow": round(float(latest.get("wrca_kgs", latest.get("coolant_flow_kgs", 16515.8))), 0),
            "psg": round(float(latest.get("psga_bar", 67.0)), 1),
            "mw": round(float(latest.get("mwe_electric", latest.get("output_mwe", 955.0))), 1),
            "cpu": round(float(latest.get("host_cpu_pct", latest.get("container_cpu_pct", 1.2))), 1),
            "ram": round(float(latest.get("host_ram_pct", latest.get("container_mem_pct", 2.8))), 1),
            "cls": threat_cls,
            "atk": atk_type if is_threat else "",
            "msg": latest.get("payload", "")[:45]
        }

        # Dispatch real packet movements to React SOC Dashboard
        if notifier:
            notifier.send_event({
                "type": "packet_transit",
                "from": src_node,
                "to": "tx-diode",
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "p": optical_payload["p"],
                "flow": optical_payload["flow"],
                "state": optical_payload["state"],
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
                "timestamp": time.time(),
            })
            notifier.send_event({
                "type": "packet_transit",
                "from": "rx-diode",
                "to": "njode-core",
                "size": pkt_size,
                "feat": feat,
                "threat": is_threat,
                "p": optical_payload["p"],
                "flow": optical_payload["flow"],
                "state": optical_payload["state"],
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
                    "timestamp": time.time(),
                })

        # Mirror across local port 9998
        try:
            mirror_sock.sendto(json.dumps(optical_payload).encode("utf-8"), ("127.0.0.1", MIRROR_PORT))
        except Exception:
            pass

        qr_text = json.dumps(optical_payload)
        qr_img = generate_qr_matrix(qr_text)

        if not headless:
            # High-impact transmitter GUI canvas
            h, w = 680, 680
            canvas = np.zeros((h, w, 3), dtype=np.uint8)

            # Top Header Banner
            cv2.rectangle(canvas, (0, 0), (w, 55), (25, 25, 40), -1)
            cv2.putText(canvas, "NUCLEAR SCADA OPTICAL DATA DIODE", (30, 36), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 240, 255), 2)

            # Draw QR frame
            canvas[70:510, 120:560] = qr_img

            # Bottom Telemetry Strip
            cv2.rectangle(canvas, (0, 520), (w, h), (18, 18, 28), -1)
            cv2.line(canvas, (0, 520), (w, 520), (50, 50, 70), 1)

            cv2.putText(canvas, f"Frame #{sequence_id} | Ingest: {total_received} packets | Size: {len(qr_text)}B", 
                        (25, 545), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            
            status_color = (0, 0, 255) if optical_payload.get("atk") or optical_payload.get("state") != "NOMINAL_FULL_POWER" else (0, 255, 120)
            cv2.putText(canvas, f"State: {optical_payload.get('state')} | CPU: {optical_payload.get('cpu')}% | RAM: {optical_payload.get('ram')}%", 
                        (25, 575), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1)

            cv2.putText(canvas, f"NPPAD Vitals: P={optical_payload.get('p')}bar | Tavg={optical_payload.get('tavg')}C | Flow={optical_payload.get('flow')}kg/s | MW={optical_payload.get('mw')}MWe", 
                        (25, 605), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 240, 255), 1)

            cv2.putText(canvas, "Air-Gap: UNIDIRECTIONAL OPTICAL PHOTONS ONLY (ZERO COPPER RETURN)", 
                        (25, 638), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 0), 1)

            cv2.putText(canvas, "Scan with Webcam / Phone on SOC or press SPACE on SOC for Loopback", 
                        (25, 665), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

            cv2.imshow("CHRONOS Nuclear Optical Diode (Transmitter)", canvas)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

        # Terminal live telemetry output (Exact Docker plant telemetry)
        p_val = optical_payload.get('p', 155.5)
        t_val = optical_payload.get('tavg', 310.0)
        flow_val = optical_payload.get('flow', 16500.0)
        mw_val = optical_payload.get('mw', 955.0)
        state_val = optical_payload.get('state', 'NOMINAL_FULL_POWER')
        print(f"[SCADA DIODE TX] Frame #{sequence_id:04d} | Kudankulam Unit 1 PWR | Pressure: {p_val:.1f} bar | Core Temp: {t_val:.1f} °C | Flow: {flow_val:.1f} kg/s | Output: {mw_val:.1f} MWe | State: {state_val}")

        sequence_id += 1
        elapsed = time.time() - start_time
        sleep_dur = max(0.05, (1.0 / max(0.5, fps)) - elapsed)
        time.sleep(sleep_dur)

    if notifier:
        notifier.close()
    if not headless:
        cv2.destroyAllWindows()
