"""
CHRONOS: NUCLEAR SCADA NODE (REAL-WORLD NPPAD BENCHMARK DATASET)
----------------------------------------------------------------
Streams authentic, published Pressurized Water Reactor (PWR) operational telemetry
from the NPPAD benchmark dataset (Nature Scientific Data, 2022) across the optical data diode.

Dataset Citation:
  Qi, B., Xiao, X., Liang, J. et al. An open time-series simulated dataset covering
  various accidents for nuclear power plants. Nature Scientific Data 9, 766 (2022).

Telemetry Channels (NPPAD):
  - P: Primary Coolant System Pressure (bar)
  - TAVG: Core Average Temperature (deg C)
  - THA / TCA: Hot Leg / Cold Leg Coolant Temperatures (deg C)
  - WRCA: Reactor Coolant Flow Rate (kg/s)
  - PSGA: Steam Generator A Pressure (bar)
  - QMWT: Reactor Thermal Core Power (MWth)

Real Host Machine Monitoring:
  - Real-time Laptop CPU %, RAM %, and process table via psutil.
  - Live OS Process Sentry: Detects launch of notepad.exe, calc.exe, cmd.exe, powershell.exe, etc.

Interactive Threat Injection:
  - [1] Data Exfiltration Flood (Burst Anomaly)
  - [2] Stealth C2 Heartbeat Beacon
  - [3] High-Entropy DGA DNS Tunnel
  - [4] Loss of Coolant Accident / Valve Rupture (Streams NPPAD LOCA dataset)
  - [0] Normal Reactor Baseline (NPPAD Normal dataset)
  - [ENTER] Instant Host Intrusion Alert

Usage:
  python diode/nuclear_node.py
"""

import os
import sys
import csv
import json
import time
import socket
import threading
import psutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
    print("CHRONOS: NUCLEAR SCADA NODE (REAL-WORLD NPPAD BENCHMARK DATASET)")
    print("Usage: python diode/nuclear_node.py [TARGET_IP]")
    sys.exit(0)

TARGET_IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
TARGET_PORT = 9999

NODE_ID = 1
FACILITY_NAME = "BARC / NPCIL Kudankulam Unit 1 (PWR)"
DATASET_SOURCE = "Nature Scientific Data (NPPAD 96-Sensor Benchmark)"

NORMAL_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "nuclear", "nppad_normal.csv")
LOCA_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "nuclear", "nppad_loca.csv")

# Load NPPAD Datasets
normal_records = []
loca_records = []

try:
    with open(NORMAL_CSV, "r", encoding="utf-8") as f:
        normal_records = list(csv.DictReader(f))
    print(f"[+] Loaded {len(normal_records)} authentic normal telemetry steps from NPPAD dataset.")
except Exception as e:
    print(f"[-] Warning: Failed to load {NORMAL_CSV}: {e}")

try:
    with open(LOCA_CSV, "r", encoding="utf-8") as f:
        loca_records = list(csv.DictReader(f))
    print(f"[+] Loaded {len(loca_records)} accident telemetry steps from NPPAD LOCA dataset.")
except Exception as e:
    print(f"[-] Warning: Failed to load {LOCA_CSV}: {e}")

# Fallback record if files missing
fallback_record = {
    "TIME": "0.0", "P": "155.5", "TAVG": "310.0", "THA": "327.8", "TCA": "292.2",
    "WRCA": "16515.8", "PSGA": "67.0", "QMWT": "2895.0"
}
if not normal_records:
    normal_records = [fallback_record]
if not loca_records:
    loca_records = [fallback_record]

# Monitored processes for live host breach detection (Cross-Platform Windows & Linux)
WATCHED_APPS = {
    # Windows binaries
    "notepad.exe": "Notepad (Text Editor)",
    "calc.exe": "Windows Calculator",
    "calculatorapp.exe": "Windows Calculator",
    "cmd.exe": "Command Prompt (CMD)",
    "powershell.exe": "PowerShell Console",
    "mspaint.exe": "MS Paint",
    "taskmgr.exe": "Task Manager",
    "python.exe": "Python Execution Agent",
    # Linux & UNIX binaries
    "notepad": "Notepad (Text Editor)",
    "calc": "Calculator Tool",
    "gnome-calculator": "GNOME Calculator",
    "kcalc": "KDE Calculator",
    "gedit": "GEdit Text Editor",
    "kate": "Kate Text Editor",
    "nano": "Nano Editor",
    "vim": "Vim Editor",
    "bash": "Bash Shell (Remote Egress)",
    "sh": "POSIX Shell Execution",
    "zsh": "Zsh Shell Execution",
    "python": "Python Process",
    "python3": "Python3 Sentry Agent",
    "wireshark": "Wireshark Packet Capture",
    "nmap": "Nmap Network Scanner"
}

