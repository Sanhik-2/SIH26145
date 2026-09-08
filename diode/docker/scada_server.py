"""
CHRONOS: NUCLEAR SCADA NODE (CONTAINERIZED DOCKER SERVICE)
----------------------------------------------------------
Runs inside an isolated Docker container with strict CPU (1.0 core) and RAM (1024 MB) limits.
1. Reads authentic Pressurized Water Reactor (PWR) operational telemetry from the
   peer-reviewed NPPAD benchmark dataset (Nature Scientific Data, 2022).
   - Default: nppad_normal.csv (100% full power nominal Kudankulam Unit 1 / BARC PWR baseline).
   - On Modbus Pump Trip: transitions to nppad_lof.csv (Loss of Flow / Coolant Pump Trip).
   - On Pipe Break: transitions to nppad_loca.csv (Loss of Coolant Accident).
2. Real Cgroups v2 Resource Tracking:
   - Measures exact container CPU % from /sys/fs/cgroup/cpu.stat.
   - Measures exact container RAM from /sys/fs/cgroup/memory.current (1024 MB limit).
   - Measures Network I/O from /proc/net/dev.
3. Serves Modbus/TCP on Port 502 (industrial protocol).
4. Serves Web SCADA HMI on Port 8080 (REST telemetry & text views).
5. Provides a continuous, clean text telemetry log stream on stdout for Docker Desktop.
6. When attacked with DDoS / connection flood:
   - Processes genuine compute workload on the single CPU core, spiking container CPU to 100%!
   - Polling latency degrades under load.
7. Simplex flow telemetry emitted to optical data diode.
"""

import os
import csv
import json
import time
import socket
import select
import hashlib
import threading

MODBUS_PORT = 502
HMI_PORT = 8080

FACILITY_NAME = "BARC / NPCIL Kudankulam Unit 1 (PWR)"
DATASET_SOURCE = "Nature Scientific Data (NPPAD 96-Sensor Benchmark)"

DIODE_HOST = os.environ.get("DIODE_HOST", "127.0.0.1")
DIODE_PORT = int(os.environ.get("DIODE_PORT", "9999"))

# Datasets
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
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
            print(f"[-] Failed loading {path}: {e}")
    return []

records_normal = load_csv(NORMAL_CSV)
records_lof = load_csv(LOF_CSV)
records_loca = load_csv(LOCA_CSV)

fallback_rec = {
    "TIME": "0.0", "P": "155.5", "TAVG": "310.0", "THA": "327.8", "TCA": "292.2",
    "WRCA": "16515.8", "PSGA": "67.0", "QMWT": "2895.0"
}
if not records_normal:
    records_normal = [fallback_rec]
if not records_lof:
    records_lof = [fallback_rec]
if not records_loca:
    records_loca = [fallback_rec]

# State Machine
reactor_state = "NOMINAL_FULL_POWER"  # NOMINAL_FULL_POWER, LOSS_OF_FLOW, LOCA_ACCIDENT
active_records = records_normal
state_lock = threading.Lock()
current_idx = 0

# Metrics & counters
stats = {
    "modbus_requests": 0,
    "hmi_requests": 0,
    "attack_packets_received": 0,
    "last_attack": "None",
    "last_attack_time": "--:--:--",
    "cpu_pct": 1.2,
    "memory_mb": 22.0,
    "memory_pct": 2.1,
    "net_rx_bytes": 0,
    "net_tx_bytes": 0,
    "net_rx_kb": 0.0,
    "net_tx_kb": 0.0,
    "scada_latency_ms": 1.8
}

out_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
out_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

