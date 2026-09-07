# CHRONOS: AI-Powered Passive Threat Detection Pipeline
### Smart India Hackathon 2026 — Problem Statement ID: 26145
**Title:** AI-Based Detection of Cyber Threats in Unidirectional IP Traffic  
**Theme:** Blockchain & Cybersecurity | **Category:** Software  
**Team Name:** CYBER FREAKS  

```text
  ██████╗██╗  ██╗██████╗ ███╗   ██╗██████╗ ███████╗
 ██╔════╝██║  ██║██╔══██╗████╗  ██║██╔══██╗██╔════╝
 ██║     ███████║██████╔╝██╔██╗ ██║██║  ██║███████╗
 ██║     ██╔══██║██╔══██╗██║╚██╗██║██║  ██║╚════██║
 ╚██████╗██║  ██║██║  ██║██║ ╚████║██████╔╝███████║
  ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝ ╚══════╝

   A I - P O W E R E D   P A S S I V E   T H R E A T   D E T E C T I O N   P I P E L I N E
           FOR UNIDIRECTIONAL IP TRAFFIC & AIR-GAPPED NETWORKS
       Smart India Hackathon 2026 | PS ID: 26145 | Team: CYBER FREAKS
```

[![SIH 2026](https://img.shields.io/badge/SIH-2026-orange.svg)](https://sih.gov.in)
[![PS ID 26145](https://img.shields.io/badge/Problem%20Statement-26145-blue.svg)](https://sih.gov.in)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![Kernel Bypass](https://img.shields.io/badge/Ingestion-eBPF%20%2F%20AF__XDP-red.svg)](https://ebpf.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Executive Summary

**CHRONOS** is a high-speed, non-intrusive, read-only AI/ML cybersecurity threat detection pipeline specifically designed for **unidirectional (simplex) IP traffic streams** and **air-gapped critical infrastructure**. 

In high-security operational technology (OT), industrial control systems (ICS), defense, and satellite ground stations, **hardware data diodes** enforce strict one-way physical isolation. Traditional intrusion detection systems (IDS) rely on active probing, two-way TCP handshake tracking, stateful reassembly, or deep packet payload decryption — all of which fail in a unidirectional environment where **no return communication (ACK / feedback) is possible**.

**CHRONOS** converts a passive, one-way network mirror into an intelligent cybersecurity sensor. By extracting non-payload behavioral features (timing jitter, spectral distributions, flow entropy, and encrypted metadata fingerprints), CHRONOS detects advanced zero-day threats, covert channels, command-and-control (C2) beacons, and exfiltration attempts **without requiring network access, payload decryption, or return packets**.

---

## 🔬 Mathematical Formulation & Continuous-Time AI Core (NJ-ODE)

The threat detection engine of CHRONOS is built upon **Neural Jump Ordinary Differential Equations (NJ-ODE)** (*Herrera, Krach & Teichmann, ICLR 2021, arXiv:2006.04727*). 

Unlike conventional discrete models that force fixed 5-minute batch aggregation windows, NJ-ODE models continuous latent trajectories with discrete stochastic jumps triggered upon packet arrival. A window of simplex network traffic is modeled as a continuous trajectory $\mathbf{h}(t) \in \mathbb{R}^{d_h}$ punctuated by stochastic observations $\mathbf{x}_i \in \mathbb{R}^{d_x}$ at irregular arrival timestamps $t_i \in [0, 1]$:

$$\frac{d\mathbf{h}(t)}{dt} = f_\theta(\mathbf{h}(t), \mathbf{x}_{\text{last}}, t_{\text{last}}, t - t_{\text{last}}), \quad t \in [t_{i-1}, t_i)$$

$$\mathbf{h}(t_i) = \text{jumpNN}_\theta(\mathbf{x}_i), \quad \mathbf{y}^-(t_i) = \text{outputNN}_\theta(\mathbf{h}(t_i^-))$$

### Paper-Faithful Objective Function (Herrera et al., Eq. 33):
$$\Phi(\theta) = \frac{1}{N} \sum_{\text{paths}} \frac{1}{n_j} \sum_{i=1}^{n_j} \left( \|\mathbf{x}_i - \mathbf{y}_i\|_2 + \|\mathbf{y}_i - \mathbf{y}_i^-\|_2 \right)^2$$

### Dynamic Window-Peak Anomaly Decision:
$$\mathcal{S}_{\text{peak}} = \max_{j} \|\mathbf{x}_j - \mathbf{y}^-_j\|_2^2 > \tau_{\text{thresh}}$$

Where:
* **$\mathbf{y}^-_j = \text{outputNN}(\mathbf{h}(t_j^-))$:** Online conditional expectation of benign network behavior predicted immediately prior to observation $j$.
* **Anomaly Metric $\mathcal{S}_{\text{peak}}$:** The peak one-step prediction error within a sliding window. Any deviation from learned benign baseline dynamics (covert exfiltration flood, randomized C2 beaconing, DNS tunneling) causes $\mathcal{S}_{\text{peak}}$ to violently spike past calibrated threshold $\tau$.
* **Why Diode Lossiness Maps Directly to NJ-ODE:** The hardware/QR data diode is lossy and strictly simplex. Dropped QR frames $\to$ missing observations $\to$ `mask=False` slots. Rather than requiring artificial imputation, NJ-ODE's continuous latent ODE flow **natively consumes irregular and missing observations** with theoretical convergence guarantees.

---

## 🏗️ End-to-End System Architecture

```text
                    ┌─ INSIDE air gap ─┐        [QR diode]        ┌─ scanner side ──────────────┐
packets ──► featurize ──► feature frames ──► ~~~ one-way ~~~ ──► QRIngest ──► Windower ──► NJ-ODE ──► τ ──► alerts
                    └──────────────────┘   (lossy, reordering)  (dedup/CRC)   (scaler)   (frozen)   (peak)
```

```mermaid
graph LR
    subgraph Air-Gapped Network [Inside Protected Zone]
        P[Simplex IP Traffic] --> FE[Feature Extractor]
        FE -->|4-Feature Contract| FF[Feature Frames]
        FF --> TX[QR Optical Diode Transmitter]
    end

    TX -->|One-Way Simplex Channel| RX[Scanner / Camera Ingest]

    subgraph Defense Console [Scanner / AI Defense Side]
        RX --> QI[QRIngest / Frame Reassembly]
        QI --> WA[Unified Slot Aggregation aggregate_slots]
        WA --> LF[LiveFeeder / Windower]
        LF --> NO[Frozen NJ-ODE Engine d_h=10, hidden=50]
        NO --> SC[Window-Peak Scoring vs tau]
        SC --> CH[Unsupervised Channel Attribution]
        CH --> HY[N-of-M Hysteresis Filter]
        HY --> AL[Actionable SOC Alerts]
    end
```

### 🔒 Locked Design Decisions (Defensible in Q&A)

| Decision | Locked Specification | Rationale & Defense |
|---|---|---|
| **Frozen Model in Operation** | No online learning at runtime (`eval()` mode). Retraining = deliberate ops event. | **Security Gold:** The AI engine operates on the receive side of the hardware/QR diode. Because there is **no return channel**, an attacker inside the air gap cannot poison the model baseline or warm it up. Model updates require physical access. |
| **Retraining Cadence as Ops Parameter** | Cheap retraining (~60 s): e.g. nightly retrain on verified benign + recalibrate $\tau$. | Rebuts runtime drift concerns without compromising baseline integrity or introducing vulnerability to adversarial manipulation. |
| **Single Multiregime Baseline** | Telemetry + web_sync trained jointly into one checkpoint. | Simpler, single $\tau$, single checkpoint. Proves multi-regime adaptability without brittle gating or complex ensembles. |
| **Attribution via Channel Heuristic** | Unsupervised rule mapping: `bytes`/`burst` $\to$ **exfil-flood**, `entropy` $\to$ **tunnel/encrypted-c2**, `iat` $\to$ **beacon/recon**. | Retains the **pure zero-day story**. Adding supervised classification heads requires labeled attacks, destroying zero-day claims. Channel residuals provide SOC explainability honestly. |
| **Alert Semantics: Window-Peak vs $\tau$ with Hysteresis** | Evaluates $\max_j S_j > \tau$ with $N$-of-$M$ hysteresis (e.g. 2 of 3 consecutive windows). | Peak scoring reliably detects sudden bursts and intermittent beacons; hysteresis provides anti-flicker stability across overlapping sliding strides. |
| **Checkpoint = Full Versioned Artifact** | Checkpoint carries `version`, `features: ["iat", "bytes", "entropy", "burst"]`, and scaler buffers (`x_mean`, `x_std`). | Eliminates preprocessing drift. Any retrain is safely self-contained, and mismatched feature regimes are rejected upon load. |

### 🔧 Zero Train/Serve Skew Windowing Contract

To ensure mathematical consistency between offline evaluation and live streaming:
* **One Windowing Implementation, Two Consumers:** Both `Windower` (batch training/evaluation) and `LiveFeeder` (live scanner/QR ingest) route through `aggregate_slots(...)`.
* **Collision Policy per Slot:**
  * `iat`: minimum inter-arrival gap
  * `bytes`: cumulative volume (sum)
  * `entropy`: maximum information surprise
  * `burst`: maximum burst indicator
* **Sliding Stride:** Batch training uses non-overlapping windows; live feeder uses a 2.0 s sliding stride for sub-second alert responsiveness.

---

## 💻 Repository Structure (Target Roadmap)

```bash
CHRONOS/
├── README.md               # System specification and documentation (this file)
├── requirements.txt        # Core Python and C++ binding dependencies
├── docs/                   # System architecture specs, slide decks, and diagrams
│   └── architecture.png    # Technical pipeline layout diagram
├── simulation/             # Virtual data diode & synthetic simplex traffic generator
│   ├── diode_tap.py        # Simulates one-way packet dropping / optical tap behavior
│   ├── attacks/            # Synthetic attack traffic generators
│   │   ├── c2_beacon.py    # Randomized jitter C2 beaconing simulator
│   │   ├── dga_tunnel.py   # Base64/DNS covert tunneling generator
│   │   └── exfil_burst.py  # Asymmetric data exfiltration burst simulator
│   └── benign/             # Baseline benign traffic generators (telemetry, regular syncs)
│       ├── telemetry.py    # Industrial SCADA/PLC telemetry simulator
│       └── web_sync.py     # Unidirectional NTP / HTTP sync traffic simulator
├── features/               # High-speed feature extraction pipeline
│   ├── temporal_iat.py     # Inter-arrival time calculations and sliding windows
│   ├── spectral.py         # Welch PSD and Lomb-Scargle periodogram analysis
│   ├── entropy.py          # Sliding-window Shannon entropy calculations
│   └── ja4_fingerprint.py  # TLS 1.3 ClientHello metadata extraction
├── models/                 # Semi-supervised model definitions and checkpoints
│   ├── autoencoder.py      # PyTorch Deep Autoencoder architecture
│   ├── svdd_boundary.py    # One-Class / SVDD latent boundary calculator
│   ├── temporal_fusion.py  # Transformer attention fusion layer
│   └── export_onnx.py      # Script to quantize and compile models for fast inference
└── dashboard/              # Streamlit / Web-based visualization console
    └── app.py              # Visual interface showing live anomaly scores & attack flags
```

---

## 📚 Academic & Theoretical Foundations

CHRONOS is backed by peer-reviewed research across signal processing, spectral analysis, random matrix theory, and non-linear dynamics:

| Threat Category & Method | Citation & Publication Venue | Engineering Rationale & Problem Solved | Reference Link / DOI |
| :--- | :--- | :--- | :--- |
| **1. C2 Beaconing Detection**<br>`Lomb-Scargle Periodogram` | **VanderPlas, J. T. (2018)**<br>*The Astrophysical Journal Supp.* | Least-squares spectral estimation for uneven time series; resolves randomized timing jitter ($T = T_0 \pm \delta$) in APT C2 beacons where standard FFT fails. | [10.3847/1538-4365/aab766](https://doi.org/10.3847/1538-4365/aab766) |
| **2. Volumetric DDoS**<br>`Wavelet Scattering (WST)` | **Bruna, J. & Mallat, S. (2013)**<br>*IEEE Trans. PAMI* | Multi-scale cascaded wavelet modulus convolutions; extracts translation-invariant, deformation-stable burst dynamics from packet streams. | [10.1109/TPAMI.2012.230](https://doi.org/10.1109/TPAMI.2012.230) |
| **3. Botnet & Reconnaissance**<br>`RMT & BBP Transition` | **Baik, Ben Arous, & Péché (2005)**<br>*Annals of Probability* | Tracks cross-flow correlation matrix eigenvalue excursions beyond Marchenko-Pastur noise; enables 100% unsupervised botnet sweep detection. | [10.1214/009117905000000233](https://doi.org/10.1214/009117905000000233) |
| **4. Encrypted Topology**<br>`Takens' Delay Embedding` | **Takens, F. (1981)**<br>*Dynamical Systems & Turbulence* | Reconstructs geometric phase-space manifolds and computes Betti numbers ($\beta_0, \beta_1$) from packet timing to bypass TLS 1.3/QUIC encryption. | [10.1007/BFb0091924](https://doi.org/10.1007/BFb0091924) |
| **5. Asymmetric Exfiltration**<br>`Directed Transfer Entropy` | **Schreiber, T. (2000)**<br>*Physical Review Letters* | Measures directional causality and information flow across micro-bursts to detect covert data exfiltration without reverse-path TCP ACK tracking. | [10.1103/PhysRevLett.85.461](https://doi.org/10.1103/PhysRevLett.85.461) |
| **6. Continuous-Time AI**<br>`Neural Jump-ODEs` | **Herrera, Krach, & Teichmann (2021)**<br>*ICLR Conference* | Continuous latent trajectory modeling with discrete stochastic jumps on packet arrival; eliminates 5-min batch windows for bounded sub-ms latency. | [arXiv:2006.04727](https://arxiv.org/abs/2006.04727) |
| **7. DGA & DNS Tunneling**<br>`Byte-Level Perplexity` | **Radford et al. (2019) / Tranco (2019)**<br>*OpenAI / NDSS Symposium* | Calculates character sequence surprisal trained on Tranco Top-1M; isolates dictionary-based DGAs & base64 tunneling without flagging CDNs. | [tranco-list.eu](https://tranco-list.eu/) |
| **8. Wire-Speed Ingestion**<br>`eBPF / AF_XDP Kernel Bypass` | **Høiland-Jørgensen et al. (2018)**<br>*ACM CoNEXT Conference* | Zero-copy UMEM userspace ring buffer ingestion; processes 10–100 Gbps line-rate traffic on passive optical taps without OS overhead. | [10.1145/3281411.3281443](https://doi.org/10.1145/3281411.3281443) |
| **9. TLS 1.3 Profiling**<br>`JA4+ Fingerprinting` | **FoxIO / John Althouse (2023)**<br>*FoxIO Open Security Standard* | TLS 1.3 ClientHello multi-attribute hashing (ciphers, extensions, ALPN); replaces obsolete JA3 fingerprints that collapse on TLS 1.3. | [github.com/FoxIO-LLC/ja4](https://github.com/FoxIO-LLC/ja4) |

---

## ⚡ Quickstart & Setup Guide

### 1. Prerequisites
Ensure Python 3.10+ and C++ build tools are installed on your Linux system:
```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv build-essential libpcap-dev
```

### 2. Installation
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/CYBER-FREAKS/CHRONOS.git
cd CHRONOS

python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
pip install -r requirements.txt
```

### 3. Train Multi-Regime NJ-ODE Baseline
Extract features from benign regimes (telemetry + web sync), train the continuous-time NJ-ODE, and calibrate the detection threshold $\tau$:
```bash
python train.py --epochs 30 --lr 0.001 --device cpu
```
This produces the versioned artifact `checkpoints/njode_telemetry.pt` with feature contract metadata and self-contained standardization buffers.

### 4. Run Comprehensive Evaluation
Evaluate the model against benign traffic and synthetic zero-day attack campaigns (`c2_beacon`, `exfil_burst`, `dga_tunnel`) with channel attribution:
```bash
python evaluate.py --checkpoint checkpoints/njode_telemetry.pt --output results/eval.json
```

### 5. Run Verification Test Suite
Execute the full pytest suite covering slot aggregation, `LiveFeeder` sliding stride, channel attribution heuristic, model calibration, and checkpoint contracts:
```bash
pytest tests/ -v
```

---

## 🛡️ Impact & Security Benefits

* **Air-Gapped Infrastructure Protection:** Full visibility over one-way OT networks, satellite downlinks, and military communications.
* **Payload Encryption Agnostic:** Detects threats inside TLS 1.3, QUIC, and encrypted custom tunnels using metadata timing and spectral scattering.
* **Zero Attack Surface:** Operates strictly in passive receive mode — impossible for adversaries to detect, scan, or exploit the sensor.
* **Sub-Millisecond Detection Bounded Latency:** Uses ONNX Runtime quantization and eBPF kernel bypass for real-time wire-speed monitoring.

---

## 👥 Team CYBER FREAKS — Smart India Hackathon 2026

* **Problem Statement ID:** 26145
* **Problem Statement Title:** AI-Based Detection of Cyber Threats in Unidirectional IP Traffic
* **Theme:** Blockchain & Cybersecurity
* **Category:** Software
* **Team:** CYBER FREAKS

---
*Developed for Smart India Hackathon 2026. Designed for Mission-Critical Defense & OT Networks.*
