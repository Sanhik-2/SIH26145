"""
CHRONOS GATEWAY DIODE (Runs on Laptop 5)
---------------------------------------
1. Listens for incoming telemetry & traffic from Laptops 1, 2, 3, and 4.
2. Aggregates flows into IPFIX/NetFlow-style records (Entropy, IAT, DNS, Rates).
3. Signs every frame using Cryptographic Hash Chaining (Blockchain chain-of-custody).
4. Multiplexes data into a High-Density RGB Chromatic QR Code and flashes on screen.
"""

import socket
import json
import time
import sys
import hashlib
import threading
import math
import numpy as np
import cv2
import qrcode

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Local Gateway Configuration
GATEWAY_IP = "0.0.0.0"       # Listen on all interfaces
GATEWAY_PORT = 9999          # Port where nodes & attacker send traffic

# Global State for Traffic Aggregation
traffic_buffer = []
buffer_lock = threading.Lock()
prev_frame_hash = "0000000000000000000000000000000000000000000000000000000000000000"
sequence_id = 100

def calculate_entropy(ip_list):
    """Calculates Shannon Entropy of Source IPs (Spikes during DDoS Spoofing)."""
    if not ip_list:
        return 0.0
    counts = {}
    for ip in ip_list:
        counts[ip] = counts.get(ip, 0) + 1
    total = len(ip_list)
    entropy = 0.0
    for count in counts.values():
        p = count / total
        entropy -= p * math.log2(p)
    return round(entropy, 2)

def packet_listener():
    """Listens for UDP packets from all laptops on the local Wi-Fi."""
    global traffic_buffer
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((GATEWAY_IP, GATEWAY_PORT))
    print(f"[*] Gateway Diode listening on port {GATEWAY_PORT}...")

    while True:
        try:
            data, addr = sock.recvfrom(4096)
            payload = json.loads(data.decode("utf-8"))
            payload["recv_time"] = time.time()
            with buffer_lock:
                traffic_buffer.append(payload)
        except Exception as e:
            pass

def make_qr_channel(text, version=6, size=(400, 400)):
    """Generates a grayscale QR image for a single color channel."""
    qr = qrcode.QRCode(
        version=version,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=3,
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("L")
    mat = np.array(img, dtype=np.uint8)
    return cv2.resize(mat, size, interpolation=cv2.INTER_NEAREST)

def run_optical_emitter():
    """Aggregates traffic every 400ms, binds blockchain hash, and renders RGB QR."""
    global traffic_buffer, prev_frame_hash, sequence_id

    # Create full-screen window for Laptop 5 display
    cv2.namedWindow("CHRONOS Optical Diode Emitter (Laptop 5)", cv2.WINDOW_NORMAL)

    while True:
        start_t = time.time()

        # Step 1: Snapshot and clear recent buffer
        with buffer_lock:
            current_batch = list(traffic_buffer)
            traffic_buffer.clear()

        # If no traffic, create a baseline heartbeat packet
        if not current_batch:
            current_batch = [{
                "src": "192.168.1.10", "dst": "192.168.1.5",
                "type": "HEARTBEAT", "proto": "TCP", "bytes": 64,
                "domain": "nldc.grid.gov.in", "ja4": "t13d1516h2_benign"
            }]

        # Step 2: Compute flow statistics
        src_ips = [p.get("src", "127.0.0.1") for p in current_batch]
        entropy = calculate_entropy(src_ips)
        total_packets = len(current_batch)
        total_bytes = sum([p.get("bytes", 64) for p in current_batch])

        # Step 3: Split telemetry across RGB streams
        # 🔴 RED CHANNEL: Volumetric DDoS & Entropy stats
        stream_r = {
            "seq": sequence_id,
            "pkts": total_packets,
            "bytes": total_bytes,
            "entropy": entropy,
            "prev": prev_frame_hash[:8]
        }

        # 🟢 GREEN CHANNEL: C2 Beaconing & DNS stats
        recent_domains = [p.get("domain", "") for p in current_batch if "domain" in p]
        stream_g = {
            "seq": sequence_id,
            "domains": recent_domains[:3],
            "iats": [round(current_batch[i]["recv_time"] - current_batch[i-1]["recv_time"], 3) 
                     for i in range(1, min(4, len(current_batch)))],
            "prev": prev_frame_hash[:8]
        }

        # 🔵 BLUE CHANNEL: Encrypted TLS JA4 & Exfiltration stats
        recent_ja4 = [p.get("ja4", "") for p in current_batch if "ja4" in p]
        stream_b = {
            "seq": sequence_id,
            "ja4": recent_ja4[:2],
            "targets": list(set([p.get("dst", "") for p in current_batch]))[:3],
            "prev": prev_frame_hash[:8]
        }

        # Step 4: Compute Blockchain Hash of this frame
        frame_payload = json.dumps({"r": stream_r, "g": stream_g, "b": stream_b, "prev": prev_frame_hash}, sort_keys=True)
        current_frame_hash = hashlib.sha256(frame_payload.encode()).hexdigest()

        # Step 5: Render RGB Multiplexed Chromatic QR Code
        str_r = json.dumps(stream_r)
        str_g = json.dumps(stream_g)
        str_b = json.dumps(stream_b)

        qr_r = make_qr_channel(str_r)
        qr_g = make_qr_channel(str_g)
        qr_b = make_qr_channel(str_b)

        # Merge channels into BGR color image
        color_frame = cv2.merge([qr_b, qr_g, qr_r])

        # Add visual HUD overlay showing status
        canvas = np.zeros((650, 600, 3), dtype=np.uint8)
        canvas[0:400, 100:500] = color_frame
        cv2.putText(canvas, f"OPTICAL DIODE EMITTER (SEQ: {sequence_id})", (40, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 255), 2)
        cv2.putText(canvas, f"Hash: {current_frame_hash[:24]}...", (40, 475), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        cv2.putText(canvas, f"Packets/sec: {total_packets * 2.5:.0f}  |  IP Entropy: {entropy}", (40, 510), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
        cv2.putText(canvas, f"[PHOTONS TRANSMITTING -> ZERO RETURN PATH]", (40, 560), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)

        cv2.imshow("CHRONOS Optical Diode Emitter (Laptop 5)", canvas)

        # Update Blockchain state
        prev_frame_hash = current_frame_hash
        sequence_id += 1

        # Maintain 2.5 Hz (400ms refresh period)
        elapsed = time.time() - start_t
        wait_ms = max(1, int((0.40 - elapsed) * 1000))
        if cv2.waitKey(wait_ms) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    # Start packet listener in background thread
    listener_thread = threading.Thread(target=packet_listener, daemon=True)
    listener_thread.start()

    # Start optical visual emitter
    run_optical_emitter()
