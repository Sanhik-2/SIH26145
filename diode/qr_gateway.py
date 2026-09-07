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

import argparse
import os
from pathlib import Path
import socket
import json
import sys
import time
import threading
import numpy as np
import cv2
import qrcode

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from features.extractor import Packet, shannon_entropy
from diode.protocol import decode_packet, decode_record

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
last_pkt_arrival = None

def packet_listener(port=INGEST_PORT, mirror_port=MIRROR_PORT):
    """Listens for UDP packets from Nuclear SCADA or Network Producer and queues for optical encoding."""
    global log_buffer, total_received, total_bytes, last_event, last_event_time, is_alert_active, last_pkt_arrival
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", port))

    mirror_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("\n" + "=" * 65)
    print("  CHRONOS: OPTICAL DATA DIODE TRANSMITTER GATEWAY ONLINE")
    print(f"  Ingest Port  : 0.0.0.0:{port} (Simplex Inbound)")
    print(f"  Mirror Port  : 127.0.0.1:{mirror_port} (Simplex Optical Loopback)")
    print(f"  Optical Out  : High-Contrast QR Photon Stream")
    print(f"  Air Gap      : STRICT ONE-WAY EGRESS (ZERO RETURN PATH)")
    print("=" * 65 + "\n")

    while True:
        try:
            data, addr = sock.recvfrom(65535)
            total_received += 1
            total_bytes += len(data)

            now = time.strftime("%H:%M:%S")
            now_t = time.time()
            iat = 1.0 if last_pkt_arrival is None else max(0.0001, now_t - last_pkt_arrival)
            last_pkt_arrival = now_t

            payload = None
            # 1. Try decoding JSON payload (SCADA, Host breach, Cyber attack)
            try:
                payload = json.loads(data.decode("utf-8"))
            except Exception:
                pass

            # 2. Try decoding binary packet / record from diode.protocol
            if payload is None:
                pkt = decode_packet(data)
                if pkt is not None:
                    if pkt.size == 0 and pkt.payload == b"EOS":
                        payload = {
                            "event_type": "EOS",
                            "payload": "EOS Sentinel",
                            "time": now,
                            "feat": [0.0, 0, 0.0, 0.0, 0],
                        }
                    else:
                        ent = shannon_entropy(pkt.payload) if pkt.payload else 0.0
                        payload = {
                            "event_type": "NETWORK_PACKET",
                            "t": round(pkt.t, 4),
                            "size": pkt.size,
                            "entropy": round(ent, 2),
                            "direction": getattr(pkt, "direction", 0),
                            "payload": f"Simplex IP Datagram ({pkt.size}B)",
                            "feat": [round(iat, 4), pkt.size, round(ent, 2), 1.0, getattr(pkt, "direction", 0)],
                            "time": now,
                        }
                else:
                    rec = decode_record(data)
                    if rec is not None:
                        t_s, iat_s, wire_bytes, entropy, direction, flow_hash = rec
                        payload = {
                            "event_type": "NETWORK_RECORD",
                            "t": round(t_s, 4),
                            "size": wire_bytes,
                            "entropy": round(entropy, 2),
                            "direction": direction,
                            "flow_hash": flow_hash,
                            "payload": f"Diode Record 15B ({wire_bytes}B)",
                            "feat": [round(iat_s, 4), wire_bytes, round(entropy, 2), 1.0, direction],
                            "time": now,
                        }

            if payload is None:
                continue

            event_type = payload.get("event_type", "ROUTINE_SCADA")

            # Attach standard 5-channel feature vector if not provided
            if "feat" not in payload:
                if event_type == "PROCESS_EXECUTION":
                    payload["feat"] = [0.01, 1024, 7.95, 10.0, 0]
                elif event_type == "CYBER_ATTACK":
                    atk = str(payload.get("attack_type", "")).upper()
                    if "EXFIL" in atk:
                        payload["feat"] = [0.04, 1400, 7.92, 8.0, 0]
                    elif "C2" in atk:
                        payload["feat"] = [1.002, 64, 4.20, 1.0, 0]
                    elif "DGA" in atk or "DNS" in atk:
                        payload["feat"] = [0.15, 220, 7.85, 2.0, 0]
                    elif "DDOS" in atk:
                        payload["feat"] = [0.005, 120, 1.10, 50.0, 1]
                    else:
                        payload["feat"] = [0.05, 512, 6.50, 4.0, 0]
                elif event_type == "SCADA_PHYSICAL_ANOMALY":
                    payload["feat"] = [0.10, 400, 5.80, 3.0, 0]
                else:
                    payload["feat"] = [round(iat, 4), 280, 3.80, 1.0, 0]

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

            elif event_type in ("NETWORK_PACKET", "NETWORK_RECORD"):
                last_event = f"NET: {payload.get('payload')}"
                last_event_time = now
                f = payload["feat"]
                print(f"[{now}] #{total_received:04d} Network Packet | IAT:{f[0]}s | Bytes:{f[1]}B | Ent:{f[2]} | Burst:{f[3]} | Dir:{f[4]}")

            else:
                temp = payload.get("temp_c", payload.get("temp", "--"))
                press = payload.get("pressure_bar", payload.get("press", "--"))
                freq = payload.get("grid_freq_hz", payload.get("freq", "--"))
                cpu = payload.get("host_cpu_pct", payload.get("cpu", "--"))
                print(f"[{now}] #{total_received:04d} SCADA Telemetry | Core: {temp}C | P: {press}bar | Grid: {freq}Hz | Host CPU: {cpu}%")

            with buffer_lock:
                log_buffer.append(payload)

        except Exception as e:
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

    parser = argparse.ArgumentParser(description="CHRONOS Optical Data Diode QR Gateway")
    parser.add_argument("--port", type=int, default=INGEST_PORT, help=f"Ingest UDP port (default: {INGEST_PORT})")
    parser.add_argument("--mirror-port", type=int, default=MIRROR_PORT, help=f"Mirror UDP port (default: {MIRROR_PORT})")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display window")
    parser.add_argument("--fps", type=float, default=2.0, help="Optical frame rate (default: 2.0 fps)")
    args = parser.parse_args()

    headless = args.headless or not os.environ.get("DISPLAY")
    interval = 1.0 / max(0.1, args.fps)

    mirror_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Start packet ingestion thread
    threading.Thread(target=packet_listener, args=(args.port, args.mirror_port), daemon=True).start()

    if not headless:
        try:
            cv2.namedWindow("CHRONOS Nuclear Optical Diode (Transmitter)", cv2.WINDOW_NORMAL)
        except Exception as e:
            print(f"[!] Warning: Failed to open OpenCV window ({e}). Switching to headless mode.")
            headless = True

    print(f"[*] Optical Transmitter loop active (FPS: {args.fps:.1f}, Headless: {headless})")

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
                "feat": [1.05, 120, 3.45, 1.0, 0],
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
            "feat": latest.get("feat", [1.05, 120, 3.45, 1.0, 0]),
            "temp": latest.get("temp_c", latest.get("temp", 295.4)),
            "press": latest.get("pressure_bar", latest.get("press", 155.0)),
            "freq": latest.get("grid_freq_hz", latest.get("freq", 50.00)),
            "mw": latest.get("power_mw", latest.get("mw", 880.0)),
            "cpu": latest.get("host_cpu_pct", latest.get("cpu", 10.0)),
            "ram": latest.get("host_ram_pct", latest.get("ram", 45.0)),
            "app": latest.get("app", ""),
            "atk": latest.get("attack_type", latest.get("atk", "")),
            "msg": latest.get("payload", latest.get("msg", ""))[:45]
        }

        # Broadcast mirror locally for loopback receiver
        try:
            mirror_sock.sendto(json.dumps(optical_payload).encode("utf-8"), ("127.0.0.1", args.mirror_port))
        except Exception:
            pass

        qr_text = json.dumps(optical_payload)
        qr_img = generate_qr_matrix(qr_text)

        if not headless:
            h, w = 680, 680
            canvas = np.zeros((h, w, 3), dtype=np.uint8)

            # Top Header Banner
            cv2.rectangle(canvas, (0, 0), (w, 55), (25, 25, 40), -1)
            cv2.putText(canvas, "OPTICAL DATA DIODE TRANSMITTER", (30, 36), 
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

            elapsed = time.time() - start_time
            wait_ms = max(1, int((interval - elapsed) * 1000))
            if cv2.waitKey(wait_ms) & 0xFF == ord('q'):
                break
        else:
            elapsed = time.time() - start_time
            wait_s = max(0.01, interval - elapsed)
            time.sleep(wait_s)

        sequence_id += 1

    if not headless:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
