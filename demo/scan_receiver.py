"""
demo/scan_receiver.py — Scanner side AI receiver behind the hardware / optical data diode.

Listens on simplex UDP socket (representing optical receiver / scanner feed).
Ingests packets into LiveFeeder, evaluates sliding windows, and tails alerts into alerts.jsonl.
Run:
  python demo/scan_receiver.py
"""
import argparse
import json
from pathlib import Path
import socket
import struct
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure repository root is on sys.path regardless of execution directory
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import torch

from features.extractor import Packet
from diode.protocol import decode_packet
from features.windowing import LiveFeeder
from models.njode import NJODE


def main():
    parser = argparse.ArgumentParser(description="CHRONOS Diode Scanner & AI Live Feeder")
    parser.add_argument("--mode", choices=["udp", "qr"], default="udp", help="Ingest mode: 'udp' socket or 'qr' optical diode")
    parser.add_argument("--source", choices=["camera", "loopback"], default="loopback", help="QR source: 'camera' (webcam) or 'loopback' (mirrored simplex UDP)")
    parser.add_argument("--camera-id", type=int, default=0, help="Webcam device ID (default: 0)")
    parser.add_argument("--host", default="127.0.0.1", help="UDP listen host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=9999, help="UDP listen port (default: 9999)")
    parser.add_argument("--checkpoint", default="checkpoints/njode_telemetry.pt", help="Path to versioned NJ-ODE checkpoint")
    parser.add_argument("--alert-log", default="alerts.jsonl", help="Output file for streaming alerts")
    parser.add_argument("--window-s", type=float, default=10.0, help="Sliding window width in seconds")
    parser.add_argument("--stride-s", type=float, default=2.0, help="Sliding stride in seconds")
    parser.add_argument("--hysteresis-n", type=int, default=2, help="Hysteresis confirmations required")
    parser.add_argument("--hysteresis-m", type=int, default=3, help="Hysteresis sliding window length")
    parser.add_argument("--tau", type=float, default=None, help="Optional manual threshold override")
    parser.add_argument("--device", default="cpu", help="Inference device (cpu or cuda)")
    args = parser.parse_args()

    print("=" * 74)
    print("🛡️ CHRONOS SCANNER SIDE AI INGESTION ENGINE (RECEIVER)")
    print("=" * 74)
    print(f"Loading versioned model from: {args.checkpoint}")
    model = NJODE.load(args.checkpoint, device=args.device)

    # If manual tau or checkpoint tau < 2.0 (pre-evaluation default), set canonical tau
    if args.tau is not None:
        model.threshold.copy_(torch.tensor(args.tau))
    elif model.threshold.item() < 2.0:
        model.threshold.copy_(torch.tensor(2.810))

    tau = float(model.threshold.item())
    print(f"Model Version:         v{getattr(model, 'version', '1.1')}")
    print(f"Detection Threshold τ: {tau:.4f}")
    print(f"Window / Stride:       {args.window_s:.1f} s / {args.stride_s:.1f} s")
    print(f"Hysteresis Policy:     {args.hysteresis_n}-of-{args.hysteresis_m} windows")
    print(f"Ingestion Mode:        {args.mode.upper()} (Source: {args.source if args.mode == 'qr' else f'udp://{args.host}:{args.port}'})")
    print(f"Streaming alerts to:   {args.alert_log}")
    print("=" * 74)

    # Initialize / truncate alerts.jsonl for fresh demo session
    alert_path = Path(args.alert_log)
    alert_path.parent.mkdir(parents=True, exist_ok=True)
    with open(alert_path, "w") as f:
        pass  # clear old alerts

    feeder = LiveFeeder(
        model=model,
        window_s=args.window_s,
        stride_s=args.stride_s,
        hysteresis_n=args.hysteresis_n,
        hysteresis_m=args.hysteresis_m,
        device=args.device,
    )

    pkt_count = 0

    if args.mode == "qr":
        # --- Optical QR Code Ingestion Mode ---
        import cv2
        detector = cv2.QRCodeDetector()
        last_seq = -1

        cap = None
        source_mode = args.source
        if source_mode == "camera":
            try:
                cap = cv2.VideoCapture(args.camera_id)
                if not cap.isOpened():
                    print(f"[!] Warning: Cannot open camera {args.camera_id}. Falling back to loopback port 9998.")
                    source_mode = "loopback"
            except Exception as e:
                print(f"[!] Warning: Camera error ({e}). Falling back to loopback port 9998.")
                source_mode = "loopback"

        loop_sock = None
        if source_mode == "loopback":
            loop_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            loop_sock.bind(("127.0.0.1", 9998))
            loop_sock.settimeout(0.5)

        print(f"[*] Optical QR Ingestion ACTIVE via {source_mode.upper()}... (Ctrl+C to stop)\n")

        try:
            while True:
                payload = None
                if source_mode == "camera" and cap is not None:
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        data, _, _ = detector.detectAndDecode(frame)
                        if data:
                            try:
                                payload = json.loads(data)
                            except Exception:
                                pass
                    time.sleep(0.05)
                else:
                    try:
                        raw, _ = loop_sock.recvfrom(65535)
                        payload = json.loads(raw.decode("utf-8"))
                    except (socket.timeout, Exception):
                        continue

                if not payload:
                    continue

                seq = payload.get("seq", -1)
                if seq == last_seq and last_seq != -1:
                    continue
                last_seq = seq

                # Convert optical frame payload into continuous Packet stream for NJ-ODE
                feat = payload.get("feat", [1.0, 120, 3.5, 1.0, 0])
                pkt_size = int(feat[1]) if len(feat) > 1 else 120
                direction = int(feat[4]) if len(feat) > 4 else 0
                msg_bytes = payload.get("msg", "optical").encode("utf-8")
                pkt = Packet(t=time.time(), size=pkt_size, payload=msg_bytes, direction=direction)

                # Flag immediate host breach alert if critical process execution was caught
                if payload.get("type") == "PROCESS_EXECUTION":
                    app = payload.get("app", "Unauthorized Binary")
                    now_str = time.strftime("%H:%M:%S")
                    host_record = {
                        "ts": now_str,
                        "window_t0": round(time.time(), 2),
                        "window_t1": round(time.time() + 1.0, 2),
                        "peak_score": 999.0,
                        "threshold": tau,
                        "is_anomaly": True,
                        "confirmed": True,
                        "attribution": {
                            "top_channel": "host_sentry",
                            "threat_type": f"HOST BREACH: {app}",
                            "channel_errors": {"host_sentry": 1.0}
                        },
                    }
                    with open(alert_path, "a") as f:
                        f.write(json.dumps(host_record) + "\n")
                    print(f"🚨 \033[91m[HOST INTRUSION BREACH]\033[0m Caught via Optical QR: {app.upper()}")

                pkt_count += 1
                alerts = feeder.ingest_packet(pkt)
                for a in alerts:
                    _process_alert(a, alert_path, tau)

        except KeyboardInterrupt:
            print("\n\nStopping optical scanner receiver...")
        finally:
            if cap is not None:
                cap.release()
            if loop_sock is not None:
                loop_sock.close()
            print(f"[✓] Optical receiver stopped. Ingested {pkt_count} optical frames.")

    else:
        # --- Standard UDP Network Ingestion Mode ---
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((args.host, args.port))
        sock.settimeout(1.0)

        print(f"Awaiting packet stream on udp://{args.host}:{args.port}... (Ctrl+C to stop)\n")

        try:
            while True:
                try:
                    data, addr = sock.recvfrom(65535)
                except socket.timeout:
                    continue

                pkt = None
                # Support binary packet frame
                pkt = decode_packet(data)

                # Or JSON frame with feat
                if pkt is None:
                    try:
                        j_pay = json.loads(data.decode("utf-8"))
                        feat = j_pay.get("feat", [1.0, 120, 3.5, 1.0, 0])
                        pkt = Packet(t=time.time(), size=int(feat[1]), payload=b"json_telemetry", direction=int(feat[4]))
                    except Exception:
                        continue

                # End of stream sentinel
                if pkt.size == 0 and pkt.payload == b"EOS":
                    print("\n[i] Received End-of-Stream sentinel. Flushing trailing windows...")
                    trailing_alerts = feeder.flush()
                    for a in trailing_alerts:
                        _process_alert(a, alert_path, tau)
                    continue

                pkt_count += 1
                alerts = feeder.ingest_packet(pkt)
                for a in alerts:
                    _process_alert(a, alert_path, tau)

        except KeyboardInterrupt:
            print("\n\nStopping scanner receiver...")
        finally:
            sock.close()
            print(f"[✓] Receiver stopped. Processed {pkt_count} packets.")


def _process_alert(alert, alert_path: Path, tau: float):
    attr = alert.attribution or {}
    ch = attr.get("top_channel", "—")
    threat = attr.get("threat_type", "—")

    record = {
        "ts": time.strftime("%H:%M:%S"),
        "window_t0": round(alert.window_t0, 2),
        "window_t1": round(alert.window_t1, 2),
        "peak_score": round(alert.peak_score, 4),
        "threshold": round(alert.threshold, 4),
        "is_anomaly": alert.is_anomaly,
        "confirmed": alert.confirmed,
        "attribution": alert.attribution,
    }

    with open(alert_path, "a") as f:
        f.write(json.dumps(record) + "\n")

    win_label = f"[{alert.window_t0:4.1f}s -> {alert.window_t1:4.1f}s]"
    if alert.confirmed:
        print(f"🚨 \033[91m[ATTACK CONFIRMED]\033[0m {win_label} Score = {alert.peak_score:7.2f} > τ = {tau:.2f} | Threat: {threat} ({ch})")
    elif alert.is_anomaly:
        print(f"⚠️  \033[93m[SUSPECTED ALERT ]\033[0m {win_label} Score = {alert.peak_score:7.2f} > τ = {tau:.2f} | Pre-confirmation (stride 1/2)")
    else:
        print(f"✅ \033[92m[PASSIVE CALM    ]\033[0m {win_label} Score = {alert.peak_score:7.2f} < τ = {tau:.2f}")


if __name__ == "__main__":
    main()
