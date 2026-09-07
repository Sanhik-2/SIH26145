"""
CHRONOS: NUCLEAR POWER PLANT SCADA & GRID NODE (BARC Unit 1)
-------------------------------------------------------------
Critical Infrastructure Node inside the air-gapped nuclear enclave.
1. Streams authentic Nuclear SCADA reactor physics (Core Temp, Coolant Pressure, Flow, Rods, Power, Grid Freq).
2. Reads REAL Host System Metrics (actual Laptop CPU %, RAM %, Process counts).
3. Live OS Process Sentry: Detects unauthorized execution of Notepad, Calc, CMD, PowerShell, etc.
4. Interactive Red-Team Threat Injection:
   - [1] Data Exfiltration Burst
   - [2] Stealth C2 Beaconing
   - [3] DGA DNS Tunnel
   - [4] Reactor Coolant Valve Tampering
   - [0] Normal Baseline Reset
   - [ENTER] Instant Host Event Demo Alert

Usage:
  python diode/nuclear_node.py
  python diode/nuclear_node.py <TARGET_IP>
"""

import socket
import json
import time
import sys
import threading
import random
import psutil

TARGET_IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
TARGET_PORT = 9999

NODE_ID = 1
FACILITY_NAME = "BARC / NPCIL Kudankulam Unit 1"
SUBSYSTEM = "Nuclear Reactor SCADA & NLDC Grid Interconnect"

# Monitored processes for live host breach detection
WATCHED_APPS = {
    "notepad.exe": "Notepad (Text Editor)",
    "calc.exe": "Windows Calculator",
    "calculatorapp.exe": "Windows Calculator",
    "cmd.exe": "Windows Command Prompt",
    "powershell.exe": "PowerShell Console",
    "mspaint.exe": "MS Paint",
    "taskmgr.exe": "Task Manager",
    "python.exe": "Python Execution Agent"
}

