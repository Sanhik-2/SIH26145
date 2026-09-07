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
        print("  soc          Launch the modern React SOC Full-Stack Console (Default: :8501)")
        print("  receiver     Launch Diode Scanner AI Ingestion Engine (UDP receiver)")
        print("  sender       Launch Air-Gapped In-Zone Traffic Generator")
        print("  qr           Launch Optical Data Diode QR Transmitter Gateway")
        print("  scan         Launch Optical QR Scanner Receiver & AI Core")
        print("  nuclear-node Launch Nuclear SCADA Telemetry & OS Process Sentry Node")
        print("  nuclear-soc  Launch Air-Gapped Nuclear SCADA SOC Defense Console")
        print("  dashboard    Launch classic Streamlit SOC Dashboard")
        print("  campaign     Run 300s continuous campaign benchmark (saves plot & json)")
        print("  test         Run unit and integration test suite (pytest)")
        print("\nExamples:")
        print("  python run.py soc")
        print("  python run.py qr")
        print("  python run.py scan --source loopback")
        print("  python run.py nuclear-node")
        print("  python run.py sender --attack exfil_burst --attack-at 20")
        print("  python run.py test")
        sys.exit(0)

    cmd = sys.argv[1].lower()
    extra_args = sys.argv[2:]

    if cmd in ("soc", "react", "ui"):
        # Launch the Starlette/Uvicorn fullstack server
        server_script = REPO_ROOT / "dashboard" / "server.py"
        subprocess.run([sys.executable, str(server_script)] + extra_args)

    elif cmd in ("qr", "gateway", "transmitter"):
        qr_script = REPO_ROOT / "diode" / "qr_gateway.py"
        subprocess.run([sys.executable, str(qr_script)] + extra_args)

    elif cmd in ("scan", "optical-receiver", "optical"):
        scan_script = REPO_ROOT / "diode" / "scan_receiver.py"
        subprocess.run([sys.executable, str(scan_script)] + extra_args)

    elif cmd in ("nuclear-node", "scada-node", "node"):
        node_script = REPO_ROOT / "diode" / "nuclear_node.py"
        subprocess.run([sys.executable, str(node_script)] + extra_args)

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
    main()
