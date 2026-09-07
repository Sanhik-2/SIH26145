"""
CHRONOS ALL-IN-ONE QR GATEWAY NODE (Runs on QR Node Laptop)
----------------------------------------------------------
1. Listens for telemetry from Nodes 1, 2, and 3 on port 9999.
2. In Terminal: Prints the live streaming packet logs & red host alerts (like Termux!).
3. On Screen: Displays the animated Optical QR Data Diode for the camera to scan!

Usage:
  python qr_gateway.py
"""

import socket
import json
import time
import threading
import numpy as np
import cv2
import qrcode

GATEWAY_IP = "0.0.0.0"
GATEWAY_PORT = 9999

log_buffer = []
buffer_lock = threading.Lock()
sequence_id = 1
total_received = 0
connected_nodes = {}

def packet_listener():
    """Listens for UDP packets from Nodes 1, 2, and 3 and prints live terminal logs."""
    global log_buffer, total_received, connected_nodes
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((GATEWAY_IP, GATEWAY_PORT))
    
    print("\n" + "=" * 60)
    print("   CHRONOS OPTICAL GATEWAY HUB ONLINE")
    print(f"   Listening on: 0.0.0.0:{GATEWAY_PORT}")
    print("   Waiting for Node 1, Node 2, and Node 3...")
    print("=" * 60 + "\n")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            payload = json.loads(data.decode("utf-8"))
            total_received += 1

            node_id = payload.get("node_id", 0)
            sender = payload.get("sender", f"Node {node_id}")
            event_type = payload.get("event_type", payload.get("type", "ROUTINE"))
            now = time.strftime("%H:%M:%S")

            if node_id not in connected_nodes:
                connected_nodes[node_id] = addr[0]
                print(f"[+] NODE CONNECTED: {sender} ({addr[0]})")

            # Check if an app (Notepad, Calc) was opened
            if event_type in ["APP_LAUNCH", "PROCESS_EXECUTION"]:
                app_name = payload.get("app", "Unauthorized Program")
                pid = payload.get("pid", "---")
                print(f"\n🚨 [APPLICATION LAUNCH DETECTED ON {sender.upper()}]")
                print(f"   Program : {app_name.upper()} (PID: {pid})")
                print(f"   Host IP : {addr[0]}")
                print(f"   Time    : {now}")
                print(f"   Status  : Encoded into Optical Diode QR Frame!\n")
            else:
                cpu = payload.get("cpu_pct", "--")
                ram = payload.get("ram_pct", "--")
                print(f"[{now}] #{total_received:04d} | {sender} ONLINE | CPU: {cpu}% | RAM: {ram}%")

            with buffer_lock:
                log_buffer.append(payload)

        except Exception:
            pass

def generate_qr_matrix(data_str, size=(450, 450)):
    """Generates a high-contrast QR image."""
    qr = qrcode.QRCode(
        version=4,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(data_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    mat = np.array(img, dtype=np.uint8)
    return cv2.resize(mat, size, interpolation=cv2.INTER_NEAREST)

def main():
    global log_buffer, sequence_id, total_received

    # Start listener thread
    threading.Thread(target=packet_listener, daemon=True).start()

    cv2.namedWindow("CHRONOS Optical Diode (QR Node)", cv2.WINDOW_NORMAL)

    while True:
        start_time = time.time()

        with buffer_lock:
            batch = list(log_buffer)
            log_buffer.clear()

        if not batch:
            batch = [{
                "node_id": 0,
                "sender": "Gateway",
                "receiver": "Enclave",
                "payload": "All Nodes Connected [Normal Telemetry]",
                "seq": sequence_id,
                "time": time.strftime("%H:%M:%S")
            }]

        payload = {
            "seq": sequence_id,
            "count": len(batch),
            "logs": batch[-2:]
        }

        qr_text = json.dumps(payload)
        qr_img = generate_qr_matrix(qr_text)

        canvas = np.zeros((650, 650, 3), dtype=np.uint8)
        canvas[20:470, 100:550] = qr_img

        cv2.putText(canvas, f"OPTICAL DATA DIODE: TRANSMITTING (SEQ #{sequence_id})", (40, 510), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(canvas, f"Total Ingested Packets: {total_received} | Active Nodes: {len(connected_nodes)}", (40, 545), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
        cv2.putText(canvas, "[PHOTONS ONLY -> ZERO RETURN PATH TO PRODUCTION]", (40, 585), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 120, 255), 2)
        cv2.putText(canvas, f"Latest: {batch[-1].get('sender')} -> {batch[-1].get('app', batch[-1].get('payload', ''))[:30]}", (40, 620), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        cv2.imshow("CHRONOS Optical Diode (QR Node)", canvas)

        sequence_id += 1

        elapsed = time.time() - start_time
        wait_ms = max(1, int((0.65 - elapsed) * 1000))
        if cv2.waitKey(wait_ms) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
