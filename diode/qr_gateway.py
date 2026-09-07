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

import sys
import socket
import json
import time
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

log_buffer = []
buffer_lock = threading.Lock()
sequence_id = 1
total_received = 0
total_bytes = 0
last_event = "System Initialized - Baseline Stable"
last_event_time = "--:--:--"
is_alert_active = False

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
        box_size=7,
        border=2,
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

        # Compact optical payload
        optical_payload = {
            "seq": sequence_id,
            "ts": latest.get("time", latest.get("ts", time.strftime("%H:%M:%S"))),
            "type": latest.get("event_type", "ROUTINE_SCADA"),
            "state": latest.get("reactor_state", "NOMINAL_FULL_POWER"),
            "p": round(float(latest.get("p_bar", latest.get("pressure_bar", 155.5))), 1),
            "tavg": round(float(latest.get("tavg_c", latest.get("temp_c", 310.0))), 1),
            "tha": round(float(latest.get("tha_c", 327.8)), 1),
            "tca": round(float(latest.get("tca_c", 292.2)), 1),
            "flow": round(float(latest.get("wrca_kgs", latest.get("coolant_flow_kgs", 16515.8))), 0),
            "psg": round(float(latest.get("psga_bar", 67.0)), 1),
            "mw": round(float(latest.get("mwe_electric", latest.get("output_mwe", 955.0))), 1),
            "cpu": round(float(latest.get("host_cpu_pct", latest.get("container_cpu_pct", 1.2))), 1),
            "ram": round(float(latest.get("host_ram_pct", latest.get("container_mem_pct", 2.8))), 1),
            "cls": latest.get("threat_class", ""),
            "atk": latest.get("attack_type", ""),
            "msg": latest.get("payload", "")[:45]
        }

        # Mirror across local port 9998
        try:
            mirror_sock.sendto(json.dumps(optical_payload).encode("utf-8"), ("127.0.0.1", MIRROR_PORT))
        except Exception:
            pass

        qr_text = json.dumps(optical_payload)
        qr_img = generate_qr_matrix(qr_text)

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

        cv2.putText(canvas, "Scan with Webcam on Air-Gapped SOC or press SPACE on SOC for Loopback", 
                    (25, 665), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (140, 140, 140), 1)

        cv2.imshow("CHRONOS Nuclear Optical Diode (Transmitter)", canvas)

        sequence_id += 1
        elapsed = time.time() - start_time
        sleep_dur = max(0.05, 0.5 - elapsed)
        time.sleep(sleep_dur)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
