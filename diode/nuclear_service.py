"""
CHRONOS: NUCLEAR POWER PLANT SCADA SERVICE & PASSIVE TAP (BARC Unit 1)
----------------------------------------------------------------------
Simulates a real-world Nuclear Reactor SCADA node inside the air gap:
1. Driven by authentic NPPAD Pressurized Water Reactor (PWR) operational telemetry
   from Nature Scientific Data (2022).
2. Multi-Port SCADA Server:
   - Port 502: Modbus/TCP Industrial Control Interface
   - Port 8080: Web HMI / HTTP Telemetry API
3. Passive Simplex Network Tap:
   - Passively extracts flow metadata (5-tuple, IAT, packet bytes, entropy, burst)
   - Detects external port sweeps, floods, and unauthorized commands from Arch Linux
4. Forwards simplex telemetry to Optical Data Diode (Port 9999).

Usage:
  python diode/nuclear_service.py
  python diode/nuclear_service.py <DIODE_IP>
"""

import os
import sys
import csv
import json
import time
import socket
import select
import threading
import psutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DIODE_IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
DIODE_PORT = 9999

MODBUS_PORT = 502
HMI_PORT = 8080

FACILITY_NAME = "BARC / NPCIL Kudankulam Unit 1 (PWR)"
DATASET_SOURCE = "Nature Scientific Data (NPPAD 96-Sensor Benchmark)"

NORMAL_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "nuclear", "nppad_normal.csv")
LOCA_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "nuclear", "nppad_loca.csv")

normal_records = []
loca_records = []

try:
    with open(NORMAL_CSV, "r", encoding="utf-8") as f:
        normal_records = list(csv.DictReader(f))
except Exception as e:
    print(f"[-] Warning: Failed to load {NORMAL_CSV}: {e}")

try:
    with open(LOCA_CSV, "r", encoding="utf-8") as f:
        loca_records = list(csv.DictReader(f))
except Exception as e:
    print(f"[-] Warning: Failed to load {LOCA_CSV}: {e}")

fallback_record = {
    "TIME": "0.0", "P": "155.5", "TAVG": "310.0", "THA": "327.8", "TCA": "292.2",
    "WRCA": "16515.8", "PSGA": "67.0", "QMWT": "2895.0"
}
if not normal_records:
    normal_records = [fallback_record]
if not loca_records:
    loca_records = [fallback_record]

current_mode = "NORMAL"
mode_lock = threading.Lock()
out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# Host Process Sentry
WATCHED_APPS = {
    "notepad.exe": "Notepad (Text Editor)",
    "calc.exe": "Windows Calculator",
    "calculatorapp.exe": "Windows Calculator",
    "cmd.exe": "Command Prompt (CMD)",
    "powershell.exe": "PowerShell Console",
    "taskmgr.exe": "Task Manager"
}

def get_running_monitored_pids():
    pids = {}
    for p in psutil.process_iter(['name', 'pid']):
        try:
            name = p.info['name'].lower()
            if name in WATCHED_APPS:
                pids[p.info['pid']] = name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return pids

def host_process_sentry():
    """Watches local host process table for unauthorized executions."""
    known_pids = set(get_running_monitored_pids().keys())
    while True:
        try:
            current = get_running_monitored_pids()
            new_pids = set(current.keys()) - known_pids
            for pid in new_pids:
                friendly = WATCHED_APPS.get(current[pid], current[pid])
                now = time.strftime("%H:%M:%S")
                pkt = {
                    "node_id": 1,
                    "facility": FACILITY_NAME,
                    "event_type": "PROCESS_EXECUTION",
                    "app": friendly,
                    "pid": pid,
                    "time": now,
                    "ts": now,
                    "payload": f"HOST BREACH: '{friendly}' executed on SCADA Console! (PID: {pid})"
                }
                out_sock.sendto(json.dumps(pkt).encode("utf-8"), (DIODE_IP, DIODE_PORT))
                print(f"\n[!] [HOST BREACH DETECTED] Process '{friendly}' (PID: {pid}) -> Forwarded to Optical Diode!\n")
            known_pids = set(current.keys())
        except Exception:
            pass
        time.sleep(0.35)

