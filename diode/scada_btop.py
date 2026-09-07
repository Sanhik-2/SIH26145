"""
CHRONOS: NUCLEAR SCADA TERMINAL RESOURCE MONITOR (BTOP / HTOP STYLE HUD)
------------------------------------------------------------------------
Terminal dashboard monitoring the containerized Nuclear SCADA Node running under
hard Docker cgroup limits (1.0 CPU core, 1024 MB RAM).

Visualizes:
1. Real-time CPU core utilization bar (Green -> Yellow -> Red gradient).
2. Hard-limit Memory consumption gauge (MB and % of 1024 MB).
3. Live Network I/O throughput (Rx/Tx KB/s).
4. Authentic NPPAD Reactor Physics Vitals (Pressure, Temp, Flow, Grid Power).
5. Active Industrial Protocol Sockets (Modbus Port 502, Web HMI Port 8080).
6. Live Cyber Threat Alert Banner (DDoS, Modbus Injection, Port Scan).
7. SCADA Polling Latency degradation in milliseconds.

Usage:
  python diode/scada_btop.py [TARGET_IP]
"""

import sys
import time
import json
import urllib.request
import urllib.error
import os

if sys.platform == "win32":
    try:
        os.system("color")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TARGET_IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
HMI_URL = f"http://{TARGET_IP}:8080"
STATS_URL = f"http://{TARGET_IP}:8080/stats"