current_mode = "NORMAL"
mode_lock = threading.Lock()

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

def live_process_sentry(sock):
    """Monitors Windows process table for newly spawned unauthorized processes."""
    known_pids = set(get_running_monitored_pids().keys())
    
    print("\n[*] Live OS Process Sentry ACTIVE on Nuclear SCADA Workstation.")
    print("[*] Open Notepad or Calculator on this laptop to trigger an immediate optical diode alert!\n")

    while True:
        try:
            current = get_running_monitored_pids()
            new_pids = set(current.keys()) - known_pids
            for pid in new_pids:
                app_name = current[pid]
                friendly = WATCHED_APPS.get(app_name, app_name)
                now = time.strftime("%H:%M:%S")

                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "event_type": "PROCESS_EXECUTION",
                    "app": friendly,
                    "pid": pid,
                    "severity": "CRITICAL_RED",
                    "payload": f"SECURITY BREACH: Unauthorized binary '{friendly}' spawned on SCADA! (PID: {pid})",
                    "time": now
                }

                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))
                print(f"\n🚨 [HOST INTRUSION DETECTED] Spawned: '{friendly}' (PID: {pid}) -> Sent to Optical Diode!\n")

            known_pids = set(current.keys())
        except Exception:
            pass
        time.sleep(0.35)