# Reactor physical state
reactor_state = {
    "mode": "NOMINAL",            # NOMINAL, ATTACK_EXFIL, ATTACK_C2, ATTACK_DGA, SENSOR_TAMPER
    "core_temp": 295.4,           # deg C (nominal 290-300 C)
    "primary_pressure": 155.0,    # bar (nominal 150-160 bar)
    "coolant_flow": 42100.0,      # m^3/h
    "control_rods": 18.5,         # % inserted
    "power_output": 880.0,        # MW electrical
    "grid_frequency": 50.00,      # Hz (Indian Grid standard)
    "radiation_msv": 0.08         # mSv/h (ambient)
}
state_lock = threading.Lock()

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
                    "subsystem": SUBSYSTEM,
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
    global reactor_state
    print("---------------------------------------------------------------")
    print(" 🎮 PRESENTATION CONTROLS (Press key + ENTER):")
    print("   [1] Inject Data Exfiltration Flood (Large Burst)")
    print("   [2] Inject Periodic C2 Beaconing (Stealth)")
    print("   [3] Inject DGA DNS Tunnelling (High Entropy)")
    print("   [4] Inject Reactor Coolant Valve Tampering (Physical Trip)")
    print("   [0] Reset Reactor to Normal Baseline")
    print("   [ENTER] Fire Instant Host Execution Demo Alert")
    print("---------------------------------------------------------------\n")

    while True:
        try:
            cmd = input().strip()
            now = time.strftime("%H:%M:%S")

            if cmd == "1":
                with state_lock:
                    reactor_state["mode"] = "ATTACK_EXFIL"
                print("\n[⚡ ATTACK TRIGGERED] Data Exfiltration Flood injected into Simplex Stream!")
                for i in range(8):
                    pkt = {
                        "node_id": NODE_ID,
                        "facility": FACILITY_NAME,
                        "subsystem": SUBSYSTEM,
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
                with state_lock:
                    reactor_state["mode"] = "ATTACK_C2"
                print("\n[⚡ ATTACK TRIGGERED] Stealth Periodic C2 Beaconing injected!")
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "subsystem": SUBSYSTEM,
                    "event_type": "CYBER_ATTACK",
                    "attack_type": "C2_BEACONING",
                    "interval_s": 1.002,
                    "jitter": 0.001,
                    "payload": "C2 BEACON: Covert heartbeat SYN beacon to external IP 198.51.100.23",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))

            elif cmd == "3":
                with state_lock:
                    reactor_state["mode"] = "ATTACK_DGA"
                print("\n[⚡ ATTACK TRIGGERED] DGA High-Entropy DNS Tunnel injected!")
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "subsystem": SUBSYSTEM,
                    "event_type": "CYBER_ATTACK",
                    "attack_type": "DGA_TUNNEL",
                    "domain": "xk9q-7fa2-90bm-nvz.darknet.ru",
                    "entropy": 7.85,
                    "payload": "DGA TUNNEL: High-entropy pseudo-random domain query detected!",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))

            elif cmd == "4":
                with state_lock:
                    reactor_state["mode"] = "SENSOR_TAMPER"
                    reactor_state["core_temp"] = 348.6
                    reactor_state["primary_pressure"] = 176.2
                    reactor_state["coolant_flow"] = 18400.0
                print("\n[⚠️ PHYSICAL ANOMALY] Coolant Valve Tampering Injected! Temp: 348.6 C | Pressure: 176.2 bar!")
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "subsystem": SUBSYSTEM,
                    "event_type": "SCADA_PHYSICAL_ANOMALY",
                    "payload": "ALARM: Primary Coolant Loop 1 Valve Restricted! Core Temp Spiking to 348.6C!",
                    "temp": 348.6,
                    "pressure": 176.2,
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))

            elif cmd == "0":
                with state_lock:
                    reactor_state["mode"] = "NOMINAL"
                    reactor_state["core_temp"] = 295.4
                    reactor_state["primary_pressure"] = 155.0
                    reactor_state["coolant_flow"] = 42100.0
                print("\n[✅ BASELINE RESTORED] Reactor returned to Nominal Stable Baseline.")

            else:
                # Instant manual host trigger
                pkt = {
                    "node_id": NODE_ID,
                    "facility": FACILITY_NAME,
                    "subsystem": SUBSYSTEM,
                    "event_type": "PROCESS_EXECUTION",
                    "app": "Mimikatz / Privilege Escalation Tool",
                    "pid": 8844,
                    "severity": "CRITICAL_RED",
                    "payload": "ALERT: Unauthorized binary 'mimikatz.exe' executed in SCADA memory!",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))
                print(f"\n[⚡ INSTANT EVENT FIRED] Simulated Host Breach Alert sent to Optical Diode!\n")

        except Exception:
            pass

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("=" * 65)
    print("  CHRONOS: NUCLEAR POWER PLANT SCADA NODE")
    print(f"  Facility : {FACILITY_NAME}")
    print(f"  Target Optical Diode Transmitter: {TARGET_IP}:{TARGET_PORT}")
    print("=" * 65)

    # Start live OS watcher & keyboard injector
    threading.Thread(target=live_process_sentry, args=(sock,), daemon=True).start()
    threading.Thread(target=interactive_threat_injector, args=(sock,), daemon=True).start()

    seq = 1
    while True:
        # Collect real laptop host stats
        host_cpu = psutil.cpu_percent(interval=None)
        host_ram = psutil.virtual_memory().percent
        host_procs = len(psutil.pids())
        now = time.strftime("%H:%M:%S")

        with state_lock:
            # Subtle realistic physics fluctuation
            if reactor_state["mode"] == "NOMINAL":
                temp = round(reactor_state["core_temp"] + random.uniform(-0.35, 0.35), 2)
                press = round(reactor_state["primary_pressure"] + random.uniform(-0.2, 0.2), 2)
                flow = round(reactor_state["coolant_flow"] + random.uniform(-50, 50), 1)
                freq = round(50.00 + random.uniform(-0.03, 0.03), 3)
                power = round(880.0 + random.uniform(-1.5, 1.5), 1)
            else:
                temp = reactor_state["core_temp"]
                press = reactor_state["primary_pressure"]
                flow = reactor_state["coolant_flow"]
                freq = 49.62
                power = 945.0

            pkt = {
                "node_id": NODE_ID,
                "facility": "BARC_Kudankulam_1",
                "subsystem": "Reactor_Primary_Loop",
                "event_type": "ROUTINE_SCADA",
                "seq": seq,
                "time": now,
                # Physics Vitals
                "temp_c": temp,
                "pressure_bar": press,
                "coolant_flow": flow,
                "control_rods_pct": reactor_state["control_rods"],
                "grid_freq_hz": freq,
                "power_mw": power,
                # Real Host Workstation Vitals
                "host_cpu_pct": host_cpu,
                "host_ram_pct": host_ram,
                "host_procs": host_procs,
                "payload": f"Reactor Core [T:{temp}C, P:{press}bar, Freq:{freq}Hz, Output:{power}MW]"
            }

        try:
            sock.sendto(json.dumps(pkt).encode("utf-8"), (TARGET_IP, TARGET_PORT))
            status_tag = "✅ NORMAL" if reactor_state["mode"] == "NOMINAL" else "⚠️ ATTACK/ANOMALY"
            print(f"[{now}] #{seq:04d} | {status_tag} | T: {temp}C | P: {press}bar | Freq: {freq}Hz | CPU: {host_cpu}% | RAM: {host_ram}%")
        except Exception as e:
            print(f"[-] Send error: {e}")

        seq += 1
        time.sleep(1.2)

if __name__ == "__main__":
    main()