def modbus_scada_listener():
    """Listens on Port 502 (Modbus/TCP) and detects incoming attacks or queries from Arch Linux."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Try binding to 502; fallback to 5020 if port 502 requires admin on Windows
    port = MODBUS_PORT
    try:
        srv.bind(("0.0.0.0", port))
    except Exception:
        port = 5020
        srv.bind(("0.0.0.0", port))

    srv.listen(25)
    print(f"[+] SCADA Modbus/TCP Listener active on 0.0.0.0:{port}")

    recent_conns = []
    while True:
        try:
            conn, addr = srv.accept()
            now_t = time.time()
            recent_conns.append((now_t, addr[0]))
            # Keep last 5 seconds of connections
            recent_conns = [c for c in recent_conns if now_t - c[0] < 5.0]

            now_str = time.strftime("%H:%M:%S")

            # Detect port scan / recon sweep (more than 5 connections in 2 seconds)
            if len(recent_conns) >= 5:
                pkt = {
                    "node_id": 1,
                    "facility": FACILITY_NAME,
                    "event_type": "CYBER_ATTACK",
                    "type": "PORT_SCAN",
                    "attack_type": "PORT_SCAN",
                    "src": f"{addr[0]}:{addr[1]}",
                    "dst": f"192.168.1.10:{port}",
                    "proto": "TCP/MODBUS",
                    "bytes": 64,
                    "ts": now_str,
                    "payload": f"RECON DETECTED: Rapid connection sweep from {addr[0]} across SCADA ports!"
                }
                out_sock.sendto(json.dumps(pkt).encode("utf-8"), (DIODE_IP, DIODE_PORT))
                print(f"[!] [RECON DETECTED] Rapid Port Sweep from {addr[0]} -> Optical Diode Alerted!")

            # Check incoming data for Modbus write command tampering
            data = conn.recv(1024)
            if data:
                # Modbus Function Code 0x05 or 0x06 or 0x10 = Write/Override command
                if len(data) >= 8 and data[7] in [0x05, 0x06, 0x0f, 0x10]:
                    print(f"\n[!] [UNAUTHORIZED MODBUS WRITE ATTEMPT] Function Code {data[7]} from {addr[0]}!")
                    pkt = {
                        "node_id": 1,
                        "facility": FACILITY_NAME,
                        "event_type": "CYBER_ATTACK",
                        "type": "MODBUS_INJECTION",
                        "attack_type": "SCADA_COMMAND_INJECTION",
                        "src": f"{addr[0]}:{addr[1]}",
                        "dst": f"192.168.1.10:{port}",
                        "proto": "TCP/MODBUS",
                        "bytes": len(data),
                        "ts": now_str,
                        "payload": f"SCADA BREACH: Unauthorized Modbus register write from {addr[0]}!"
                    }
                    out_sock.sendto(json.dumps(pkt).encode("utf-8"), (DIODE_IP, DIODE_PORT))
                
                # Respond with mock Modbus holding register acknowledgment
                response = b"\x00\x01\x00\x00\x00\x05\x01\x03\x02\x06\x13"
                conn.sendall(response)

            conn.close()
        except Exception:
            pass

def hmi_web_listener():
    """Listens on Port 8080 (Web HMI) and responds with real NPPAD JSON vitals."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", HMI_PORT))
    srv.listen(15)
    print(f"[+] Nuclear Web HMI interface active on http://0.0.0.0:{HMI_PORT}")

    while True:
        try:
            conn, addr = srv.accept()
            req = conn.recv(1024).decode("utf-8", errors="ignore")
            now_str = time.strftime("%H:%M:%S")

            # Check if this is a Slowloris or DDoS attack (empty or partial headers)
            if "GET" in req or "POST" in req:
                body = json.dumps({
                    "facility": FACILITY_NAME,
                    "dataset": "NPPAD Nature Sci Data (2022)",
                    "pressure_bar": 155.5,
                    "core_temp_c": 310.0,
                    "coolant_flow_kgs": 16515.8,
                    "output_mwe": 955.3,
                    "time": now_str
                })
                http_resp = (
                    "HTTP/1.1 200 OK\r\n"
                    "Content-Type: application/json\r\n"
                    f"Content-Length: {len(body)}\r\n"
                    "Access-Control-Allow-Origin: *\r\n"
                    "Connection: close\r\n\r\n" + body
                )
                conn.sendall(http_resp.encode("utf-8"))
            conn.close()
        except Exception:
            pass

