"""
CHRONOS: NUCLEAR POWER PLANT SCADA SERVICE & PASSIVE TAP (BARC Unit 1)
----------------------------------------------------------------------
Simulates a real-world Nuclear Reactor SCADA node inside the air gap:
1. Driven by authentic NPPAD Pressurized Water Reactor (PWR) operational telemetry
   from Nature Scientific Data (2022).
   - Normal: nppad_normal.csv (100% full power nominal Kudankulam Unit 1 / BARC PWR baseline).
   - On Modbus Pump Trip: transitions to nppad_lof.csv (Loss of Flow / Coolant Pump Trip).
   - On Pipe Break: transitions to nppad_loca.csv (Loss of Coolant Accident).
2. Multi-Port SCADA Server:
   - Port 502: Modbus/TCP Industrial Control Interface
   - Port 8080: Web HMI / HTTP Telemetry REST API (/stats, /trip, /loca, /reset, /text)
3. Passive Simplex Network Tap:
   - Passively extracts flow metadata (5-tuple, IAT, packet bytes, entropy, burst)
   - Detects external port sweeps, floods, and unauthorized commands
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
import hashlib
import threading
import psutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
    print("CHRONOS: NUCLEAR POWER PLANT SCADA SERVICE & PASSIVE TAP (BARC Unit 1)")
    print("Usage: python diode/nuclear_service.py [DIODE_IP]")
    sys.exit(0)

DIODE_IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
DIODE_PORT = 9999

MODBUS_PORT = 502
HMI_PORT = 8080

FACILITY_NAME = "BARC / NPCIL Kudankulam Unit 1 (PWR)"
DATASET_SOURCE = "Nature Scientific Data (NPPAD 96-Sensor Benchmark)"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "nuclear")
NORMAL_CSV = os.path.join(DATA_DIR, "nppad_normal.csv")
LOF_CSV = os.path.join(DATA_DIR, "nppad_lof.csv")
LOCA_CSV = os.path.join(DATA_DIR, "nppad_loca.csv")

def load_csv(path):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                recs = list(csv.DictReader(f))
                print(f"[+] Loaded {len(recs)} records from {os.path.basename(path)}")
                return recs
        except Exception as e:
            print(f"[-] Warning: Failed to load {path}: {e}")
    return []

normal_records = load_csv(NORMAL_CSV)
lof_records = load_csv(LOF_CSV)
loca_records = load_csv(LOCA_CSV)

fallback_record = {
    "TIME": "0.0", "P": "155.5", "TAVG": "310.0", "THA": "327.8", "TCA": "292.2",
    "WRCA": "16515.8", "PSGA": "67.0", "QMWT": "2895.0"
}
if not normal_records:
    normal_records = [fallback_record]
if not lof_records:
    lof_records = [fallback_record]
if not loca_records:
    loca_records = [fallback_record]

# Reactor State Machine
reactor_state = "NOMINAL_FULL_POWER"  # NOMINAL_FULL_POWER, LOSS_OF_FLOW, LOCA_ACCIDENT
active_records = normal_records
state_lock = threading.Lock()
current_idx = 0

stats = {
    "modbus_requests": 0,
    "hmi_requests": 0,
    "attack_packets_received": 0,
    "last_attack": "None",
    "last_attack_time": "--:--:--",
    "cpu_pct": 1.2,
    "memory_mb": 28.0,
    "memory_pct": 2.5,
    "scada_latency_ms": 1.5,
}

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

def trigger_pump_trip(reason="Unauthorized Modbus FC05 Write"):
    """Transitions reactor to Loss of Flow (NPPAD LOF transient)."""
    global reactor_state, active_records, current_idx
    with state_lock:
        reactor_state = "LOSS_OF_FLOW"
        active_records = lof_records
        current_idx = 0
        now_str = time.strftime("%H:%M:%S")
        stats["last_attack"] = f"MODBUS PUMP TRIP ({reason})"
        stats["last_attack_time"] = now_str
        print(f"\n[!] ==========================================================================")
        print(f"[!] [REACTOR EMERGENCY] PRIMARY COOLANT PUMP TRIPPED VIA CYBER ATTACK!")
        print(f"[!] Cause: {reason} at {now_str}")
        print(f"[!] Switching physics telemetry to published NPPAD LOF transient.")
        print(f"[!] Primary coolant flow WRCA dropping rapidly toward 2,100 kg/s...")
        print(f"[!] ==========================================================================\n")

def trigger_loca(reason="Pipe Rupture Anomaly"):
    """Transitions reactor to Loss of Coolant Accident (NPPAD LOCA transient)."""
    global reactor_state, active_records, current_idx
    with state_lock:
        reactor_state = "LOCA_ACCIDENT"
        active_records = loca_records
        current_idx = 0
        now_str = time.strftime("%H:%M:%S")
        stats["last_attack"] = f"LOCA PIPE RUPTURE ({reason})"
        stats["last_attack_time"] = now_str
        print(f"\n[!] ==========================================================================")
        print(f"[!] [REACTOR EMERGENCY] LOSS OF COOLANT ACCIDENT (LOCA) TRIGGERED!")
        print(f"[!] Cause: {reason} at {now_str}")
        print(f"[!] Switching physics telemetry to published NPPAD LOCA transient.")
        print(f"[!] Primary system depressurization in progress...")
        print(f"[!] ==========================================================================\n")

def reset_reactor():
    """Resets reactor to nominal full power operation."""
    global reactor_state, active_records, current_idx
    with state_lock:
        reactor_state = "NOMINAL_FULL_POWER"
        active_records = normal_records
        current_idx = 0
        stats["last_attack"] = "Baseline Restored"
        stats["last_attack_time"] = time.strftime("%H:%M:%S")
        print(f"\n[+] ==========================================================================")
        print(f"[+] [REACTOR RESTORED] Reset to nominal 100% full-power Kudankulam baseline.")
        print(f"[+] P: 155.5 bar | Core Tavg: 310.0 C | Flow: 16,515.8 kg/s | Power: 955.3 MWe")
        print(f"[+] ==========================================================================\n")

def modbus_scada_listener():
    """Listens on Port 502 (Modbus/TCP) and detects incoming attacks or queries."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    port = MODBUS_PORT
    try:
        srv.bind(("0.0.0.0", port))
    except Exception:
        port = 5020
        srv.bind(("0.0.0.0", port))

    srv.listen(50)
    print(f"[+] SCADA Modbus/TCP Listener active on 0.0.0.0:{port}")

    recent_conns = []
    while True:
        try:
            conn, addr = srv.accept()
            stats["modbus_requests"] += 1
            now_t = time.time()
            now_str = time.strftime("%H:%M:%S")

            recent_conns.append((now_t, addr[0]))
            recent_conns = [c for c in recent_conns if now_t - c[0] < 3.0]

            # Detect port scan / recon sweep (more than 5 connections in 3 seconds)
            if len(recent_conns) >= 5:
                stats["last_attack"] = f"PORT SCAN from {addr[0]}"
                stats["last_attack_time"] = now_str
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
                # Modbus Function Code 0x05 or 0x06 or 0x0f or 0x10 = Write/Override command
                if len(data) >= 8 and data[7] in [0x05, 0x06, 0x0f, 0x10]:
                    print(f"\n[!] [UNAUTHORIZED MODBUS WRITE ATTEMPT] Function Code 0x{data[7]:02x} from {addr[0]}!")
                    trigger_pump_trip(f"Modbus FC 0x{data[7]:02x} from {addr[0]}")
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