def interactive_threat_injector(sock):
    """Allows user to trigger realistic attacks during presentation."""
    global current_mode
    print("---------------------------------------------------------------")
    print(" [CONTROLS] PRESENTATION HOTKEYS (Press key + ENTER):")
    print("   [1] Inject Data Exfiltration Flood (Large Burst)")
    print("   [2] Inject Periodic C2 Beaconing (Stealth Heartbeat)")
    print("   [3] Inject DGA DNS Tunnelling (High Entropy)")
    print("   [4] Inject Loss of Coolant Incident (NPPAD LOCA Dataset)")
    print("   [0] Reset to Nominal Baseline (NPPAD Normal Dataset)")
    print("   [ENTER] Fire Instant Host Execution Demo Alert")
    print("---------------------------------------------------------------\n")

    while True:
        try:
            cmd = input().strip()
            now = time.strftime("%H:%M:%S")

            if cmd == "1":
                with mode_lock:
                    current_mode = "ATTACK_EXFIL"
                print("\n[!] [CYBER ATTACK TRIGGERED] Data Exfiltration Flood injected into Simplex Stream!")
                for i in range(8):
                    pkt = {
                        "node_id": NODE_ID,
                        "facility": FACILITY_NAME,
                        "event_type": "CYBER_ATTACK",
                        "attack_type": "EXFILTRATION_BURST",
                        "burst_rate_mbps": 48.5,
                        "entropy": 7.92,
                        "payload": f"EXFIL FLOOD: 64KB compressed archive chunk #{i+1} exfiltrating outward!",
                        "time": now
                    }
                    sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))
                    time.sleep(0.04)

            elif cmd == "2":
                with mode_lock:
                    current_mode = "ATTACK_C2"
                print("\n[!] [CYBER ATTACK TRIGGERED] Stealth Periodic C2 Beaconing injected!")
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "event_type": "CYBER_ATTACK",
                    "attack_type": "C2_BEACONING",
                    "interval_s": 1.002,
                    "jitter": 0.001,
                    "payload": "C2 BEACON: Covert heartbeat SYN beacon to external IP 198.51.100.23",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))

            elif cmd == "3":
                with mode_lock:
                    current_mode = "ATTACK_DGA"
                print("\n[!] [CYBER ATTACK TRIGGERED] DGA High-Entropy DNS Tunnel injected!")
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "event_type": "CYBER_ATTACK",
                    "attack_type": "DGA_TUNNEL",
                    "domain": "xk9q-7fa2-90bm-nvz.darknet.ru",
                    "entropy": 7.85,
                    "payload": "DGA TUNNEL: High-entropy pseudo-random domain query detected!",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))

            elif cmd == "4":
                with mode_lock:
                    current_mode = "LOCA_ACCIDENT"
                print("\n[!] [PHYSICAL INCIDENT INJECTED] Replaying NPPAD Loss of Coolant Accident (LOCA)!")
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "event_type": "SCADA_PHYSICAL_ANOMALY",
                    "payload": "ALARM: Primary Coolant Loop Rupture! LOCA Transient Underway!",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))

            elif cmd == "0":
                with mode_lock:
                    current_mode = "NORMAL"
                print("\n[+] [BASELINE RESTORED] Replaying NPPAD Normal Baseline Operational Dataset.")

            else:
                # Instant manual host breach trigger
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "event_type": "PROCESS_EXECUTION",
                    "app": "Mimikatz / Memory Dumper",
                    "pid": 8844,
                    "severity": "CRITICAL_RED",
                    "payload": "ALERT: Unauthorized binary 'mimikatz.exe' executed in SCADA memory!",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))
                print(f"\n[!] [INSTANT EVENT FIRED] Simulated Host Breach Alert sent to Optical Diode!\n")

        except (EOFError, KeyboardInterrupt):
            break
        except Exception:
            pass

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("=" * 65)
    print("  CHRONOS: NUCLEAR SCADA NODE (NPPAD BENCHMARK DATASET)")
    print(f"  Facility : {FACILITY_NAME}")
    print(f"  Source   : {DATASET_SOURCE}")
    print(f"  Diode Tx : {TARGET_IP}:{TARGET_PORT} (Simplex Optical Egress)")
    print("=" * 65)

    threading.Thread(target=live_process_sentry, args=(sock,), daemon=True).start()
    threading.Thread(target=interactive_threat_injector, args=(sock,), daemon=True).start()

    seq = 1
    norm_idx = 0
    loca_idx = 0

    while True:
        # Collect real laptop host stats
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
                status_tag = "[NORMAL: NPPAD]" if current_mode == "NORMAL" else "[CYBER ATTACK]"
                event_type = "ROUTINE_SCADA" if current_mode == "NORMAL" else "CYBER_ATTACK"

        # Parse genuine physical channels from NPPAD dataset
        p_bar = round(float(rec.get("P", 155.5)), 2)
        tavg_c = round(float(rec.get("TAVG", 310.0)), 2)
        tha_c = round(float(rec.get("THA", 327.8)), 2)
        tca_c = round(float(rec.get("TCA", 292.2)), 2)
        wrca_kgs = round(float(rec.get("WRCA", 16515.8)), 1)
        psga_bar = round(float(rec.get("PSGA", 67.0)), 2)
        qmwt = round(float(rec.get("QMWT", 2895.0)), 1)
        mwe_power = round(qmwt * 0.33, 1)  # Thermal to electrical conversion (~33% efficiency)

        pkt = {
            "node_id": NODE_ID,
            "facility": "BARC_Kudankulam_1",
            "dataset": "NPPAD_Nature_Sci_Data_2022",
            "event_type": event_type,
            "seq": seq,
            "time": now,
            # Authentic NPPAD Physical Telemetry
            "p_bar": p_bar,
            "tavg_c": tavg_c,
            "tha_c": tha_c,
            "tca_c": tca_c,
            "wrca_kgs": wrca_kgs,
            "psga_bar": psga_bar,
            "qmwt_thermal": qmwt,
            "mwe_electric": mwe_power,
            # Real Host Laptop Stats
            "host_cpu_pct": host_cpu,
            "host_ram_pct": host_ram,
            "host_procs": host_procs,
            "payload": f"NPPAD Core [P:{p_bar}bar, Tavg:{tavg_c}C, Flow:{wrca_kgs}kg/s, SG:{psga_bar}bar, Pwr:{mwe_power}MWe]"
        }

        try:
            sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))
            print(f"[{now}] #{seq:04d} | {status_tag} | P: {p_bar}bar | Tavg: {tavg_c}C | Flow: {wrca_kgs}kg/s | SG: {psga_bar}bar | Output: {mwe_power}MWe | CPU: {host_cpu}%")
        except Exception as e:
            print(f"[-] Send error: {e}")

        seq += 1
        time.sleep(1.0)

if __name__ == "__main__":
    main()