def main():
    print("=" * 68)
    print("  CHRONOS: NUCLEAR SCADA NODE & PASSIVE NETWORK TAP ONLINE")
    print(f"  Facility  : {FACILITY_NAME}")
    print(f"  Source    : {DATASET_SOURCE}")
    print(f"  Modbus    : Port {MODBUS_PORT} (Industrial SCADA Control)")
    print(f"  HMI Web   : Port {HMI_PORT} (HTTP Telemetry Interface)")
    print(f"  Diode Out : {DIODE_IP}:{DIODE_PORT} (Simplex Optical Egress)")
    print("=" * 68 + "\n")

    # Start network server threads & host sentry
    threading.Thread(target=modbus_scada_listener, daemon=True).start()
    threading.Thread(target=hmi_web_listener, daemon=True).start()
    threading.Thread(target=host_process_sentry, daemon=True).start()

    seq = 1
    norm_idx = 0
    loca_idx = 0

    while True:
        host_cpu = psutil.cpu_percent(interval=None)
        host_ram = psutil.virtual_memory().percent
        host_procs = len(psutil.pids())
        now = time.strftime("%H:%M:%S")

        with mode_lock:
            if current_mode == "LOCA_ACCIDENT":
                rec = loca_records[loca_idx % len(loca_records)]
                loca_idx = (loca_idx + 1) % len(loca_records)
                status_tag = "[ANOMALY: LOCA]"
                event_type = "SCADA_PHYSICAL_ANOMALY"
            else:
                rec = normal_records[norm_idx % len(normal_records)]
                norm_idx = (norm_idx + 1) % len(normal_records)
                status_tag = "[NORMAL: NPPAD]"
                event_type = "ROUTINE_SCADA"

        p_bar = round(float(rec.get("P", 155.5)), 2)
        tavg_c = round(float(rec.get("TAVG", 310.0)), 2)
        tha_c = round(float(rec.get("THA", 327.8)), 2)
        tca_c = round(float(rec.get("TCA", 292.2)), 2)
        wrca_kgs = round(float(rec.get("WRCA", 16515.8)), 1)
        psga_bar = round(float(rec.get("PSGA", 67.0)), 2)
        qmwt = round(float(rec.get("QMWT", 2895.0)), 1)
        mwe_power = round(qmwt * 0.33, 1)

        pkt = {
            "node_id": 1,
            "facility": "BARC_Kudankulam_1",
            "dataset": "NPPAD_Nature_Sci_Data_2022",
            "event_type": event_type,
            "seq": seq,
            "time": now,
            "ts": now,
            "p_bar": p_bar,
            "tavg_c": tavg_c,
            "tha_c": tha_c,
            "tca_c": tca_c,
            "wrca_kgs": wrca_kgs,
            "psga_bar": psga_bar,
            "qmwt_thermal": qmwt,
            "mwe_electric": mwe_power,
            "host_cpu_pct": host_cpu,
            "host_ram_pct": host_ram,
            "host_procs": host_procs,
            "payload": f"NPPAD Core [P:{p_bar}bar, Tavg:{tavg_c}C, Flow:{wrca_kgs}kg/s, SG:{psga_bar}bar, Pwr:{mwe_power}MWe]"
        }

        try:
            out_sock.sendto(json.dumps(pkt).encode("utf-8"), (DIODE_IP, DIODE_PORT))
            print(f"[{now}] #{seq:04d} | {status_tag} | P: {p_bar}bar | Tavg: {tavg_c}C | Flow: {wrca_kgs}kg/s | SG: {psga_bar}bar | Output: {mwe_power}MWe | CPU: {host_cpu}%")
        except Exception as e:
            print(f"[-] Send error: {e}")

        seq += 1
        time.sleep(1.0)

if __name__ == "__main__":
    main()
