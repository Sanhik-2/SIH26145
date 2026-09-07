"""
CHRONOS: NUCLEAR SCADA OPTICAL DATA DIODE (TRANSMITTER GATEWAY)
--------------------------------------------------------------
Enforces physical one-way air gap egress from Nuclear SCADA Enclave:
1. Ingests UDP simplex telemetry from the Nuclear SCADA Node on port 9999.
2. In Terminal: Displays live transmission logs & flags immediate security events.
3. On Screen: Renders an animated high-contrast Optical QR Stream for the receiver.
4. Broadcasts local simplex mirror on port 9998 (enables instant single-laptop SOC testing).

Usage:
  python diode/qr_gateway.py
"""

import socket
import json
import time
import threading
import numpy as np
import cv2
import qrcode

INGEST_PORT = 9999
MIRROR_PORT = 9998

log_buffer = []
buffer_lock = threading.Lock()
sequence_id = 1
total_received = 0
total_bytes = 0
last_event = "System Initialized - Baseline Stable"
last_event_time = "--:--:--"
is_alert_active = False

def packet_listener():
    """Listens for UDP packets from Nuclear SCADA and queues for optical encoding."""
    global log_buffer, total_received, total_bytes, last_event, last_event_time, is_alert_active
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", INGEST_PORT))

    mirror_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\n" + "=" * 65)
    print("  CHRONOS: NUCLEAR SCADA OPTICAL DIODE GATEWAY ONLINE")
    print(f"  Ingest Port  : 0.0.0.0:{INGEST_PORT} (Simplex Inbound from SCADA)")
    print(f"  Optical Out  : High-Contrast QR Photon Stream on Screen")
    print(f"  Air Gap      : STRICT ONE-WAY EGRESS (ZERO RETURN PATH)")
    print("=" * 65 + "\n")

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

            if event_type == "PROCESS_EXECUTION":
                is_alert_active = True
                app = payload.get("app", "Unauthorized Binary")
                pid = payload.get("pid", "---")
                last_event = f"HOST BREACH: '{app}' (PID: {pid})"
                last_event_time = now
                print(f"\n🚨 [CRITICAL HOST BREACH ENCODED TO DIODE]")
                print(f"   Unauthorized Process : {app.upper()} (PID: {pid})")
                print(f"   Origin Host          : {addr[0]}")
                print(f"   Timestamp            : {now}")
                print(f"   Action               : Blasting Optical Alert Frame across Air-Gap!\n")

            elif event_type == "CYBER_ATTACK":
                is_alert_active = True
                atk = payload.get("attack_type", "ANOMALY")
                last_event = f"CYBER ATTACK: {atk}"
                last_event_time = now
                print(f"\n⚡ [CYBER THREAT ENCODED TO DIODE] Threat: {atk} | Time: {now}\n")

            elif event_type == "SCADA_PHYSICAL_ANOMALY":
                is_alert_active = True
                last_event = "VALVE TAMPERING / CORE OVERHEAT"
                last_event_time = now
                print(f"\n⚠️ [PHYSICAL SCADA ALARM] Coolant Valve Trip! Temp: {payload.get('temp')}C\n")

            else:
                temp = payload.get("temp_c", "--")
                press = payload.get("pressure_bar", "--")
                freq = payload.get("grid_freq_hz", "--")
                cpu = payload.get("host_cpu_pct", "--")
                print(f"[{now}] #{total_received:04d} SCADA Telemetry | Core: {temp}C | P: {press}bar | Grid: {freq}Hz | Host CPU: {cpu}%")

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

    cv2.namedWindow("CHRONOS Nuclear Optical Diode (Transmitter)", cv2.WINDOW_NORMAL)

    while True:
        start_time = time.time()

        with buffer_lock:
            batch = list(log_buffer)
            log_buffer.clear()

        if not batch:
            batch = [{
                "node_id": 1,
                "facility": "BARC_Unit_1",
                "event_type": "ROUTINE_SCADA",
                "temp_c": 295.4,
                "pressure_bar": 155.0,
                "grid_freq_hz": 50.00,
                "power_mw": 880.0,
                "host_cpu_pct": 12.4,
                "payload": "Nominal Reactor Steady State",
                "seq": sequence_id,
                "time": time.strftime("%H:%M:%S")
            }]

        # Compact optical payload structure
        latest = batch[-1]
        optical_payload = {
            "seq": sequence_id,
            "ts": latest.get("time", time.strftime("%H:%M:%S")),
            "type": latest.get("event_type", "ROUTINE_SCADA"),
            "temp": latest.get("temp_c", 295.4),
            "press": latest.get("pressure_bar", 155.0),
            "freq": latest.get("grid_freq_hz", 50.00),
            "mw": latest.get("power_mw", 880.0),
            "cpu": latest.get("host_cpu_pct", 10.0),
            "ram": latest.get("host_ram_pct", 45.0),
            "app": latest.get("app", ""),
            "atk": latest.get("attack_type", ""),
            "msg": latest.get("payload", "")[:45]
        }

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

        # Outer border around QR: Green for normal, bright Red if alert
        border_color = (0, 0, 255) if is_alert_active else (0, 255, 120)
        cv2.rectangle(canvas, (116, 66), (564, 514), border_color, 3)

        # Status HUD below QR
        cv2.rectangle(canvas, (20, 530), (w - 20, 660), (20, 20, 30), -1)
        cv2.rectangle(canvas, (20, 530), (w - 20, 660), (45, 45, 60), 1)

        cv2.putText(canvas, f"OPTICAL EMISSION SEQ: #{sequence_id:06d} | FRAME READY", (35, 555), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
        cv2.putText(canvas, f"Total Ingested Telemetry: {total_received} pkts ({total_bytes / 1024:.1f} KB)", (35, 580), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 255, 200), 1)
        cv2.putText(canvas, "CHANNEL SECURITY: PHOTONS ONLY | ZERO INBOUND RETURN PATH", (35, 608), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 150, 255), 2)
        cv2.putText(canvas, f"Latest Event: [{last_event_time}] {last_event[:42]}", (35, 638), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 80, 255) if is_alert_active else (180, 180, 180), 1)

        cv2.imshow("CHRONOS Nuclear Optical Diode (Transmitter)", canvas)

        sequence_id += 1

        elapsed = time.time() - start_time
        wait_ms = max(1, int((0.6 - elapsed) * 1000))
        if cv2.waitKey(wait_ms) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
