"""
CHRONOS BULLETPROOF NODE AGENT (Runs on Laptop 1, 2, or 3)
----------------------------------------------------------
Sends real-time telemetry + process execution alerts to Termux on phone.
"""

import socket
import json
import time
import sys
import threading
import psutil

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

USER_APPS = {
    "notepad.exe": "Text Editor (Notepad)",
    "calc.exe": "Calculator",
    "calculatorapp.exe": "Calculator",
    "cmd.exe": "Command Prompt (CMD)",
    "powershell.exe": "PowerShell",
    "mspaint.exe": "MS Paint",
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge"
}

def monitor_apps(sock, phone_ip, phone_port, node_id):
    last_seen = set()
    while True:
        try:
            current = set()
            for p in psutil.process_iter(['name', 'pid']):
                try:
                    name = p.info['name'].lower()
                    if name in USER_APPS:
                        current.add((name, p.info['pid']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            new_apps = current - last_seen
            for app_name, pid in new_apps:
                friendly = USER_APPS[app_name]
                now = time.strftime("%H:%M:%S")
                # Send with BOTH event types so both old & new Termux scripts catch it!
                pkt = {
                    "node_id": node_id,
                    "sender": f"Node {node_id}",
                    "receiver": "Gateway",
                    "event_type": "PROCESS_EXECUTION",
                    "type": "APP_LAUNCH",
                    "app": friendly,
                    "pid": pid,
                    "payload": f"HOST EVENT: '{friendly}' executed! (PID: {pid})",
                    "time": now
                }
                sock.sendto(json.dumps(pkt).encode("utf-8"), (phone_ip, phone_port))
                print(f"\n[🚨 LIVE EVENT DETECTED] Host opened '{friendly}' (PID: {pid}) -> Sent to Termux!\n")

            last_seen = current
        except Exception:
            pass
        time.sleep(0.4)

def keyboard_trigger(sock, phone_ip, phone_port, node_id):
    while True:
        try:
            input()  # When user presses ENTER in terminal
            now = time.strftime("%H:%M:%S")
            pkt = {
                "node_id": node_id,
                "sender": f"Node {node_id}",
                "receiver": "Gateway",
                "event_type": "PROCESS_EXECUTION",
                "type": "APP_LAUNCH",
                "app": "UNAUTHORIZED DEMO EXECUTION",
                "pid": 9999,
                "payload": "ALERT: Unauthorized Process 'hacker_tool.exe' executed on Node!",
                "time": now
            }
            sock.sendto(json.dumps(pkt).encode("utf-8"), (phone_ip, phone_port))
            print(f"\n[⚡ MANUAL TRIGGER FIRED] Sent instant Host Event alert to Termux ({phone_ip})!\n")
        except Exception:
            pass

def main():
    node_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    phone_ip = sys.argv[2] if len(sys.argv) > 2 else "10.135.74.79"
    phone_port = 9999

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    print("=" * 65)
    print(f"  CHRONOS NODE {node_id} ACTIVE")
    print(f"  Target Termux Hub on Phone: {phone_ip}:{phone_port}")
    print(f"  -> Open Notepad / Calculator to trigger automatic alert")
    print(f"  -> OR press [ENTER] in this window to fire instant demo alert!")
    print("=" * 65 + "\n")

    threading.Thread(target=monitor_apps, args=(sock, phone_ip, phone_port, node_id), daemon=True).start()
    threading.Thread(target=keyboard_trigger, args=(sock, phone_ip, phone_port, node_id), daemon=True).start()

    seq = 1
    while True:
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        now = time.strftime("%H:%M:%S")

        pkt = {
            "node_id": node_id,
            "sender": f"Node {node_id}",
            "receiver": "Gateway",
            "event_type": "ROUTINE",
            "cpu_pct": cpu,
            "ram_pct": ram,
            "payload": f"Normal Telemetry [CPU: {cpu}%, RAM: {ram}%]",
            "seq": seq,
            "time": now
        }

        try:
            sock.sendto(json.dumps(pkt).encode("utf-8"), (phone_ip, phone_port))
            print(f"[{now}] Node {node_id} Live Telemetry | CPU: {cpu}% | RAM: {ram}%")
        except Exception as e:
            print(f"[-] Send error: {e}")

        seq += 1
        time.sleep(1.5)

if __name__ == "__main__":
    main()