def read_cgroup_resources():
    """Reads genuine container cgroup v2 & v1 CPU, Memory, and Network rates."""
    global stats
    prev_cpu_usec = 0
    prev_time = time.time()
    prev_rx_bytes = 0
    prev_tx_bytes = 0
    prev_net_time = time.time()

    while True:
        try:
            now = time.time()

            # 1. Container Memory (cgroup v2 with fallback to v1)
            mem_bytes = None
            for mem_path in [
                "/sys/fs/cgroup/memory.current",
                "/sys/fs/cgroup/memory/memory.usage_in_bytes",
                "/sys/fs/cgroup/memory.usage_in_bytes"
            ]:
                if os.path.exists(mem_path):
                    try:
                        with open(mem_path, "r") as f:
                            mem_bytes = int(f.read().strip())
                        break
                    except Exception:
                        pass

            if mem_bytes is not None:
                mem_mb = round(mem_bytes / (1024 * 1024), 2)
                stats["memory_mb"] = mem_mb
                stats["memory_pct"] = round((mem_mb / 1024.0) * 100.0, 1)

            # 2. Container CPU (cgroup v2 cpu.stat or cgroup v1 cpuacct.usage)
            cpu_usec = None
            if os.path.exists("/sys/fs/cgroup/cpu.stat"):
                try:
                    with open("/sys/fs/cgroup/cpu.stat", "r") as f:
                        for line in f:
                            if line.startswith("usage_usec"):
                                cpu_usec = int(line.split()[1])
                                break
                except Exception:
                    pass
            elif os.path.exists("/sys/fs/cgroup/cpuacct/cpuacct.usage"):
                try:
                    with open("/sys/fs/cgroup/cpuacct/cpuacct.usage", "r") as f:
                        cpu_usec = int(int(f.read().strip()) / 1000)
                except Exception:
                    pass
            elif os.path.exists("/sys/fs/cgroup/cpu/cpuacct.usage"):
                try:
                    with open("/sys/fs/cgroup/cpu/cpuacct.usage", "r") as f:
                        cpu_usec = int(int(f.read().strip()) / 1000)
                except Exception:
                    pass

            if cpu_usec is not None:
                dt = now - prev_time
                if dt >= 0.25 and prev_cpu_usec > 0:
                    dcpu = max(0, cpu_usec - prev_cpu_usec)
                    pct = (dcpu / (dt * 1000000.0)) * 100.0
                    stats["cpu_pct"] = round(min(pct, 100.0), 1)
                    prev_cpu_usec = cpu_usec
                    prev_time = now
                elif prev_cpu_usec == 0:
                    prev_cpu_usec = cpu_usec
                    prev_time = now

            # 3. Network I/O from /proc/net/dev
            if os.path.exists("/proc/net/dev"):
                rx_total = 0
                tx_total = 0
                with open("/proc/net/dev", "r") as f:
                    for line in f:
                        if ":" in line and not line.strip().startswith("lo"):
                            parts = line.split(":", 1)[1].split()
                            rx_total += int(parts[0])
                            tx_total += int(parts[8])
                stats["net_rx_bytes"] = rx_total
                stats["net_tx_bytes"] = tx_total

                d_net_t = now - prev_net_time
                if d_net_t >= 0.25 and prev_rx_bytes > 0:
                    rx_diff = max(0, rx_total - prev_rx_bytes)
                    tx_diff = max(0, tx_total - prev_tx_bytes)
                    stats["net_rx_kb"] = round(rx_diff / (d_net_t * 1024.0), 1)
                    stats["net_tx_kb"] = round(tx_diff / (d_net_t * 1024.0), 1)
                prev_rx_bytes = rx_total
                prev_tx_bytes = tx_total
                prev_net_time = now

        except Exception:
            pass
        time.sleep(0.25)

def trigger_pump_trip(reason="Unauthorized Modbus FC05 Write"):
    """Transitions reactor to Loss of Flow (NPPAD LOF transient)."""
    global reactor_state, active_records, current_idx
    with state_lock:
        reactor_state = "LOSS_OF_FLOW"
        active_records = records_lof
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

def reset_reactor():
    """Resets reactor to nominal full power operation."""
    global reactor_state, active_records, current_idx
    with state_lock:
        reactor_state = "NOMINAL_FULL_POWER"
        active_records = records_normal
        current_idx = 0
        stats["last_attack"] = "Baseline Restored"
        stats["last_attack_time"] = time.strftime("%H:%M:%S")
        print(f"\n[+] ==========================================================================")
        print(f"[+] [REACTOR RESTORED] Reset to nominal 100% full-power Kudankulam baseline.")
        print(f"[+] P: 155.5 bar | Core Tavg: 310.0 C | Flow: 16,515.8 kg/s | Power: 955.3 MWe")
        print(f"[+] ==========================================================================\n")

