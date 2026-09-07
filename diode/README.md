# CHRONOS: Unidirectional Optical Data Diode & SOC Dashboard

This module implements the **hardware-less optical data diode transport layer** and **real-time air-gapped monitoring enclave** for **SIH 2026 Problem Statement ID: 26145 (NTRO)**.

---

## 📁 Active Scripts

| Script | Role | Description |
| :--- | :--- | :--- |
| **`qr_gateway.py`** | **Optical Diode Emitter** | Central gateway listener that aggregates UDP telemetry, prints live host event logs, and renders the animated high-contrast optical QR diode on screen. |
| **`scan_receiver.py`** | **Air-Gapped Receiver** | Uses webcam/optical sensor to read and decode the optical QR stream, displaying the live dark-mode SOC dashboard with zero physical/protocol return path. |
| **`node_agent.py`** | **Host Node Agent** | Streams real-time host telemetry (CPU %, RAM %, process counts) and detects live application launches (`notepad.exe`, `calc.exe`, `cmd.exe`, etc.). |
| **`chronos_soc.py`** | **Multi-Threat AI SOC** | Full threat intelligence dashboard evaluating all 6 NTRO threat classes (DDoS, C2 Beaconing, DGA, Encrypted Malware JA4, Recon, Exfiltration). |
| **`gateway_diode.py`** | **Chromatic RGB Diode** | High-density 3-channel optical diode multiplexing telemetry across Red, Green, and Blue planes (3x data density). |
| **`pcap_feature_extractor.py`** | **Passive Feature Extractor** | Parses raw network packets (.pcap) and extracts Inter-Arrival Time (IAT), Source-IP Shannon Entropy, JA4 hashes, and byte ratios. |
| **`attacker_console.py`** | **Adversary Attack Console** | Interactive Red-Team cyber warfare launcher for live demonstration of the 6 NTRO cyber attacks. |

---

## 🚀 How to Run (Single-Laptop Demonstration)

Open 3 terminal windows on your laptop:

### Terminal 1: Optical Diode Gateway
```bash
python diode/qr_gateway.py
```

### Terminal 2: Host Telemetry & Event Agent
```bash
python diode/node_agent.py 1 127.0.0.1
```

### Terminal 3: Air-Gapped Receiver & SOC Dashboard
```bash
python diode/scan_receiver.py
```

### Live Test:
1. Open **Notepad** or **Calculator** on your laptop.
2. Terminal 2 immediately detects the process launch.
3. Terminal 1 encodes the event into the optical QR diode.
4. Terminal 3 decodes the optical stream via webcam and flashes the **RED ALERT** on the SOC dashboard in $< 500\text{ ms}$!
