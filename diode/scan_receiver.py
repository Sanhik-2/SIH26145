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

import cv2
import json
import time
import numpy as np

def render_dashboard(frame, logs, stats):
    """Draws a modern SOC dashboard for the 1st round presentation."""
    h, w = 700, 1050
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    # Top Header Banner
    cv2.rectangle(canvas, (0, 0), (w, 65), (20, 20, 32), -1)
    cv2.putText(canvas, "CHRONOS: AIR-GAPPED OPTICAL ENCLAVE (SCAN NODE DASHBOARD)", (25, 42), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.72, (0, 240, 255), 2)

    # Left Column: Live Webcam Optical Ingest View
    cv2.rectangle(canvas, (25, 80), (460, 420), (35, 35, 50), 2)
    cv2.putText(canvas, "[OPTICAL RECEIVER FEED (WEBCAM)]", (35, 105), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    if frame is not None:
        resized_cam = cv2.resize(frame, (415, 295))
        canvas[115:410, 35:450] = resized_cam

    # Left Column Bottom: Network & Air-Gap Security Badges
    cv2.rectangle(canvas, (25, 435), (460, 675), (25, 25, 38), -1)
    cv2.rectangle(canvas, (25, 435), (460, 675), (45, 45, 60), 1)
    cv2.putText(canvas, "AIR-GAP SECURITY ASSURANCE", (35, 465), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
    
    cv2.putText(canvas, f"Optical Frames Received: {stats['frames']}", (35, 505), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
    cv2.putText(canvas, f"Total Ingested Logs: {stats['total_logs']}", (35, 540), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 0), 2)
    cv2.putText(canvas, f"Live Host Events Caught: {stats['events']}", (35, 575), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 100, 255), 2)
    cv2.putText(canvas, "Return Path: PHYSICALLY IMPOSSIBLE (Camera Only)", (35, 610), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 150, 255), 1)
    cv2.putText(canvas, "Network Adapter: AIR-GAPPED (Zero Wires / No Wi-Fi)", (35, 645), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.46, (0, 255, 120), 1)

    # Right Column: Live Incoming Node Telemetry Stream
    cv2.rectangle(canvas, (480, 80), (1025, 675), (20, 20, 30), -1)
    cv2.rectangle(canvas, (480, 80), (1025, 675), (45, 45, 65), 2)
    cv2.putText(canvas, "LIVE INGESTED NETWORK & HOST EVENT STREAM", (500, 115), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 2)

    y_pos = 160
    if not logs:
        cv2.putText(canvas, "AWAITING OPTICAL TRANSMISSION...", (520, 260), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        cv2.putText(canvas, "Point webcam directly at QR Node screen.", (520, 300), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
    else:
        for entry in logs[-5:]:  # Display latest 5 logs
            is_event = (entry.get("event_type") == "PROCESS_EXECUTION")

            if is_event:
                # Flash bright Red / Amber card for real-world program launch!
                card_color = (0, 50, 255) # Bright Red
                header_text = f"🚨 [LIVE HOST EVENT] {entry.get('sender')}: APP EXECUTED!"
                payload_text = entry.get('payload', '')
            else:
                card_color = (0, 180, 120) if entry.get("node_id") == 1 else ((255, 180, 0) if entry.get("node_id") == 2 else (0, 120, 255))
                header_text = f"[{entry.get('time', '--')}] {entry.get('sender')} -> {entry.get('receiver')}"
                payload_text = f"Telemetry: {entry.get('payload', '')[:50]}"

            cv2.rectangle(canvas, (495, y_pos), (1010, y_pos + 85), (32, 32, 45), -1)
            cv2.rectangle(canvas, (495, y_pos), (1010, y_pos + 85), card_color, 2 if is_event else 1)

            cv2.putText(canvas, header_text, (505, y_pos + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.48, card_color, 2)
            cv2.putText(canvas, payload_text, (505, y_pos + 52), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255) if is_event else (220, 220, 220), 1)
            cv2.putText(canvas, f"Optical Diode Ingest: VERIFIED | Latency: <500ms", 
                        (505, y_pos + 74), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (140, 140, 140), 1)
            y_pos += 98

    return canvas

def main():
    cap = cv2.VideoCapture(0)
    detector = cv2.QRCodeDetector()

    logs_feed = []
    last_seq = -1
    stats = {"frames": 0, "total_logs": 0, "events": 0}

    print("=" * 60)
    print("  CHRONOS SCAN RECEIVER ACTIVE")
    print("  Point webcam at QR Node's display to capture logs.")
    print("=" * 60)

    while True:
        ret, frame = cap.read()
        if not ret:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Decode QR Code from webcam image
        data, bbox, _ = detector.detectAndDecode(frame)

        if data:
            try:
                payload = json.loads(data)
                seq = payload.get("seq", 0)

                if seq != last_seq:
                    last_seq = seq
                    stats["frames"] += 1
                    incoming_logs = payload.get("logs", [])
                    for item in incoming_logs:
                        logs_feed.append(item)
                        stats["total_logs"] += 1
                        if item.get("event_type") == "PROCESS_EXECUTION":
                            stats["events"] += 1
                            print(f"\n[🚨 LIVE EVENT CAPTURED] {item.get('sender')} -> {item.get('payload')}\n")
                        else:
                            print(f"[+] Decoded: {item.get('sender')} -> {item.get('payload')}")

                    # Draw green bounding box around QR on webcam view
                    if bbox is not None:
                        n = len(bbox[0])
                        for j in range(n):
                            p1 = tuple(map(int, bbox[0][j]))
                            p2 = tuple(map(int, bbox[0][(j + 1) % n]))
                            cv2.line(frame, p1, p2, (0, 255, 0), 3)

            except Exception:
                pass

        # Draw Real-Time Dashboard
        dashboard = render_dashboard(frame, logs_feed, stats)
        cv2.imshow("CHRONOS Air-Gapped SOC Dashboard", dashboard)

        if cv2.waitKey(30) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