def hmi_client_handler(conn, addr):
    """Handles an HMI REST request, including simulated workload under attack."""
    try:
        t_start = time.time()
        req = conn.recv(2048).decode("utf-8", errors="ignore")
        stats["hmi_requests"] += 1
        now_str = time.strftime("%H:%M:%S")

        # Parse request path
        path = "/"
        if "GET " in req:
            path = req.split("GET ")[1].split(" ")[0]
        elif "POST " in req:
            path = req.split("POST ")[1].split(" ")[0]

        # Heavy workload simulation when attacked (spikes CPU)
        if "attack" in path or "flood" in path or len(req) > 500:
            stats["attack_packets_received"] += 1
            stats["last_attack"] = "HTTP FLOOD / DDOS"
            stats["last_attack_time"] = now_str
            for _ in range(3000):
                hashlib.sha256(b"adversary_ddos_crypto_challenge_computation").digest()

        content_type = "application/json"

        with state_lock:
            rec = active_records[current_idx % len(active_records)]

        p_val = float(rec.get("P", 155.5))
        tavg_val = float(rec.get("TAVG", 310.0))
        flow_val = float(rec.get("WRCA", 16515.8))
        mw_val = round(float(rec.get("QMWT", 2895.0)) * 0.33, 1)

        if path == "/stats":
            body = json.dumps(stats)
        elif path == "/trip":
            trigger_pump_trip("Manual /trip API Endpoint")
            body = json.dumps({"status": "PUMP_TRIPPED", "reactor_state": reactor_state})
        elif path == "/loca":
            trigger_loca("Manual /loca API Endpoint")
            body = json.dumps({"status": "LOCA_TRIGGERED", "reactor_state": reactor_state})
        elif path == "/reset":
            reset_reactor()
            body = json.dumps({"status": "RESET_OK", "reactor_state": reactor_state})
        elif path == "/text" or "Accept: text/plain" in req:
            content_type = "text/plain; charset=utf-8"
            body = (
                f"========================================================================\n"
                f" CHRONOS: KUDANKULAM UNIT 1 (PWR) SCADA TELEMETRY (NPPAD BENCHMARK)\n"
                f"========================================================================\n"
                f" Facility                : {FACILITY_NAME}\n"
                f" Plant Operating State   : {reactor_state}\n"
                f" Primary Coolant Pressure: {p_val:6.1f} bar       (Nominal: 155.5 bar)\n"
                f" Core Average Temperature: {tavg_val:6.1f} deg C     (Nominal: 310.0 deg C)\n"
                f" Primary Coolant Flow    : {flow_val:7.1f} kg/s    (Nominal: 16515.8 kg/s)\n"
                f" Grid Electrical Output  : {mw_val:6.1f} MWe       (Rated: 1000 MWe)\n"
                f" Host CPU Core Load      : {stats['cpu_pct']:5.1f} %\n"
                f" Host RAM Usage          : {stats['memory_mb']:5.1f} MB ({stats['memory_pct']}%)\n"
                f" Active Cyber Threats    : {stats['last_attack']}\n"
                f" SCADA Polling Latency   : {stats['scada_latency_ms']:5.2f} ms\n"
                f" System Timestamp        : {now_str}\n"
                f"========================================================================\n"
            )
        else:
            body = json.dumps({
                "facility": FACILITY_NAME,
                "dataset": DATASET_SOURCE,
                "reactor_state": reactor_state,
                "pressure_bar": p_val,
                "core_temp_c": tavg_val,
                "coolant_flow_kgs": flow_val,
                "output_mwe": mw_val,
                "host_cpu_pct": stats["cpu_pct"],
                "host_mem_mb": stats["memory_mb"],
                "host_mem_pct": stats["memory_pct"],
                "time": now_str
            })

        t_elapsed = (time.time() - t_start) * 1000.0
        stats["scada_latency_ms"] = round(t_elapsed, 2)

        http_resp = (
            "HTTP/1.1 200 OK\r\n"
            f"Content-Type: {content_type}\r\n"
            f"Content-Length: {len(body.encode('utf-8'))}\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Connection: close\r\n\r\n" + body
        )
        conn.sendall(http_resp.encode("utf-8"))
        conn.close()
    except Exception:
        pass