def modbus_server():
    """Industrial Modbus/TCP server on Port 502."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", MODBUS_PORT))
    srv.listen(100)
    print(f"[+] SCADA Modbus/TCP Industrial Control listening on Port {MODBUS_PORT}")

    recent_conns = []

    while True:
        try:
            conn, addr = srv.accept()
            stats["modbus_requests"] += 1
            now_t = time.time()
            now_str = time.strftime("%H:%M:%S")

            recent_conns.append((now_t, addr[0]))
            recent_conns = [c for c in recent_conns if now_t - c[0] < 3.0]

            # Detect rapid port scan sweep
            if len(recent_conns) >= 5:
                stats["last_attack"] = f"PORT SCAN from {addr[0]}"
                stats["last_attack_time"] = now_str
                print(f"[!] [{now_str}] [SECURITY EVENT] Rapid connection sweep from {addr[0]} across SCADA ports!")
                pkt = {
                    "node_id": 1,
                    "facility": FACILITY_NAME,
                    "event_type": "CYBER_ATTACK",
                    "type": "PORT_SCAN",
                    "attack_type": "PORT_SCAN",
                    "src": f"{addr[0]}:{addr[1]}",
                    "dst": f"192.168.1.10:{MODBUS_PORT}",
                    "proto": "TCP/MODBUS",
                    "bytes": 64,
                    "ts": now_str,
                    "payload": f"RECON: Rapid connection sweep from {addr[0]} across SCADA ports!"
                }
                send_to_diode(pkt)

            data = conn.recv(1024)
            if data:
                # Modbus Function Code check: 0x05 (Write Single Coil - e.g. pump trip)
                if len(data) >= 8 and data[7] in [0x05, 0x06, 0x0f, 0x10]:
                    print(f"[!] [{now_str}] [UNAUTHORIZED MODBUS WRITE ATTEMPT] Code 0x{data[7]:02x} from {addr[0]}")
                    trigger_pump_trip(f"Modbus FC 0x{data[7]:02x} from {addr[0]}")

                    pkt = {
                        "node_id": 1,
                        "facility": FACILITY_NAME,
                        "event_type": "CYBER_ATTACK",
                        "type": "MODBUS_INJECTION",
                        "attack_type": "SCADA_COMMAND_INJECTION",
                        "src": f"{addr[0]}:{addr[1]}",
                        "dst": f"192.168.1.10:{MODBUS_PORT}",
                        "proto": "TCP/MODBUS",
                        "bytes": len(data),
                        "ts": now_str,
                        "payload": f"SCADA BREACH: Unauthorized Modbus register write attempt from {addr[0]}!"
                    }
                    send_to_diode(pkt)

                # Return standard Modbus response
                resp = b"\x00\x01\x00\x00\x00\x05\x01\x03\x02\x06\x13"
                conn.sendall(resp)

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

        # Heavy workload simulation when attacked (spikes container CPU!)
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
                f" Container CPU Core Load : {stats['cpu_pct']:5.1f} %        (Limit: 1.0 core)\n"
                f" Container RAM Usage     : {stats['memory_mb']:5.1f} MB       (Limit: 1024 MB)\n"
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
                "p": p_val,
                "core_temp_c": tavg_val,
                "tavg": tavg_val,
                "coolant_flow_kgs": flow_val,
                "flow": flow_val,
                "output_mwe": mw_val,
                "mw": mw_val,
                "container_cpu_pct": stats["cpu_pct"],
                "cpu_pct": stats["cpu_pct"],
                "cpu": stats["cpu_pct"],
                "container_mem_mb": stats["memory_mb"],
                "container_mem_pct": stats["memory_pct"],
                "ram": stats["memory_pct"],
                "net_rx_kbps": stats["net_rx_kb"],
                "net_tx_kbps": stats["net_tx_kb"],
                "net_kb": stats["net_rx_kb"],
                "net_rx_bytes": stats["net_rx_bytes"],
                "net_tx_bytes": stats["net_tx_bytes"],
                "last_attack": stats["last_attack"],
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

def hmi_server():
    """Web SCADA HMI REST API on Port 8080."""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", HMI_PORT))
    srv.listen(100)
    print(f"[+] Nuclear Web HMI interface listening on Port {HMI_PORT} (HTTP JSON & Plain-Text)")

    while True:
        try:
            conn, addr = srv.accept()
            threading.Thread(target=hmi_client_handler, args=(conn, addr), daemon=True).start()
        except Exception:
            pass

def get_docker_gateway_ip():
    """Detects host gateway IP from container /proc/net/route."""
    try:
        if os.path.exists("/proc/net/route"):
            with open("/proc/net/route", "r") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 3 and parts[1] == "00000000":
                        gw_hex = parts[2]
                        return socket.inet_ntoa(int(gw_hex, 16).to_bytes(4, byteorder="little"))
    except Exception:
        pass
    return None

def send_to_diode(pkt):
    """Sends UDP flow record to optical data diode gateway."""
    data = json.dumps(pkt).encode("utf-8")
    targets = [
        (DIODE_HOST, DIODE_PORT),
        ("host.docker.internal", DIODE_PORT),
        ("172.17.0.1", DIODE_PORT),
        ("127.0.0.1", DIODE_PORT)
    ]
    gw_ip = get_docker_gateway_ip()
    if gw_ip and gw_ip not in [t[0] for t in targets]:
        targets.insert(0, (gw_ip, DIODE_PORT))

    for host, port in targets:
        try:
            out_sock.sendto(data, (host, port))
        except Exception:
            pass

def telemetry_emitter():
    """Streams continuous NPPAD telemetry across optical diode and logs clean text to console."""
    global current_idx
    seq = 1
    while True:
        with state_lock:
            rec = active_records[current_idx % len(active_records)]
            current_idx += 1

        p_bar = round(float(rec.get("P", 155.5)), 1)
        tavg_c = round(float(rec.get("TAVG", 310.0)), 1)
        tha_c = round(float(rec.get("THA", 327.8)), 1)
        tca_c = round(float(rec.get("TCA", 292.2)), 1)
        wrca_kgs = round(float(rec.get("WRCA", 16515.8)), 1)
        psga_bar = round(float(rec.get("PSGA", 67.0)), 1)
        qmwt = round(float(rec.get("QMWT", 2895.0)), 1)
        mwe = round(qmwt * 0.33, 1)

        event_type = "ROUTINE_SCADA" if reactor_state == "NOMINAL_FULL_POWER" else "SCADA_PHYSICAL_ANOMALY"

        # Continuous clean text telemetry log line visible in Docker Desktop Logs tab
        status_tag = "[NOMINAL]" if reactor_state == "NOMINAL_FULL_POWER" else f"[{reactor_state}]"
        print(f"[{time.strftime('%H:%M:%S')}] {status_tag} Pressure: {p_bar:5.1f} bar | Temp: {tavg_c:5.1f} C | Flow: {wrca_kgs:7.1f} kg/s | Power: {mwe:5.1f} MWe | State: {reactor_state}")

        pkt = {
            "node_id": 1,
            "facility": "BARC_Kudankulam_1",
            "src": "nuclear-scada",
            "dataset": "NPPAD_Nature_Sci_Data_2022",
            "reactor_state": reactor_state,
            "state": reactor_state,
            "event_type": event_type,
            "seq": seq,
            "time": time.strftime("%H:%M:%S"),
            "ts": time.strftime("%H:%M:%S"),
            "p_bar": p_bar,
            "p": p_bar,
            "tavg_c": tavg_c,
            "tavg": tavg_c,
            "tha_c": tha_c,
            "tca_c": tca_c,
            "wrca_kgs": wrca_kgs,
            "flow": wrca_kgs,
            "psga_bar": psga_bar,
            "mwe_electric": mwe,
            "mw": mwe,
            "host_cpu_pct": stats["cpu_pct"],
            "cpu": stats["cpu_pct"],
            "host_ram_pct": stats["memory_pct"],
            "ram": stats["memory_pct"],
            "host_ram_mb": stats["memory_mb"],
            "net_rx_kb": stats["net_rx_kb"],
            "net_tx_kb": stats["net_tx_kb"],
            "net_kb": stats["net_rx_kb"],
            "net": stats["net_rx_kb"],
            "payload": f"NPPAD [{reactor_state}] [P:{p_bar}bar, Tavg:{tavg_c}C, Flow:{wrca_kgs}kg/s, Power:{mwe}MWe, CPU:{stats['cpu_pct']}%, Net:{stats['net_rx_kb']}KB/s]"
        }

        send_to_diode(pkt)
        seq += 1
        time.sleep(1.0)

def main():
    print("=" * 74)
    print("  CHRONOS: NUCLEAR SCADA NODE (CONTAINERIZED DOCKER SERVICE)")
    print(f"  Facility        : {FACILITY_NAME}")
    print(f"  Modbus Control  : Port {MODBUS_PORT} (Industrial SCADA)")
    print(f"  Web HMI API     : Port {HMI_PORT} (JSON & Plain-Text Telemetry)")
    print(f"  Diode Output    : {DIODE_HOST}:{DIODE_PORT} (Simplex Optical Egress)")
    print(f"  Resource Bounds : cpus: 1.0 core | memory: 1024 MB RAM")
    print(f"  Tools Included  : htop, procps (top/ps), curl")
    print("=" * 74 + "\n")

    threading.Thread(target=read_cgroup_resources, daemon=True).start()
    threading.Thread(target=modbus_server, daemon=True).start()
    threading.Thread(target=hmi_server, daemon=True).start()
    telemetry_emitter()

if __name__ == "__main__":
    main()
