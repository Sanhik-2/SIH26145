"""
CHRONOS ADVERSARY ATTACK CONSOLE (Runs on Laptop 4)
---------------------------------------------------
Interactive Red-Team Cyber Warfare Launcher:
Allows judges and team members to launch live cyber attacks against the network:
1. Volumetric / Protocol DDoS (Spoofed SYN Flood)
2. Stealth Botnet C2 Beaconing (Cobalt Strike / Sliver)
3. DGA Domains & DNS Tunnelling (dnscat2 base64 exfiltration)
4. Encrypted Malware Session (Known Malicious JA4 Fingerprints)
5. Reconnaissance & Port Scanning (Fan-out sweep)

Usage:
  python attacker_console.py <GATEWAY_IP>
"""

import tkinter as tk
import socket
import json
import time
import random
import threading
import sys

class AttackerConsole:
    def __init__(self, root, gateway_ip="127.0.0.1", gateway_port=9999):
        self.root = root
        self.gateway_ip = gateway_ip
        self.gateway_port = gateway_port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.active_attack = None
        self.running = False

        self.root.title("CHRONOS RED-TEAM ADVERSARY CONSOLE [ATTACK INJECTOR]")
        self.root.geometry("800x600")
        self.root.configure(bg="#0c0d14")

        self.setup_ui()

    def setup_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg="#1a0b12", height=65)
        hdr.pack(fill="x")
        tk.Label(hdr, text="ADVERSARY CYBER WARFARE CONSOLE [RED-TEAM]", font=("Consolas", 14, "bold"), fg="#ff3366", bg="#1a0b12").pack(side="left", padx=20, pady=15)
        self.status_lbl = tk.Label(hdr, text="● IDLE (NO ATTACK ACTIVE)", font=("Consolas", 10, "bold"), fg="#00ff66", bg="#1a0b12")
        self.status_lbl.pack(side="right", padx=20)

        # Body
        body = tk.Frame(self.root, bg="#0c0d14")
        body.pack(fill="both", expand=True, padx=20, pady=15)

        # Left Column: Attack Launch Buttons
        btn_frame = tk.Frame(body, bg="#14111d", width=340, bd=1, relief="solid")
        btn_frame.pack(side="left", fill="both", padx=(0, 10))

        tk.Label(btn_frame, text="SELECT ATTACK VECTOR TO INJECT:", font=("Consolas", 10, "bold"), fg="#ffffff", bg="#14111d").pack(anchor="w", padx=15, pady=(15, 10))

        self.create_attack_btn(btn_frame, "1. Volumetric SYN Flood (DDoS)", "#ff0055", self.launch_ddos)
        self.create_attack_btn(btn_frame, "2. Botnet C2 Beaconing (Cobalt)", "#cc00ff", self.launch_c2)
        self.create_attack_btn(btn_frame, "3. DNS Tunnelling / DGA Exfil", "#ffaa00", self.launch_dns)
        self.create_attack_btn(btn_frame, "4. Encrypted Malware (JA4)", "#ff3300", self.launch_encrypted)
        self.create_attack_btn(btn_frame, "5. Reconnaissance / Port Scan", "#00d4ff", self.launch_scan)

        # Stop Button
        stop_btn = tk.Button(btn_frame, text="⏹ CEASE ALL ATTACKS (BENIGN)", font=("Consolas", 11, "bold"), 
                             fg="#ffffff", bg="#333344", activebackground="#444455", activeforeground="#ffffff", 
                             command=self.stop_attack, bd=0, padx=10, pady=8, cursor="hand2")
        stop_btn.pack(fill="x", padx=15, pady=(15, 10))

        # Right Column: Attack Console Logs
        log_frame = tk.Frame(body, bg="#14111d", bd=1, relief="solid")
        log_frame.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(log_frame, text="LIVE ADVERSARY TRANSMISSION LOGS:", font=("Consolas", 10, "bold"), fg="#ff3366", bg="#14111d").pack(anchor="w", padx=15, pady=15)
        self.log_box = tk.Listbox(log_frame, bg="#08070d", fg="#ff8099", font=("Consolas", 9), bd=0)
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def create_attack_btn(self, parent, text, color, cmd):
        btn = tk.Button(parent, text=text, font=("Consolas", 10, "bold"), fg="#ffffff", bg=color, 
                        activebackground="#ffffff", activeforeground=color, command=cmd, bd=0, padx=10, pady=8, cursor="hand2")
        btn.pack(fill="x", padx=15, pady=6)

    def log(self, msg):
        now = time.strftime("%H:%M:%S")
        self.log_box.insert(0, f"[{now}] {msg}")
        if self.log_box.size() > 100:
            self.log_box.delete(100, "end")

    def stop_attack(self):
        self.running = False
        self.active_attack = None
        self.status_lbl.config(text="● IDLE (NO ATTACK ACTIVE)", fg="#00ff66")
        self.log("All attack threads halted. Transmitting benign state.")

    def launch_ddos(self):
        self.stop_attack()
        self.running = True
        self.status_lbl.config(text="● EXECUTING: VOLUMETRIC SYN FLOOD", fg="#ff0055")
        self.log(">>> LAUNCHING HIGH-ENTROPY SPOOFED SYN FLOOD ON GATEWAY...")
        threading.Thread(target=self._ddos_thread, daemon=True).start()

    def _ddos_thread(self):
        while self.running:
            # Blast 40 packets with completely randomized spoofed source IPs (Entropy spike!)
            for _ in range(40):
                fake_ip = f"{random.randint(11, 220)}.{random.randint(1, 254)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
                pkt = {
                    "src": fake_ip,
                    "dst": "192.168.1.5",
                    "proto": "TCP/SYN",
                    "bytes": 64,
                    "type": "SYN_FLOOD",
                    "domain": "target.gateway.gov.in"
                }
                self.sock.sendto(json.dumps(pkt).encode("utf-8"), (self.gateway_ip, self.gateway_port))
            self.log(f"Blasted 40 spoofed SYN packets | Target: Gateway [192.168.1.5]")
            time.sleep(0.3)

    def launch_c2(self):
        self.stop_attack()
        self.running = True
        self.status_lbl.config(text="● EXECUTING: STEALTH C2 BEACONING", fg="#cc00ff")
        self.log(">>> INITIATING COBALT STRIKE C2 BEACON LOOP (5.0s ± 5% Jitter)...")
        threading.Thread(target=self._c2_thread, daemon=True).start()

    def _c2_thread(self):
        while self.running:
            pkt = {
                "src": "192.168.1.30",
                "dst": "198.51.100.42",
                "proto": "TCP/HTTPS",
                "bytes": 256,
                "domain": "c2.adversary-command.org",
                "ja4": "t13d1516h2_cobalt",
                "type": "C2_BEACON"
            }
            self.sock.sendto(json.dumps(pkt).encode("utf-8"), (self.gateway_ip, self.gateway_port))
            self.log(f"Transmitted C2 Heartbeat -> 198.51.100.42:443 [Cobalt Strike]")
            time.sleep(1.0)  # Periodic beacon pulse

    def launch_dns(self):
        self.stop_attack()
        self.running = True
        self.status_lbl.config(text="● EXECUTING: DNS TUNNELLING EXFIL", fg="#ffaa00")
        self.log(">>> TRANSMITTING BASE64 ENCODED SECRET VIA DNS PORT 53...")
        threading.Thread(target=self._dns_thread, daemon=True).start()

    def _dns_thread(self):
        while self.running:
            # Generate high-entropy, long base64 tunnel domain
            random_b64 = "".join(random.choices("abcdefghijklmnopqrstuvwxyz0123456789", k=45))
            tunnel_domain = f"{random_b64}.exfil.darknet.ru"
            pkt = {
                "src": "192.168.1.10",
                "dst": "8.8.8.8",
                "proto": "UDP/DNS",
                "port": 53,
                "bytes": 512,
                "domain": tunnel_domain,
                "type": "DNS_TUNNEL"
            }
            self.sock.sendto(json.dumps(pkt).encode("utf-8"), (self.gateway_ip, self.gateway_port))
            self.log(f"Tunnel Query TX: {tunnel_domain[:35]}... (Entropy: >4.5)")
            time.sleep(0.8)

    def launch_encrypted(self):
        self.stop_attack()
        self.running = True
        self.status_lbl.config(text="● EXECUTING: ENCRYPTED MALWARE SESSION", fg="#ff3300")
        self.log(">>> ESTABLISHING TLS 1.3 ENCRYPTED SESSION WITH SLIVER C2 FINGERPRINT...")
        threading.Thread(target=self._encrypted_thread, daemon=True).start()

    def _encrypted_thread(self):
        while self.running:
            pkt = {
                "src": "192.168.1.20",
                "dst": "203.0.113.88",
                "proto": "TCP/TLS1.3",
                "port": 443,
                "bytes": 1024,
                "domain": "cdn-cloud-update.sliver.sh",
                "ja4": "t13d2012h2_sliver",
                "type": "ENCRYPTED_C2"
            }
            self.sock.sendto(json.dumps(pkt).encode("utf-8"), (self.gateway_ip, self.gateway_port))
            self.log(f"TLS ClientHello sent with JA4 signature: 't13d2012h2_sliver'")
            time.sleep(1.0)

    def launch_scan(self):
        self.stop_attack()
        self.running = True
        self.status_lbl.config(text="● EXECUTING: RECONNAISSANCE SCAN", fg="#00d4ff")
        self.log(">>> SCANNING INTERNAL SUBNET HOSTS (FAN-OUT SWEEP)...")
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        while self.running:
            targets = ["192.168.1.10", "192.168.1.20", "192.168.1.30", "192.168.1.5", "192.168.1.100"]
            for target in targets:
                pkt = {
                    "src": "192.168.1.150",
                    "dst": target,
                    "proto": "TCP/SYN",
                    "bytes": 48,
                    "type": "PORT_SCAN",
                    "domain": "recon.internal"
                }
                self.sock.sendto(json.dumps(pkt).encode("utf-8"), (self.gateway_ip, self.gateway_port))
            self.log(f"Scanned {len(targets)} internal subnets from 192.168.1.150")
            time.sleep(0.6)

if __name__ == "__main__":
    gw_ip = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    root = tk.Tk()
    app = AttackerConsole(root, gw_ip)
    root.mainloop()
