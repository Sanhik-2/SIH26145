#!/usr/bin/env python3
"""
CHRONOS Unified CLI Runner
Allows running any component from anywhere without directory confusion:
  python run.py soc                    # Launch modern React SOC fullstack dashboard
  python run.py receiver               # Launch diode scanner AI receiver
  python run.py sender --attack exfil_burst  # Launch air-gap in-zone traffic sender
  python run.py dashboard              # Launch classic Streamlit dashboard
  python run.py test                   # Run full test suite
  python run.py campaign               # Run 300s continuous campaign benchmark
"""
import os
import sys
import subprocess
from pathlib import Path

# Always anchor to the repository root directory
REPO_ROOT = Path(__file__).resolve().parent
os.chdir(REPO_ROOT)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def print_banner():
    print("=" * 70)
    print("🛡️  CHRONOS: Passive Threat Detection in Unidirectional IP Traffic")
    print("    Neural Jump-ODE AI Core · Simplex Diode Guard · SOC Console")
    print("=" * 70)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_banner()
        print("Commands (4-System Physical Air-Gap Pipeline):")
        print("  system1          System 1: Launch Laptop Dashboard & NJ-ODE Continuous AI Scanner")
        print("  system2          System 2: Launch Optical Data Diode QR Generator Gateway")
        print("  system3 [SYS2_IP] System 3: Launch Useful SCADA Log Sender to System 2")
        print("  system4 <atk> [SYS2_IP] System 4: Launch Attacking Node (Red-Team Cyber Warfare)")
        print("  soc              Alias for system1 (React Full-Stack SOC Console)")
        print("  qr               Alias for system2 (Optical QR Transmitter Gateway)")
        print("  nuclear-node     Alias for system3 (Kudankulam SCADA Telemetry Node)")
        print("  redteam <atk>    Alias for system4 (Red-Team Cyber Attacks a-f)")
        print("  scan             Launch Optical QR Scanner Receiver & AI Core")
        print("  scada            Launch Nuclear SCADA Kudankulam Service (Modbus 502, HMI 8080)")
        print("  btop             Launch Real-Time SCADA Terminal Resource Monitor (cgroups HUD)")
        print("  nuclear-soc      Launch Air-Gapped Nuclear SCADA SOC Defense Console")
        print("  usb              Launch Physical USB Wire Cable Bridge (Type-A to C / Type-C to C)")
        print("  real-packet      Launch Real Packet Network Automation Engine (Optical QR Mesh)")
        print("  test             Run unit and integration test suite (pytest)")
        print("\nExamples:")
        print("  python run.py system1                                            # System 1: Laptop Dashboard & AI")
        print("  python run.py system2                                            # System 2: Display Optical QR Diode Stream")
        print("  python run.py system3 192.168.1.50                               # System 3: Stream SCADA logs to System 2")
        print("  python run.py system4 ddos 192.168.1.50                          # System 4: Launch DDoS attack targeting System 2")
        print("  python run.py real-packet --gui --scada-host 192.168.137.1       # Real packet optical QR mesh with GUI")
        print("  python run.py test                                               # Run full pytest suite")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    extra_args = sys.argv[2:]

    if cmd in ("system1", "sys1", "system-1", "sys-1", "soc", "react", "ui"):
        # System 1: Starlette/Uvicorn fullstack server + continuous NJ-ODE AI
        server_script = REPO_ROOT / "dashboard" / "server.py"
        subprocess.run([sys.executable, str(server_script)] + extra_args)

    elif cmd in ("system2", "sys2", "system-2", "sys-2", "qr", "gateway", "transmitter"):
        # System 2: Optical QR generator gateway
        qr_script = REPO_ROOT / "diode" / "qr_gateway.py"
        subprocess.run([sys.executable, str(qr_script)] + extra_args)

    elif cmd in ("system3", "sys3", "system-3", "sys-3", "nuclear-node", "scada-node", "node"):
        # System 3: In-zone useful SCADA log & telemetry sender
        node_script = REPO_ROOT / "diode" / "nuclear_node.py"
        subprocess.run([sys.executable, str(node_script)] + extra_args)

    elif cmd in ("system4", "sys4", "system-4", "sys-4", "redteam", "attack", "offensive"):
        # System 4: Attacking node targeting System 2
        red_script = REPO_ROOT / "diode" / "redteam_arch.py"
        subprocess.run([sys.executable, str(red_script)] + extra_args)

    elif cmd in ("real-packet", "realpacket", "reak-packet", "reakpacket", "real_packet", "reak_packet", "real", "reak", "mesh", "automate", "packet", "packets"):
        mesh_script = REPO_ROOT / "diode" / "real_packet.py"
        subprocess.run([sys.executable, str(mesh_script)] + extra_args)

    elif cmd in ("scan", "optical-receiver", "optical"):
        scan_script = REPO_ROOT / "diode" / "scan_receiver.py"
        subprocess.run([sys.executable, str(scan_script)] + extra_args)

    elif cmd in ("nuclear-service", "scada", "scada-service"):
        svc_script = REPO_ROOT / "diode" / "nuclear_service.py"
        subprocess.run([sys.executable, str(svc_script)] + extra_args)

    elif cmd in ("btop", "monitor", "hud"):
        btop_script = REPO_ROOT / "diode" / "scada_btop.py"
        subprocess.run([sys.executable, str(btop_script)] + extra_args)

    elif cmd in ("nuclear-soc", "soc-gui"):
        soc_script = REPO_ROOT / "diode" / "nuclear_soc.py"
        subprocess.run([sys.executable, str(soc_script)] + extra_args)

    elif cmd == "receiver":
        receiver_script = REPO_ROOT / "demo" / "scan_receiver.py"
        subprocess.run([sys.executable, str(receiver_script)] + extra_args)

    elif cmd == "sender":
        sender_script = REPO_ROOT / "demo" / "inzone_sender.py"
        subprocess.run([sys.executable, str(sender_script)] + extra_args)

    elif cmd in ("dashboard", "streamlit"):
        dash_script = REPO_ROOT / "dashboard" / "app.py"
        subprocess.run(["streamlit", "run", str(dash_script)] + extra_args)

    elif cmd in ("usb", "wire", "cable"):
        usb_script = REPO_ROOT / "diode" / "usb_bridge.py"
        subprocess.run([sys.executable, str(usb_script)] + extra_args)

    elif cmd in ("test", "tests", "pytest"):
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"] + extra_args)

    elif cmd == "campaign":
        eval_script = REPO_ROOT / "evaluate_campaign.py"
        subprocess.run([sys.executable, str(eval_script), "--multiregime"] + extra_args)

    else:
        print(f"Unknown command: '{cmd}'. Run 'python run.py --help' for available commands.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
