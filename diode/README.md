# CHRONOS: Air-Gapped Nuclear SCADA Defense & Optical Data Diode
### Smart India Hackathon 2026 — Problem Statement ID: 26145 (NTRO)
**Title:** AI-Based Detection of Cyber Threats in Unidirectional IP Traffic  
**Target Asset:** BARC / NPCIL Kudankulam Unit 1 Nuclear SCADA & NLDC Power Grid Interconnect  

---

## 📌 Executive Summary: Protecting Critical Infrastructure

In mission-critical operational technology (OT) such as Nuclear Power Plants and National Power Grids, safety-critical systems cannot be connected to standard IT networks. **Hardware optical data diodes** enforce strict unidirectional (simplex) isolation—allowing telemetry to egress for monitoring while **physically eliminating any return communication (ACK / feedback)**.

**CHRONOS** provides a comprehensive 3-tier defense architecture:
1. **Unidirectional Optical Data Diode:** Simplex optical egress via modulated photons. Zero physical inbound path exists, rendering remote exploitation or C2 injection physically impossible.
2. **Continuous-Time Anomaly Scoring (NJ-ODE):** Detects covert data exfiltration, stealth C2 beacons, and DGA DNS tunnels from simplex telemetry using the 4-feature contract ($[\text{iat}, \text{bytes}, \text{entropy}, \text{burst}]$) without requiring TCP reassembly or payload decryption.
3. **Zero-Trust Host Process Sentry:** Instantly detects newly spawned unauthorized executables (`notepad.exe`, `calc.exe`, PowerShell, or malware binaries) on the SCADA console and blasts real-time optical alert frames across the air gap in $< 350\text{ ms}$.

---

## 📁 Active Single-Laptop Scripts

| Script | Role | Description |
| :--- | :--- | :--- |
| **[`nuclear_node.py`](nuclear_node.py)** | **Nuclear SCADA Node** | Streams authentic reactor physics (Temp, Pressure, Coolant Flow, Rods, Power, 50 Hz Grid Freq) + reads real laptop CPU/RAM + watches live process table. |
| **[`qr_gateway.py`](qr_gateway.py)** | **Optical Diode Transmitter** | Aggregates simplex telemetry from port 9999, logs to terminal, and renders the high-contrast animated optical QR diode on screen. |
| **[`nuclear_soc.py`](nuclear_soc.py)** | **Air-Gapped SOC Dashboard** | Industrial dark-mode defense console. Features live reactor gauges, AI anomaly score $\mathcal{S}_{\text{peak}}$ vs $\tau$, host sentry alerts, and dual Webcam / Direct Loopback modes. |
| **[`chronos_soc.py`](chronos_soc.py)** | **Multi-Threat AI SOC** | Extended multi-threat intelligence evaluator covering all 6 NTRO threat categories. |
| **[`pcap_feature_extractor.py`](pcap_feature_extractor.py)** | **Passive Feature Extractor** | Passive network packet featurizer for PCAP analysis (IAT, Entropy, JA4). |
| **[`attacker_console.py`](attacker_console.py)** | **Red-Team Attack Launcher** | GUI launcher for injecting targeted cyber threats into the pipeline. |

---

## 🚀 How to Run on a Single Laptop (3 Terminals)

Open 3 terminal windows on your laptop side-by-side:

### Terminal 1: Nuclear SCADA Telemetry & Host Sentry
```bash
python diode/nuclear_node.py
```

### Terminal 2: Optical Data Diode Transmitter
```bash
python diode/qr_gateway.py
```

### Terminal 3: Air-Gapped Nuclear SOC Dashboard
```bash
python diode/nuclear_soc.py
```

> [!TIP]
> **Single-Laptop Presentation Pro-Tip:**
> On `nuclear_soc.py`, press **`[SPACE]`** anytime to toggle between:
> - **Webcam Optical Mode:** Optical camera scanning from screen or phone.
> - **Direct Simplex Loopback:** Mirrored simplex packet ingest directly on the laptop (ideal for smooth screen-sharing / projector presentations).

---

## 🎮 Live 2-Minute Presentation Walkthrough for Evaluators

1. **Step 1: Baseline Normal Operation**
   - Point out the **Nominal Reactor Vitals**: Core Temp $\approx 295.4^\circ\text{C}$, Pressure $\approx 155.0\text{ bar}$, Grid Frequency $\approx 50.000\text{ Hz}$, Electrical Output $\approx 880\text{ MW}$.
   - Show the **Optical Data Diode**: Modulated photons carrying real-time telemetry with **Zero Inbound Return Path**.
   - Show the **AI Anomaly Score**: $\mathcal{S}_{\text{peak}} \approx 0.08 < \tau = 0.45$ (Nominal Baseline).

2. **Step 2: Live Host Process Breach Demonstration**
   - On your laptop, open **Notepad** (or **Calculator**).
   - In $< 400\text{ ms}$, Terminal 1 catches the newly spawned PID.
   - Terminal 2 encodes the critical event into the optical QR diode.
   - Terminal 3 flashes the glowing **RED DEFENSE ALERT: UNAUTHORIZED PROCESS DETECTED**!

3. **Step 3: Stealth Cyber Attack Demonstration**
   - In Terminal 1, press **`[1]` + ENTER** (Data Exfiltration Flood) or **`[2]` + ENTER** (Stealth C2 Beacon).
   - In Terminal 3, the Peak Anomaly Score $\mathcal{S}_{\text{peak}}$ spikes past $\tau$, and the Threat Attribution Classifier immediately flags the attack category!

4. **Step 4: Physical Coolant Valve Tampering**
   - In Terminal 1, press **`[4]` + ENTER**.
   - The Core Temperature spikes past $348^\circ\text{C}$ and Primary Pressure jumps to $176\text{ bar}$, triggering the physical reactor safety alarms on the SOC dashboard!
   - Press **`[0]` + ENTER** to restore nominal baseline.