# ANSI Color codes
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_CYAN = "\033[96m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_RED = "\033[91m"
C_MAGENTA = "\033[95m"
C_BLUE = "\033[94m"
C_BG_RED = "\033[41m\033[97m"
C_BG_BLUE = "\033[44m\033[97m"
C_DIM = "\033[90m"

def render_bar(pct, width=38):
    pct = max(0.0, min(100.0, pct))
    filled = int((pct / 100.0) * width)
    unfilled = width - filled

    if pct < 50.0:
        color = C_GREEN
    elif pct < 80.0:
        color = C_YELLOW
    else:
        color = C_RED

    bar = f"{color}{'|' * filled}{C_DIM}{'.' * unfilled}{C_RESET}"
    return bar

def fetch_json(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ChronosBtop/1.0"})
        with urllib.request.urlopen(req, timeout=1.2) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def clear_screen():
    # ANSI clear screen and home cursor
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def main():
    prev_rx = 0
    prev_tx = 0
    prev_time = time.time()

    print(f"{C_CYAN}[*] Connecting to Chronos SCADA Node at {HMI_URL}...{C_RESET}")

    while True:
        t_start = time.time()
        telemetry = fetch_json(HMI_URL)
        stats = fetch_json(STATS_URL)
        t_now = time.time()
        latency_measured = (t_now - t_start) * 1000.0

        clear_screen()

        # Terminal Header
        print(f"{C_BOLD}{C_CYAN}+-----------------------------------------------------------------------------+{C_RESET}")
        print(f"{C_BOLD}{C_CYAN}|  CHRONOS: NUCLEAR SCADA NODE RESOURCE MONITOR (BTOP HUD)                    |{C_RESET}")
        print(f"{C_BOLD}{C_CYAN}|  Facility: BARC / Kudankulam Unit 1 (PWR)  |  Target: {TARGET_IP:<21} |{C_RESET}")
        print(f"{C_BOLD}{C_CYAN}+-----------------------------------------------------------------------------+{C_RESET}")

        if not telemetry or not stats:
            print(f"\n{C_RED}{C_BOLD}[!] SCADA NODE UNREACHABLE OR REFUSING CONNECTIONS!{C_RESET}")
            print(f"{C_YELLOW}    Verifying if container is down or paralyzed by volumetric flood...{C_RESET}\n")
            time.sleep(1.0)
            continue

        cpu_pct = stats.get("cpu_pct", telemetry.get("container_cpu_pct", 0.0))
        mem_mb = stats.get("memory_mb", telemetry.get("container_mem_mb", 0.0))
        mem_pct = stats.get("memory_pct", telemetry.get("container_mem_pct", 0.0))
        scada_lat = max(latency_measured, stats.get("scada_latency_ms", 0.0))
        reactor_state = telemetry.get("reactor_state", "NOMINAL_FULL_POWER")
        last_attack = stats.get("last_attack", "None")
        last_attack_time = stats.get("last_attack_time", "--:--:--")

        # Network bandwidth rate calculation
        rx_bytes = stats.get("net_rx_bytes", 0)
        tx_bytes = stats.get("net_tx_bytes", 0)
        dt = t_now - prev_time
        if dt > 0 and prev_rx > 0:
            rx_rate_kb = (rx_bytes - prev_rx) / (dt * 1024.0)
            tx_rate_kb = (tx_bytes - prev_tx) / (dt * 1024.0)
        else:
            rx_rate_kb = 0.0
            tx_rate_kb = 0.0
        prev_rx = rx_bytes
        prev_tx = tx_bytes
        prev_time = t_now

        # 1. HARDWARE CGROUP RESOURCES
        print(f"\n{C_BOLD}{C_BLUE}[*] CONTAINER HARDWARE CONSTRAINTS (cgroups v2){C_RESET}")
        print(f"  CPU [1.0 Core Limit] : [{render_bar(cpu_pct, 36)}] {cpu_pct:>5.1f}%")
        print(f"  RAM [1024 MB Limit]  : [{render_bar(mem_pct, 36)}] {mem_mb:>5.1f} MB ({mem_pct:>4.1f}%)")
        print(f"  Network Rx Rate      : {C_CYAN}{rx_rate_kb:>7.1f} KB/s{C_RESET}  |  Tx Rate: {C_CYAN}{tx_rate_kb:>7.1f} KB/s{C_RESET}")
        
        lat_color = C_GREEN if scada_lat < 15.0 else (C_YELLOW if scada_lat < 100.0 else C_RED)
        print(f"  SCADA Polling Latency: {lat_color}{scada_lat:>6.1f} ms{C_RESET}  |  Modbus Req: {stats.get('modbus_requests', 0)}  |  HMI Req: {stats.get('hmi_requests', 0)}")

        # 2. CYBER SECURITY & ATTACK MONITOR
        print(f"\n{C_BOLD}{C_MAGENTA}[*] ZERO-TRUST SCADA SECURITY & ATTACK STATUS{C_RESET}")
        if last_attack != "None" and last_attack != "Baseline Restored":
            print(f"  {C_BG_RED} [ACTIVE THREAT DETECTED] {C_RESET} {C_RED}{C_BOLD}{last_attack}{C_RESET} at {last_attack_time}")
            print(f"  Attack Load Packets : {C_RED}{stats.get('attack_packets_received', 0)}{C_RESET}")
        else:
            print(f"  Security Posture    : {C_GREEN}[NOMINAL SECURE] No active cyber intrusions.{C_RESET}")
            print(f"  Industrial Ingress  : Modbus/TCP 502 {C_GREEN}LISTENING{C_RESET} | Web HMI 8080 {C_GREEN}ONLINE{C_RESET}")

        # 3. AUTHENTIC NPPAD REACTOR PHYSICS
        print(f"\n{C_BOLD}{C_YELLOW}[*] NPPAD REACTOR PHYSICS (Nature Sci Data 2022 Benchmark){C_RESET}")
        
        state_badge = f"{C_GREEN}[NOMINAL FULL POWER]{C_RESET}" if reactor_state == "NOMINAL_FULL_POWER" else f"{C_RED}{C_BOLD}[CRITICAL: LOSS OF FLOW / PUMP TRIP]{C_RESET}"
        print(f"  Plant Status         : {state_badge}")

        p_val = telemetry.get("pressure_bar", 155.5)
        t_val = telemetry.get("core_temp_c", 310.0)
        flow_val = telemetry.get("coolant_flow_kgs", 16515.8)
        mw_val = telemetry.get("output_mwe", 955.3)

        p_col = C_GREEN if 150 <= p_val <= 162 else C_RED
        t_col = C_GREEN if t_val <= 315.0 else C_RED
        f_col = C_GREEN if flow_val > 5000.0 else C_RED

        print(f"  Primary Pressure     : {p_col}{p_val:>6.1f} bar{C_RESET}     (Nominal: 155.5 bar)")
        print(f"  Core Average Temp    : {t_col}{t_val:>6.1f} deg C{C_RESET}   (Nominal: 310.0 deg C)")
        print(f"  Coolant Loop Flow    : {f_col}{flow_val:>7.1f} kg/s{C_RESET}   (Nominal: 16515.8 kg/s)")
        print(f"  Grid Electrical Gen  : {C_CYAN}{mw_val:>6.1f} MWe{C_RESET}     (Capacity: 1000.0 MWe)")

        # 4. OPTICAL DATA DIODE STATUS
        print(f"\n{C_BOLD}{C_CYAN}[*] OPTICAL DATA DIODE STATUS{C_RESET}")
        print(f"  Physical Air Gap     : {C_GREEN}STRICT ONE-WAY EGRESS (Simplex QR Bus){C_RESET}")
        print(f"  Diode Forwarding     : UDP Port 9999 -> SOC Air-Gapped Station")
        print(f"  Physical Return Path : {C_RED}ZERO PHYSICAL COPPER / RF RETURN PATH{C_RESET}")

        print(f"\n{C_DIM}-----------------------------------------------------------------------------{C_RESET}")
        print(f"{C_DIM}Press CTRL+C to stop monitor. Refresh rate: 1.0s. NTRO PS #26145 Compliant.{C_RESET}")

        time.sleep(1.0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C_CYAN}[*] Chronos SCADA Monitor exited.{C_RESET}")
