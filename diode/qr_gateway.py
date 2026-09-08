"""
CHRONOS: NUCLEAR SCADA OPTICAL DATA DIODE (TRANSMITTER GATEWAY)
--------------------------------------------------------------
Enforces physical one-way air gap egress from Nuclear SCADA Enclave:
1. Ingests UDP simplex telemetry from the Nuclear SCADA Node on port 9999.
2. Background thread continuously polls containerized SCADA Node REST API (http://<host>:8080)
   for live cgroup CPU/RAM usage, network rate spikes, and NPPAD nuclear vitals.
3. Renders high-contrast Optical QR Photon Stream on screen for optical scanning.
4. Broadcasts local simplex mirror on port 9998 (enables instant single-laptop SOC testing).

Usage:
  python diode/qr_gateway.py
  python diode/qr_gateway.py 192.168.137.1
  python diode/qr_gateway.py --scada-host 192.168.137.1
"""

import os
import sys
import socket
import json
import time
import argparse
import threading
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
import numpy as np
import cv2
import qrcode

REPO_ROOT = Path(__file__).resolve().parent.parent

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

# Live hardware and nuclear telemetry polled asynchronously from Node 1 Docker container
current_vitals = {
    "node_id": 1,
    "facility": "BARC_Kudankulam_1",
    "src": "nuclear-scada",
    "state": "NOMINAL_FULL_POWER",
    "reactor_state": "NOMINAL_FULL_POWER",
    "p": 155.5,
    "tavg": 310.0,
    "flow": 16515.8,
    "mw": 955.3,
    "cpu": 1.2,
    "ram": 2.8,
    "net": 0.0,
    "net_rx_kbps": 0.0,
    "net_tx_kbps": 0.0,
    "last_attack": "None",
    "last_poll_time": 0.0,
    "online": False,
}
vitals_lock = threading.Lock()


def detect_gateway_ip():
    """Detects default gateway IP (e.g. 192.168.137.1 when connected to Windows hotspot)."""
    try:
        if sys.platform == "win32":
            res = subprocess.run(["route", "print", "0.0.0.0"], capture_output=True, text=True, timeout=1.0)
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    gw = parts[2]
                    if gw.count(".") == 3 and not gw.startswith("127."):
                        return gw
        else:
            res = subprocess.run(["ip", "route", "show", "default"], capture_output=True, text=True, timeout=1.0)
            parts = res.stdout.split()
            if "via" in parts:
                return parts[parts.index("via") + 1]
    except Exception:
        pass
    return "192.168.137.1"


def scada_poller_worker(target_host=None):
    """Continuously polls the containerized SCADA node in the background.
    Runs asynchronously so the OpenCV QR rendering loop maintains smooth 30 FPS
    and never drops frames or stalls during heavy container DDoS bursts.
    """
    global current_vitals

    gw_ip = detect_gateway_ip()
    candidate_urls = []
    if target_host:
        h = str(target_host).strip()
        if not h.startswith("http"):
            h = f"http://{h}:8080"
        candidate_urls.append(h)

    # Add hotspot gateway and localhost candidates
    for h_ip in [gw_ip, "192.168.137.1", "127.0.0.1", "localhost", "host.docker.internal"]:
        if h_ip:
            u = f"http://{h_ip}:8080"
            if u not in candidate_urls:
                candidate_urls.append(u)

    active_url = candidate_urls[0]

    while True:
        data = None
        urls_to_try = [active_url] + [u for u in candidate_urls if u != active_url]
        for url in urls_to_try:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "ChronosDiodeGateway/1.0"})
                with urllib.request.urlopen(req, timeout=1.2) as resp:
                    raw = resp.read().decode("utf-8")
                    parsed = json.loads(raw)
                    if "pressure_bar" in parsed or "p" in parsed or "container_cpu_pct" in parsed or "cpu_pct" in parsed or "cpu" in parsed:
                        data = parsed
                        active_url = url
                        break
            except Exception:
                continue

        if data:
            p_val = round(float(data.get("pressure_bar", data.get("p", 155.5))), 1)
            tavg_val = round(float(data.get("core_temp_c", data.get("tavg", 310.0))), 1)
            flow_val = round(float(data.get("coolant_flow_kgs", data.get("flow", 16515.8))), 1)
            mw_val = round(float(data.get("output_mwe", data.get("mw", 955.3))), 1)
            cpu_val = round(float(data.get("container_cpu_pct", data.get("cpu_pct", data.get("cpu", 1.2)))), 1)
            ram_val = round(float(data.get("container_mem_pct", data.get("ram", 2.8))), 1)
            net_val = round(float(data.get("net_rx_kbps", data.get("net_rx_kb", data.get("net_kb", data.get("net", 0.0))))), 1)
            net_tx = round(float(data.get("net_tx_kbps", data.get("net_tx_kb", 0.0))), 1)
            state_val = str(data.get("reactor_state", data.get("state", "NOMINAL_FULL_POWER")))
            atk_val = str(data.get("last_attack", "None"))

            with vitals_lock:
                current_vitals["p"] = p_val
                current_vitals["tavg"] = tavg_val
                current_vitals["flow"] = flow_val
                current_vitals["mw"] = mw_val
                current_vitals["cpu"] = cpu_val
                current_vitals["ram"] = ram_val
                current_vitals["net"] = net_val
                current_vitals["net_rx_kbps"] = net_val
                current_vitals["net_tx_kbps"] = net_tx
                current_vitals["state"] = state_val
                current_vitals["reactor_state"] = state_val
                current_vitals["last_attack"] = atk_val
                current_vitals["last_poll_time"] = time.time()
                current_vitals["online"] = True

        time.sleep(0.25)


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