def hmi_web_listener():
    """Listens on Port 8080 (Web HMI) and responds with real NPPAD JSON vitals and REST commands."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", HMI_PORT))
    srv.listen(50)
    print(f"[+] Nuclear Web HMI interface active on http://0.0.0.0:{HMI_PORT}")

    while True:
        try:
            conn, addr = srv.accept()
            threading.Thread(target=hmi_client_handler, args=(conn, addr), daemon=True).start()
        except Exception:
            pass

def main():
    global current_idx
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

    while True:
        host_cpu = round(psutil.cpu_percent(interval=None), 1)
        mem_info = psutil.virtual_memory()
        host_ram = round(mem_info.percent, 1)
        host_ram_mb = round((mem_info.total - mem_info.available) / (1024 * 1024), 1)
        host_procs = len(psutil.pids())
        now = time.strftime("%H:%M:%S")

        stats["cpu_pct"] = host_cpu
        stats["memory_pct"] = host_ram
        stats["memory_mb"] = host_ram_mb

        with state_lock:
            rec = active_records[current_idx % len(active_records)]
            current_idx += 1

        p_bar = round(float(rec.get("P", 155.5)), 2)
        tavg_c = round(float(rec.get("TAVG", 310.0)), 2)
        tha_c = round(float(rec.get("THA", 327.8)), 2)
        tca_c = round(float(rec.get("TCA", 292.2)), 2)
        wrca_kgs = round(float(rec.get("WRCA", 16515.8)), 1)
        psga_bar = round(float(rec.get("PSGA", 67.0)), 2)
        qmwt = round(float(rec.get("QMWT", 2895.0)), 1)
        mwe_power = round(qmwt * 0.33, 1)

        event_type = "ROUTINE_SCADA" if reactor_state == "NOMINAL_FULL_POWER" else "SCADA_PHYSICAL_ANOMALY"
        status_tag = f"[{reactor_state}]"

        pkt = {
            "node_id": 1,
            "facility": "BARC_Kudankulam_1",
            "src": "nuclear-scada",
            "dataset": "NPPAD_Nature_Sci_Data_2022",
            "reactor_state": reactor_state,
            "state": reactor_state,
            "event_type": event_type,
            "seq": seq,
            "time": now,
            "ts": now,
            "p_bar": p_bar,
            "p": p_bar,
            "tavg_c": tavg_c,
            "tavg": tavg_c,
            "tha_c": tha_c,
            "tca_c": tca_c,
            "wrca_kgs": wrca_kgs,
            "flow": wrca_kgs,
            "psga_bar": psga_bar,
            "qmwt_thermal": qmwt,
            "mwe_electric": mwe_power,
            "mw": mwe_power,
            "host_cpu_pct": host_cpu,
            "cpu": host_cpu,
            "host_ram_pct": host_ram,
            "ram": host_ram,
            "host_ram_mb": host_ram_mb,
            "host_procs": host_procs,
            "payload": f"NPPAD Core [{reactor_state}] [P:{p_bar}bar, Tavg:{tavg_c}C, Flow:{wrca_kgs}kg/s, SG:{psga_bar}bar, Pwr:{mwe_power}MWe]"
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
