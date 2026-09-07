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


def print_banner():
    print("=" * 70)
    print("🛡️  CHRONOS: Passive Threat Detection in Unidirectional IP Traffic")
    print("    Neural Jump-ODE AI Core · Simplex Diode Guard · SOC Console")
    print("=" * 70)


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_banner()
        print("Usage: python run.py <command> [options]\n")
        print("Commands:")
        print("  soc              Launch modern React Full-Stack SOC Console (:8501, HTTPS, WebRTC)")
        print("  qr               Launch Optical Data Diode QR Transmitter Gateway")
        print("  scan             Launch Optical QR Scanner Receiver & AI Core")
        print("  scada            Launch Nuclear SCADA Kudankulam Service (Modbus 502, HMI 8080)")
        print("  btop             Launch Real-Time SCADA Terminal Resource Monitor (cgroups HUD)")
        print("  redteam <attack> Launch Red-Team Cyber Warfare Attacks (NTRO PS #26145 a-f)")
        print("  nuclear-soc      Launch Air-Gapped Nuclear SCADA SOC Defense Console")
        print("  real-packet      Launch Real Packet Network Automation Engine (Optical QR Mesh)")
        print("  nuclear-node     Launch Nuclear SCADA Telemetry & OS Process Sentry Node")
        print("  test             Run unit and integration test suite (pytest)")
        print("\nExamples:")
        print("  python run.py soc                                                # Launch React SOC Dashboard")
        print("  python run.py qr                                                 # Display Optical QR Diode Stream on screen")
        print("  python run.py scada                                              # Launch Kudankulam SCADA node (Ports 502, 8080)")
        print("  python run.py btop                                               # Terminal HUD monitoring CPU/RAM & NPPAD")
        print("  python run.py redteam ddos                                       # Launch Threat [a] Volumetric Flood")
        print("  python run.py redteam modbus                                     # Inject Modbus Pump Trip (Trips Coolant Flow)")
        print("  python run.py scan --phone 10.1.45.X                             # Decode QR using Phone Camera")
        print("  python run.py test                                               # Run full pytest suite")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    extra_args = sys.argv[2:]

    if cmd in ("soc", "react", "ui"):
        # Launch the Starlette/Uvicorn fullstack server
        server_script = REPO_ROOT / "dashboard" / "server.py"
        subprocess.run([sys.executable, str(server_script)] + extra_args)

    elif cmd in ("real-packet", "realpacket", "mesh", "automate"):
        mesh_script = REPO_ROOT / "diode" / "real_packet.py"
        subprocess.run([sys.executable, str(mesh_script)] + extra_args)

    elif cmd in ("qr", "gateway", "transmitter"):
        qr_script = REPO_ROOT / "diode" / "qr_gateway.py"
        subprocess.run([sys.executable, str(qr_script)] + extra_args)

    elif cmd in ("scan", "optical-receiver", "optical"):
        scan_script = REPO_ROOT / "diode" / "scan_receiver.py"
        subprocess.run([sys.executable, str(scan_script)] + extra_args)

    elif cmd in ("nuclear-node", "scada-node", "node"):
        node_script = REPO_ROOT / "diode" / "nuclear_node.py"
        subprocess.run([sys.executable, str(node_script)] + extra_args)

    elif cmd in ("nuclear-service", "scada", "scada-service"):
        svc_script = REPO_ROOT / "diode" / "nuclear_service.py"
        subprocess.run([sys.executable, str(svc_script)] + extra_args)

    elif cmd in ("btop", "monitor", "hud"):
        btop_script = REPO_ROOT / "diode" / "scada_btop.py"
        subprocess.run([sys.executable, str(btop_script)] + extra_args)

    elif cmd in ("redteam", "attack", "offensive"):
        red_script = REPO_ROOT / "diode" / "redteam_arch.py"
        subprocess.run([sys.executable, str(red_script)] + extra_args)

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