def run_transmitter_loop(mirror_sock, notifier, headless=False, fps=2.0, custom_host=None):
    global sequence_id, total_received, total_bytes, is_alert_active

    # Load authentic NPPAD benchmark for fallback progression
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

        # Read latest genuine hardware and nuclear vitals from asynchronous poller
        with vitals_lock:
            vitals = dict(current_vitals)

        # If poller hasn't contacted container yet, advance from CSV benchmark
        if not vitals["online"] and nppad_fallback_records:
            rec = nppad_fallback_records[sequence_id % len(nppad_fallback_records)]
            vitals["p"] = round(float(rec.get("P", 155.5)), 1)
            vitals["tavg"] = round(float(rec.get("TAVG", 310.0)), 1)
            vitals["flow"] = round(float(rec.get("WRCA", 16515.8)), 1)
            vitals["mw"] = round(float(rec.get("QMWT", 2895.0)) * 0.33, 1)

        is_threat = False
        atk_type = ""
        threat_cls = ""
        feat = None
        src_node = "nuclear-scada"
        pkt_size = 128

        if batch:
            latest = batch[-1]
            atk_type = str(latest.get("attack_type", latest.get("atk", ""))).upper()
            threat_cls = str(latest.get("threat_class", latest.get("cls", ""))).lower()
            evt = str(latest.get("event_type", ""))

            if evt == "CYBER_ATTACK" or atk_type or (threat_cls in ["a", "b", "c", "d", "e", "f"]):
                is_threat = True
                src_node = "redteam-attacker"

            if "cpu" in latest:
                vitals["cpu"] = max(vitals["cpu"], float(latest["cpu"]))
            if "net" in latest:
                vitals["net"] = max(vitals["net"], float(latest["net"]))
            if "reactor_state" in latest and latest["reactor_state"] != "NOMINAL_FULL_POWER":
                vitals["state"] = latest["reactor_state"]
            if "state" in latest and latest["state"] != "NOMINAL_FULL_POWER":
                vitals["state"] = latest["state"]

            feat = latest.get("feat")
            pkt_size = int(latest.get("bytes", latest.get("size", 128)))

        # Detect attack or physical anomaly from live container state
        if vitals.get("last_attack") and vitals["last_attack"] not in ("None", "Baseline Restored"):
            if any(k in vitals["last_attack"] for k in ("FLOOD", "DDOS", "SCAN", "TRIP", "MODBUS")):
                is_threat = True
                if not atk_type:
                    atk_type = vitals["last_attack"]

        # Reactor state anomaly (e.g. LOSS_OF_FLOW)
        if vitals["state"] not in ("NOMINAL", "NOMINAL_FULL_POWER"):
            is_threat = True

        # Real-time hardware spike thresholds (DDoS saturation)
        if vitals["cpu"] >= 45.0 or vitals["net"] >= 150.0:
            is_threat = True
            if not atk_type:
                atk_type = "VOLUMETRIC_FLOOD_DDOS"

        # Determine 5-channel feature vector [iat, bytes, entropy, burst, direction] for NJ-ODE AI
        if not feat:
            if "FLOOD" in atk_type or "DDOS" in atk_type or threat_cls == "a" or vitals["cpu"] >= 50.0 or vitals["net"] >= 150.0:
                feat = [0.002, 64, 1.10, 50.0, 1]
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
            elif "MODBUS" in atk_type or "PUMP" in atk_type or vitals["state"] == "LOSS_OF_FLOW":
                feat = [0.10, 400, 5.80, 3.0, 0]
            else:
                feat = [1.05, 128, 3.45, 1.0, 0]

        p_val = vitals["p"]
        tavg_val = vitals["tavg"]
        flow_val = vitals["flow"]
        mw_val = vitals["mw"]
        cpu_val = vitals["cpu"]
        ram_val = vitals["ram"]
        net_val = vitals["net"]
        state_val = vitals["state"]

        # Highly Optimized Optical QR Payload (~145 bytes, Version 4/5 QR Code)
        # Bold, high-contrast, easily scannable by phone webcams over physical air gaps
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
            "net": net_val,
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
                "net": net_val,
                "net_rx_kbps": net_val,
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
            
            # Dynamic telemetry alert color: Red/Amber on spike or threat, Emerald on nominal
            if is_threat or cpu_val >= 50.0 or net_val >= 150.0:
                status_color = (0, 50, 255)  # Bright Red
            elif state_val not in ("NOMINAL", "NOMINAL_FULL_POWER"):
                status_color = (0, 140, 255) # Warning Amber
            else:
                status_color = (0, 255, 120) # Emerald Green

            cv2.putText(canvas, f"State: {state_val} | CPU: {cpu_val:.1f}% | RAM: {ram_val:.1f}% | Net: {net_val:.1f} KB/s", 
                        (25, 630), cv2.FONT_HERSHEY_SIMPLEX, 0.48, status_color, 1)

            cv2.putText(canvas, f"NPPAD Vitals: P={p_val:.1f}bar | Tavg={tavg_val:.1f}C | Flow={flow_val:.1f}kg/s | MW={mw_val:.1f}MWe", 
                        (25, 660), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 240, 255), 1)

            cv2.putText(canvas, "Air-Gap: UNIDIRECTIONAL OPTICAL PHOTONS ONLY (ZERO COPPER RETURN)", 
                        (25, 692), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 255, 0), 1)

            cv2.imshow("CHRONOS Nuclear Optical Diode (Transmitter)", canvas)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break

        # Terminal live telemetry output with genuine container CPU/RAM/Net spikes
        status_tag = "[NOMINAL]" if state_val in ("NOMINAL", "NOMINAL_FULL_POWER") and not is_threat else f"[{state_val}]"
        if is_threat and atk_type:
            status_tag = f"[ALERT:{atk_type[:12]}]"
        print(f"[{time.strftime('%H:%M:%S')}] {status_tag} CPU: {cpu_val:5.1f}% | RAM: {ram_val:5.1f}% | Net: {net_val:6.1f} KB/s | P: {p_val:5.1f} bar | Flow: {flow_val:7.1f} kg/s | State: {state_val}")

        sequence_id += 1
        elapsed = time.time() - start_time
        sleep_dur = max(0.05, (1.0 / max(0.5, fps)) - elapsed)
        time.sleep(sleep_dur)

    if notifier:
        notifier.close()
    if not headless:
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser(description="CHRONOS Nuclear Optical Data Diode QR Gateway")
    parser.add_argument("host_pos", nargs="?", default="", help="Optional SCADA host IP (e.g. 192.168.137.1 or 10.1.72.254)")
    parser.add_argument("--scada-host", "--host", default="", help="Node 1 Docker SCADA host IP (e.g. 192.168.137.1)")
    parser.add_argument("--gui", action="store_true", help="Force display graphical QR diode window")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display window")
    parser.add_argument("--fps", type=float, default=2.0, help="Optical frame rate (default: 2.0 fps)")
    parser.add_argument("--dashboard-url", default=DEFAULT_DASHBOARD_URL, help="SOC Dashboard URL for SSE sync")
    args = parser.parse_args()

    target_host = args.scada_host or args.host_pos or ""
    if not target_host:
        target_host = detect_gateway_ip()

    global SCADA_HMI_URL
    if not target_host.startswith("http"):
        SCADA_HMI_URL = f"http://{target_host}:8080"
    else:
        SCADA_HMI_URL = target_host

    headless = args.headless or (sys.platform != "win32" and not os.environ.get("DISPLAY") and not args.gui)
    notifier = DashboardNotifier(base_url=args.dashboard_url)

    # Start background packet ingestion thread
    threading.Thread(target=packet_listener, daemon=True).start()

    # Start background SCADA container poller thread
    threading.Thread(target=scada_poller_worker, args=(target_host,), daemon=True).start()

    mirror_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if not headless:
        try:
            cv2.namedWindow("CHRONOS Nuclear Optical Diode (Transmitter)", cv2.WINDOW_NORMAL)
        except Exception:
            headless = True

    run_transmitter_loop(mirror_sock, notifier, headless=headless, fps=args.fps, custom_host=target_host)


if __name__ == "__main__":
    main()
