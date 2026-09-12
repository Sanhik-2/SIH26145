# CHRONOS: Real Dataset Methodology & AI Model Architecture Specification
### Passive Cyber Threat Detection in Unidirectional IP Traffic
**Smart India Hackathon 2026 | Problem Statement ID: 26145**  
**Organization:** National Technical Research Organisation (NTRO)  
**Department:** National Technical Research Organisation (NTRO)  
**Theme:** Blockchain & Cybersecurity | **Category:** Software  
**Team Name:** CYBER FREAKS  

---

## 📌 1. Executive Summary & Problem Overview

Critical-infrastructure operators observe their gateway and peering links using **passive optical mirroring or hardware data diodes** that copy traffic into a monitoring enclave in **one direction only**. The enclave has full passive visibility over every packet crossing the physical link, but possesses **no physical or protocol-level path back into the production network**. 

This physical design eliminates an entire class of remote exploitation vectors: a compromised monitoring or analytics sensor can never become a pivot into the core industrial control system (ICS), operational technology (OT), or defense networks. Furthermore, it preserves an inviolable, tamper-proof chain of custody for forensic analysis.

However, this one-way architectural constraint introduces fundamental operational challenges:
1. **Strictly Read-Only Ingest:** The threat detection engine cannot send active probes, cannot complete TCP three-way handshakes, cannot track reverse-path TCP ACK states, and cannot issue inline TCP resets (`RST`) or firewall blocks back across the diode.
2. **Zero Payload Decryption:** Modern traffic crossing peering links is predominantly encrypted (TLS 1.3, QUIC, SSH). Decryption at line rate inside an air-gapped enclave without private keys is computationally and cryptographically impossible. Inspection must rely strictly on unencrypted packet metadata, temporal rhythms, and encrypted flow fingerprints.
3. **Continuous Streaming Inference:** Threat scoring must happen incrementally with bounded sub-millisecond latency to raise actionable security alerts in near real time, rather than waiting for an end-of-day batch processing run.

**CHRONOS** solves this challenge through a multi-modal, continuous-time AI cybersecurity pipeline powered by **Neural Jump Ordinary Differential Equations (NJ-ODE)** and **Dual-Model Semi-Supervised Manifold Learning**. Grounded in authentic, peer-reviewed open datasets (**CIC-IDS2017**, **Tranco Top-1M**, **abuse.ch SSLBL/Feodo**, and **Nature Scientific Data NPPAD**), CHRONOS detects, classifies, and attributes the full spectrum of cyber threats using non-payload behavioral signatures alone.

---

## 🌐 2. Dedicated Real Datasets & Provenance

In accordance with the NTRO problem statement and rigorous scientific evaluation standards, CHRONOS ingests and models authentic datasets from dedicated, authoritative cybersecurity research sources:

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                   CHRONOS AUTHENTIC BENCHMARK DATASET REPOSITORY                 │
├──────────────────────────┬─────────────────────────────┬─────────────────────────┤
│ Dataset Source           │ Research Origin / Venue     │ Target Feature Domain   │
├──────────────────────────┼─────────────────────────────┼─────────────────────────┤
│ 1. CIC-IDS2017           │ Canadian Institute for      │ Flow rate, IAT, length, │
│    Benchmark Sample      │ Cybersecurity (UNB)         │ fan-out, DoS & PortScan │
├──────────────────────────┼─────────────────────────────┼─────────────────────────┤
│ 2. Tranco Top-1M         │ Le Pochat et al., NDSS 2019 │ Benign DNS domains,     │
│    Scientific Ranking    │ tranco-list.eu              │ n-gram surprisal, len   │
├──────────────────────────┼─────────────────────────────┼─────────────────────────┤
│ 3. abuse.ch SSLBL        │ abuse.ch Swiss Cyber Threat │ Authentic TLS JA3/JA4   │
│    JA3/JA4 Fingerprints  │ Intelligence Platform       │ malware fingerprints    │
├──────────────────────────┼─────────────────────────────┼─────────────────────────┤
│ 4. abuse.ch Feodo        │ Feodo Tracker               │ Active Botnet C2 IP &   │
│    Botnet C2 Telemetry   │ abuse.ch                    │ port endpoints          │
├──────────────────────────┼─────────────────────────────┼─────────────────────────┤
│ 5. NPPAD (Nature Sci     │ Tsinghua INET /             │ 96-sensor nuclear SCADA │
│    Data 2022 Benchmark)  │ Nature Scientific Data      │ operational telemetry   │
└──────────────────────────┴─────────────────────────────┴─────────────────────────┘
```

### 2.1 Dataset Breakdown & Schemas

#### A. CIC-IDS2017 (`data/real/cicids2017_sample.csv`, 19.4 MB)
- **Source:** Canadian Institute for Cybersecurity (University of New Brunswick).
- **Scope:** 56,661 authentic network traffic flow records captured across realistic testbed networks.
- **Labels:** 
  - `BENIGN`: 22,731 legitimate flow conversations (HTTP, HTTPS, RPC, SMB, NTP).
  - `DoS`: 19,035 volumetric and protocol flood records (SYN flood, Slowloris, UDP flood).
  - `PortScan`: 7,946 reconnaissance sweeps across broad destination port spans.
  - `Bot`: 1,966 botnet command-and-control communication records.
  - `Infiltration`: 36 high-volume asymmetric data exfiltration and compromise records.
- **Key Flow Attributes Extracted:**
  - `Flow Duration`, `Total Fwd Packets`, `Total Backward Packets`
  - `Fwd Packet Length Mean`, `Fwd Packet Length Std`, `Fwd Packet Length Max`
  - `Flow IAT Mean`, `Flow IAT Std`, `Flow IAT Max`, `Flow IAT Min`
  - `Flow Bytes/s`, `Flow Packets/s`, `Down/Up Ratio`, `Average Packet Size`

#### B. Tranco Top-1M Scientific List (`data/real/tranco_top10k.csv`, 182.7 KB)
- **Source:** *Le Pochat, V. et al. "Tranco: A Research-Oriented Top Sites Ranking Hardened Against Manipulation", NDSS Symposium 2019* (`tranco-list.eu`).
- **Scope:** Scientific top 10,000 legitimate domain names aggregated via Borda/Dowdall voting across Google CrUX, Cloudflare Radar, Cisco Umbrella, Farsight, and Majestic.
- **Role in Pipeline:** Establishes the empirical benign distribution for DNS query string length, character frequency distributions, and n-gram surprisal to distinguish legitimate infrastructure lookups from algorithmic DGA or DNS tunneling.

#### C. abuse.ch Suricata JA3/JA4 Blacklist (`data/real/abuse_ch_ja3.csv`, 8.3 KB)
- **Source:** `https://sslbl.abuse.ch/blacklist/ja3_fingerprints.csv`
- **Scope:** Cryptographic hashes of TLS ClientHello parameter sets (ciphers, extensions, elliptic curves, ALPN) belonging to documented malware strains (Cobalt Strike Malleable C2, TrickBot, Emotet, QakBot, BazarLoader).
- **Role in Pipeline:** Allows the passive diode enclave to profile and categorize encrypted sessions from handshake metadata alone without requiring decryption.

#### D. abuse.ch Feodo Tracker Botnet C2 Blocklist (`data/real/feodo_c2_ips.csv`, 0.9 KB)
- **Source:** `https://feodotracker.abuse.ch/downloads/ipblocklist.csv`
- **Scope:** Active command-and-control server IP addresses and port telemetry tracked in the wild for banking trojans and botnets (Dridex, Emotet, QakBot).

#### E. NPPAD Nuclear Power Plant Accident Dataset (`data/nuclear/`, Nature Scientific Data 2022)
- **Source:** *Qi, B., Xiao, X., Liang, J. et al. "An open time-series simulated dataset covering various accidents for nuclear power plants." Nature Scientific Data 9, 766 (2022).*
- **Scope:** 96 physical reactor channels (Primary Coolant Pressure $P$, Core Average Temperature $T_{\text{AVG}}$, Reactor Coolant Flow Rate $W_{\text{RCA}}$, Steam Generator Pressure $P_{\text{SGA}}$, Thermal Power $Q_{\text{MWT}}$) sampled every 1.0 s.

---

## ⚙️ 3. Trace-Driven Simulation Methodology

The core NTRO requirement specifies:
> *"The AI should take from real datasets. Take a real dataset and simulate it to generate a dataset."*

Rather than generating naive random noise, CHRONOS implements a **trace-driven simulation engine** (`simulation/real_dataset_sim.py`). It ingests authentic flow records and real domain/fingerprint catalogs, and converts them into chronologically sequenced simplex IP packet streams:

$$\mathcal{S} = \{ \text{Packet}(t_i, \text{size}_i, \text{payload}_i, \text{direction}_i, \text{flow\_key}_i, \text{ja4}_i, \text{dns\_query}_i, \text{label}_i) \}_{i=1}^N$$

```text
┌──────────────────────────────────────────────────────────────────────────────────┐
│                      TRACE-DRIVEN DATASET SIMULATION ENGINE                      │
├──────────────────────────┬───────────────────────────────────────────────────────┤
│ Real Dataset Source      │ Trace-Driven Simulation Mechanism                     │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ CIC-IDS2017 BENIGN +     │ Empirical IAT distribution sampling, structured HTTP  │
│ Tranco Top-10k +         │ headers + authentic Tranco DNS query names +          │
│ NPPAD SCADA              │ genuine 96-sensor Modbus/TCP telemetry frames.        │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ CIC-IDS2017 DoS / DDoS   │ Reconstructs high packet rate streams (>300 pkts/s),  │
│ Flow Records             │ micro-bursts (IAT <= 5 ms), and spoofed-source        │
│                          │ IP entropy distributions: H(src_ip) > 4.5.           │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ CIC-IDS2017 Botnet +     │ Low coefficient of variation IAT (CV_iat < 0.1),      │
│ Feodo Tracker C2 IPs     │ periodic check-in cadence (T0 = 2.0s ± 50ms), and     │
│                          │ fixed session flow keys targeting active C2 IPs.      │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ Tranco Baseline vs       │ Injects algorithmic pseudo-random characters          │
│ DGArchive & dnscat2      │ (entropy > 4.2) and base64 data-bearing TXT/NULL      │
│                          │ record chunks exceeding 80 bytes in length.           │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ abuse.ch JA3/JA4         │ Injects authentic malware JA3 hashes, 512-byte TLS    │
│ Malware Blacklist        │ ApplicationData record framing, and pure cryptographic │
│                          │ payload entropy (Shannon entropy > 7.85 bits).        │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ CIC-IDS2017 PortScan     │ Single-packet SYN probes (44-64 bytes) fanning out   │
│ Sweeps                   │ across broad destination port spans (21, 22, 80, 443, │
│                          │ 502, 8080) targeting multiple internal IP hosts.      │
├──────────────────────────┼───────────────────────────────────────────────────────┤
│ CIC-IDS2017 Infiltration │ Continuous multi-packet bursts saturating MTU         │
│ / Exfiltration Flows     │ (1400-1460 bytes) with asymmetric outbound-to-        │
│                          │ inbound byte volume ratios: Bytes_out / Bytes_in > 50 │
└──────────────────────────┴───────────────────────────────────────────────────────┘
```

### 3.1 Mathematical Formulation of Threat Simulation

#### A. Volumetric & Protocol DDoS
Simulates high-speed SYN and UDP reflection floods using the empirical flow parameters from CIC-IDS2017:
$$\lambda_{\text{flood}} \sim \text{Uniform}(250, 600) \text{ pkts/s}, \quad \Delta t_i \sim \text{Exp}(\lambda_{\text{flood}}^{-1})$$
Source IP addresses are pseudo-randomly spoofed across class A/B subnets, causing the Shannon entropy of the source IP distribution over sliding window $W$ to spike:
$$H(S_{\text{ip}}) = -\sum_{s \in S} p(s) \log_2 p(s) > 4.5 \text{ bits}$$

#### B. Botnet C2 Beaconing
APT command-and-control implants establish outbound periodic check-in beacons with timing jitter $\delta$:
$$t_k = t_{k-1} + T_0 + \epsilon_k, \quad \epsilon_k \sim \mathcal{N}(0, \sigma_{\delta}^2), \quad \sigma_{\delta} \ll T_0$$
The inter-arrival coefficient of variation $CV_{\text{iat}} = \frac{\sigma_{\text{iat}}}{\mu_{\text{iat}}} < 0.15$ indicates near-deterministic periodicity. Target destinations are drawn from active Feodo Tracker C2 blocklist IPs.

#### C. DGA Domains & DNS Tunnelling
Compares authentic Tranco domain character sequences against pseudo-random algorithmic generators:
$$\text{CharEntropy}(Q) = -\sum_{c \in \Sigma} p(c) \log_2 p(c)$$
While authentic Tranco domains (`google.com`, `cloudflare.com`, `ntro.gov.in`) yield $\text{CharEntropy} \in [2.2, 3.4]$, DGA domains and dnscat2 base64 tunnels exhibit $\text{CharEntropy} \in [4.2, 5.8]$ and query lengths $|Q| \in [65, 180]$ characters.

#### D. Malware in Encrypted Sessions
Adversary traffic over TLS 1.3 / QUIC is modeled without payload decryption by assigning authentic abuse.ch JA3/JA4 fingerprint hashes (`6734f374...` Cobalt Strike, `51c64c...` TrickBot) and structuring uniform random ciphertexts:
$$H(\text{payload}) = -\sum_{b=0}^{255} p(b) \log_2 p(b) \ge 7.85 \text{ bits}$$

#### E. Reconnaissance & Port Scanning
Models rapid single-source fan-out scans across multiple destination ports and IPs:
$$\text{FanOut}(s) = |\{ (d_{\text{ip}}, d_{\text{port}}) : \text{flow}(s \to d) \in W \}| > 25, \quad \text{size}_i \le 64 \text{ bytes}$$

#### F. Data Exfiltration
Simulates asymmetric bulk data egress through the unidirectional tap:
$$\mathcal{R}_{\text{byte}} = \frac{\sum \text{Bytes}_{\text{out}}}{\max(1, \sum \text{Bytes}_{\text{in}})} > 20.0, \quad \text{size}_i \ge 1380 \text{ bytes}$$

### 3.2 Standardized Simulated Dataset Artifact (`data/real_traffic_stream.jsonl`)
Executing `python simulation/real_dataset_sim.py` generates the standardized JSON Lines stream:
```json
{"t": 0.045120, "size": 64, "direction": 0, "entropy": 1.7695, "flow_key": "10.0.1.10:502->10.0.1.50:502", "ja4": "", "dns_query": "", "label": "BENIGN"}
{"t": 120.10420, "size": 64, "direction": 1, "entropy": 0.0000, "flow_key": "185.220.101.5:41234->192.168.1.100:80", "ja4": "", "dns_query": "", "label": "ddos_flood"}
{"t": 140.05120, "size": 160, "direction": 0, "entropy": 7.4215, "flow_key": "192.168.1.45:49812->185.180.198.45:443", "ja4": "t13d1516h2_8daaf6152771_0", "dns_query": "", "label": "c2_beacon"}
{"t": 160.01250, "size": 112, "direction": 0, "entropy": 4.8120, "flow_key": "192.168.1.55:53->8.8.8.8:53", "ja4": "", "dns_query": "48f9a2b1c0d4e5f6.exfil-tunnel.sec.net", "label": "dga_tunnel"}
```

---

## 🧠 4. Complete AI Model Architecture Deep-Dive

```text
                               ┌─ ZERO-COPY INGESTION LAYER ─┐
                               │ AF_XDP / DPDK Ring Buffer   │
                               │ Passive Diode Optical Tap   │
                               └──────────────┬──────────────┘
                                              │ Raw Packets
                                              ▼
                               ┌─ SIGNAL TRANSFORM LAYER ────┐
                               │ [iat, bytes, entropy,       │
                               │  burst, direction]          │
                               └──────────────┬──────────────┘
                                              │ Feature Vectors
                                              ▼
                               ┌─ UNIFIED WINDOW CONTRACT ───┐
                               │ aggregate_slots (dt=0.01)   │
                               │ Train/Serve Skew = 0        │
                               └──────────────┬──────────────┘
                                              │ (values, mask, t_grid)
                                              ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│                    CONTINUOUS-TIME NEURAL JUMP-ODE CORE (Herrera et al. 2021)                │
│                                                                                              │
│   dh(t)/dt = f_θ(h(t), x_last, t_last, dt)  ───► Euler Continuous Trajectory                │
│   h(t_i)   = jumpNN_θ(x_i)                  ───► Discrete Stochastic Jump                   │
│   y^-(t_i) = outputNN_θ(h(t_i^-))           ───► Online Expectation of Normal Network Path  │
│                                                                                              │
│   Prediction Residual: S_i = ||x_i - y^-(t_i)||_2^2                                          │
│   Dynamic Peak Metric: S_peak = max_j S_j                                                    │
└─────────────────────────────────────────────┬────────────────────────────────────────────────┘
                                              │ S_peak vs τ
                                              ▼
                               ┌─ DECISION & ATTRIBUTION ────┐
                               │ S_peak > τ                  │
                               │ N-of-M Hysteresis Filter    │
                               │ Channel Attribution (Bayes) │
                               └──────────────┬──────────────┘
                                              │ Labelled Intelligence
                                              ▼
                               ┌─ SOC DASHBOARD & ALERTS ────┐
                               │ Standardized CEF/STIX Alert │
                               │ Calibrated Confidence Score │
                               │ Explainable Forensic Bundle │
                               └─────────────────────────────┘
```

### 4.1 Neural Jump Ordinary Differential Equations (NJ-ODE)

The anomaly detection core of CHRONOS is built on **Neural Jump Ordinary Differential Equations** (*Herrera, Krach & Teichmann, ICLR 2021, arXiv:2006.04727*).

#### Why NJ-ODE is Uniquely Suited for Data Diodes:
Traditional recurrent architectures (RNN, LSTM, GRU) assume fixed, equidistant observation timesteps (e.g. 1 s or 5 min batches). However:
1. **Network traffic arrives at irregular intervals:** Inter-packet times vary across microseconds to seconds.
2. **Data diodes drop frames under optical noise:** Missing observations produce non-uniform gaps.
Rather than requiring artificial interpolation or forward-filling, NJ-ODE models network dynamics as a **continuous latent state trajectory** $\mathbf{h}(t) \in \mathbb{R}^{d_h}$ governed by an ODE, interrupted by **instantaneous discrete stochastic jumps** upon packet arrival.

#### Mathematical Formulation:
Between packet arrival times $t \in [t_{i-1}, t_i)$, the latent state flows continuously according to the neural vector field $f_\theta$:
$$\frac{d\mathbf{h}(t)}{dt} = f_\theta(\mathbf{h}(t), \mathbf{x}_{\text{last}}, t_{\text{last}}, t - t_{\text{last}})$$
Where $f_\theta$ is parameterized by a residual multi-layer perceptron (ResidualMLP) with bounded $\tanh$ activations.

Upon observation of a packet feature vector $\mathbf{x}_i \in \mathbb{R}^{d_x}$ at timestamp $t_i$:
1. **Prior Online Expectation:** The output network predicts the expected benign state immediately before the jump:
   $$\mathbf{y}^-(t_i) = \text{outputNN}_\theta(\mathbf{h}(t_i^-))$$
2. **Stochastic Jump:** The latent state jumps to incorporate the new observation:
   $$\mathbf{h}(t_i) = \text{jumpNN}_\theta(\mathbf{x}_i)$$
3. **Posterior Projection:**
   $$\mathbf{y}(t_i) = \text{outputNN}_\theta(\mathbf{h}(t_i))$$

#### Training Objective (Herrera et al., Eq. 33):
The model is trained entirely **unsupervised / semi-supervised on benign baseline traffic** using Adam ($\text{lr}=10^{-3}, \text{weight\_decay}=5\times 10^{-4}$):
$$\Phi(\theta) = \frac{1}{N} \sum_{\text{paths}} \frac{1}{n_j} \sum_{i=1}^{n_j} \left( \|\mathbf{x}_i - \mathbf{y}_i\|_2 + \|\mathbf{y}_i - \mathbf{y}_i^-\|_2 \right)^2$$

#### Dynamic Window-Peak Anomaly Metric:
$$\mathcal{S}_{\text{peak}} = \max_{j=1}^{K} \|\mathbf{x}_j - \mathbf{y}^-_j\|_2^2 > \tau$$
When traffic conforms to benign dynamics, the one-step prediction error $\|\mathbf{x}_j - \mathbf{y}^-_j\|_2^2 \approx 0$. When an attack or covert channel is injected, the observations violently violate the learned expectation, causing $\mathcal{S}_{\text{peak}}$ to spike past calibrated threshold $\tau$.

---

### 4.2 Dual-Model Semi-Supervised Anomaly Core ($L_{\text{semi}}$)

Complementing NJ-ODE's temporal dynamics, CHRONOS incorporates a **Deep Autoencoder Latent Manifold Envelope** (Slide 4):

$$\mathcal{L}_{\text{semi}} = \sum_{i=1}^n \|\mathbf{x}_i - g_\theta(f_\phi(\mathbf{x}_i))\|_2^2 + \lambda \cdot \Omega(\mathbf{W})$$

Where:
- $\mathbf{z}_i = f_\phi(\mathbf{x}_i)$ represents the compressed latent bottleneck.
- $\hat{\mathbf{x}}_i = g_\theta(\mathbf{z}_i)$ represents the reconstructed flow feature vector.
- $\Omega(\mathbf{W}) = \|\mathbf{W}\|_F^2$ is the Frobenius regularization penalty preventing overfitting to transient packet noise.
- A One-Class latent boundary envelope establishes an outer convex hull around benign network behaviors. Unseen zero-day exploits outside this manifold immediately trigger high-confidence anomaly flags.

---

### 4.3 Zero Train/Serve Skew Windowing Contract

To ensure mathematical parity between offline batch training (`Windower`) and live streaming diode ingest (`LiveFeeder`), all aggregation passes through the shared function `aggregate_slots(...)`:

$$\text{Collision Policy per Slot } j \in [0, K]:$$
- **Inter-Arrival Time (`iat`):** $\min_{i \in \text{slot}_j} (\text{iat}_i)$ — captures the tightest inter-arrival burst.
- **Wire Volume (`bytes`):** $\sum_{i \in \text{slot}_j} (\text{size}_i)$ — captures cumulative byte volume.
- **Shannon Entropy (`entropy`):** $\max_{i \in \text{slot}_j} (\text{entropy}_i)$ — records maximum information surprise.
- **Burst Indicator (`burst`):** $\max_{i \in \text{slot}_j} (\text{burst}_i)$ — micro-burst active flag ($\text{iat} \le 20\text{ ms}$).
- **Direction (`direction`):** $\text{majority}_{i \in \text{slot}_j} (\text{direction}_i)$ — inbound dominant indicator.

#### Slotted Standardization (Guaranteed Unit Variance):
To prevent multi-packet byte summing from causing numerical clipping, the feature standardizer is fitted directly over slotted observations:
$$\mathbf{x}_{\text{std}} = \text{clip}\left( \frac{\mathbf{x}_{\text{slot}} - \hat{\boldsymbol{\mu}}_{\text{slot}}}{\hat{\boldsymbol{\sigma}}_{\text{slot}}}, -30.0, 30.0 \right)$$
The scaler buffers $(\hat{\boldsymbol{\mu}}, \hat{\boldsymbol{\sigma}})$ and threshold $\tau$ are persisted directly inside the versioned model checkpoint (`checkpoints/njode_telemetry.pt`), eliminating preprocessing drift.

---

### 4.4 Multi-Threat Channel Attribution & Calibrated Confidence

#### Unsupervised Channel Residual Mapping:
Because the enclave cannot query external threat intelligence servers across the diode, CHRONOS attributes threats by isolating the feature channel with the largest squared prediction residual:
$$k^* = \arg\max_{k \in \{ \text{iat}, \text{bytes}, \text{entropy}, \text{burst}, \text{direction} \}} \sum_{j \in \text{anom}} (x_{j,k} - y_{j,k}^-)^2$$

Combined with window evidence metrics (distinct flow count, flow entropy, outbound/inbound byte ratio), CHRONOS deterministically maps deviations to the 6 target threat classes:

```text
┌──────────────────────────┬────────────────────────────────────────────────────────┐
│ Threat Category          │ Decision Logic & Forensic Evidence Signature           │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ a. Volumetric /          │ Top channel = 'direction' OR (Inbound > Outbound * 1.5 │
│    Protocol DDoS         │ and Distinct Flows > 20). High source IP entropy.      │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ b. Botnet C2 Beaconing   │ Top channel = 'iat' with low packet volume, or fixed   │
│                          │ 1.5–2.0s cadence toward small set of destination IPs.  │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ c. DGA Domains &         │ Top channel = 'entropy' with query length > 35 chars   │
│    DNS Tunnelling        │ and mean DNS character entropy > 3.8 bits.             │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ d. Encrypted Malware     │ Fixed frame sizes (e.g. 512B), ciphertext entropy      │
│    (TLS/QUIC)            │ > 7.5 bits, matching abuse.ch JA3/JA4 fingerprint.     │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ e. Reconnaissance &      │ Distinct Flows > 20 with average packet size < 100B    │
│    Port Scanning         │ fanning out across multiple destination ports/hosts.   │
├──────────────────────────┼────────────────────────────────────────────────────────┤
│ f. Data Exfiltration     │ Top channel in ('bytes', 'burst') with Outbound /      │
│                          │ Inbound Byte Ratio > 20.0 and packet sizes >= 1380B.   │
└──────────────────────────┴────────────────────────────────────────────────────────┘
```

#### Empirical Quantile Confidence Calibration:
Confidence score $\mathcal{C} \in [0.0, 1.0]$ is computed monotonically against empirical benign calibration quantiles $[q_{50}, q_{90}, q_{99}, q_{99.9}]$:
$$\mathcal{C}(\mathcal{S}_{\text{peak}}) = 
\begin{cases} 
0.10 \cdot \frac{\mathcal{S}_{\text{peak}}}{q_{50}} & \text{if } \mathcal{S}_{\text{peak}} \le q_{50} \\
0.10 + 0.50 \cdot \frac{\mathcal{S}_{\text{peak}} - q_{50}}{q_{90} - q_{50}} & \text{if } q_{50} < \mathcal{S}_{\text{peak}} \le q_{90} \\
0.60 + 0.30 \cdot \frac{\mathcal{S}_{\text{peak}} - q_{90}}{q_{99} - q_{90}} & \text{if } q_{90} < \mathcal{S}_{\text{peak}} \le q_{99} \\
0.90 + 0.08 \cdot \frac{\mathcal{S}_{\text{peak}} - q_{99}}{q_{99.9} - q_{99}} & \text{if } q_{99} < \mathcal{S}_{\text{peak}} \le q_{99.9} \\
\min\left(1.0, 0.98 + 0.02 \left(1 - e^{-0.5 \frac{\mathcal{S}_{\text{peak}} - q_{99.9}}{q_{99.9}}}\right)\right) & \text{if } \mathcal{S}_{\text{peak}} > q_{99.9}
\end{cases}$$

---

## 📊 5. Empirical Evaluation Results & Benchmarks

### 5.1 Multi-Regime Attack Detection Performance (`results/eval.json`)
Evaluated across 40 independent evaluation windows per threat category on the multi-regime benign baseline:

```text
========================================================================================
CHRONOS MULTI-REGIME DETECTION & ATTRIBUTION MATRIX (τ = 5.80)
========================================================================================
Threat Category          | Detection Rate | Flagged Obs % | Mean Peak S | Attribution %
-------------------------+----------------+---------------+-------------+---------------
a. Volumetric DDoS       |     100.0%     |     99.8%     |    804.8    |    100.0%
b. Botnet C2 Beaconing   |     100.0%     |     37.2%     |     26.3    |     90.0%
c. DGA & DNS Tunnelling  |     100.0%     |     97.4%     |     74.1    |     95.0%
d. Encrypted TLS Malware |     100.0%     |     52.9%     |    142.4    |    100.0%
e. Recon / Port Scan     |     100.0%     |     99.5%     |    131.1    |    100.0%
f. Data Exfiltration     |     100.0%     |    100.0%     |    944.0    |    100.0%
-------------------------+----------------+---------------+-------------+---------------
Benign Baseline FPR      |       0.0%     |  (Peak S: Mean = 1.87, p99 = 5.65)
========================================================================================
```

### 5.2 Throughput & Latency Benchmark (`results/benchmark.json`)
Evaluated across escalating traffic ingestion rates on a standard commodity Linux system:

```text
========================================================================================
CHRONOS HIGH-SPEED INGESTION THROUGHPUT & LATENCY BENCHMARK
========================================================================================
Target Rate  | Measured Ingest Rate | Window Scoring p50 | Window Scoring p99 | Status
-------------+----------------------+--------------------+--------------------+---------
 100 pkts/s  |     100.2 pkts/s     |      0.082 ms      |      0.245 ms      | PASS
 500 pkts/s  |     499.8 pkts/s     |      0.084 ms      |      0.251 ms      | PASS
1000 pkts/s  |     998.4 pkts/s     |      0.087 ms      |      0.264 ms      | PASS
2000 pkts/s  |    1995.1 pkts/s     |      0.091 ms      |      0.278 ms      | PASS
3000 pkts/s  |    2989.5 pkts/s     |      0.096 ms      |      0.292 ms      | PASS
5000 pkts/s  |    4978.2 pkts/s     |      0.104 ms      |      0.315 ms      | PASS
========================================================================================
Maximum Sustained Ingestion Rate : > 5,000 packets/second (equivalent to line-rate flows)
Window Scoring Latency           : Sub-millisecond (p50 = 0.08 ms, p99 = 0.31 ms)
========================================================================================
```

---

## 🛡️ 6. Compliance with NTRO Architectural Constraints

| Constraint | Architectural Requirement | How CHRONOS Satisfies the Constraint |
|---|---|---|
| **a. Read-Only Ingest** | Strictly read-only input. No return path, live probe, or inline block. | CHRONOS operates strictly on the receive side of a hardware optical data diode / zero-copy ring buffer tap. The network interface has no transmit pin (`TX`), physically and mathematically preventing any transmission back into the monitored network. |
| **b. No Payload Decryption** | TLS/QUIC sessions analyzed from metadata only, never decrypted. | All TLS/QUIC features are derived from unencrypted packet headers, wire sizes, inter-arrival timing sequences (SPLT), and ClientHello JA4/JA3 metadata hashes. Payloads remain fully encrypted. |
| **c. Streaming, Not Batch** | Process traffic incrementally and raise alerts with bounded latency. | The `LiveFeeder` operates an online sliding window (10.0 s width, 2.0 s stride) through continuous ODE state updates. Window evaluation executes in $< 0.35\text{ ms}$, ensuring near real-time SOC alerting. |
| **d. Defined Throughput Target** | State and demonstrate sustained traffic rate (flows/s or Mbps). | Rigorously benchmarked via `benchmark.py` up to **5,000 pkts/s sustained** with sub-millisecond scoring execution (p50 = 0.08 ms, p99 = 0.31 ms) with bounded memory consumption. |
| **e. Standardized Alert Schema** | Structured records: timestamp, flow identifier, threat class, confidence, evidence. | Emits standardized CEF and JSON structured alert records adhering to standard SIEM / STIX formats containing full explainable evidence packages. |

---

## 📜 7. Standardized Alert Schema Specification

Every anomaly emitted by CHRONOS conforms to the structured JSON/CEF specification:

```json
{
  "timestamp": "2026-09-12T15:55:00.124Z",
  "window_t0": 120.0,
  "window_t1": 130.0,
  "peak_score": 944.02,
  "threshold": 5.80,
  "is_anomaly": true,
  "confirmed": true,
  "confidence": 0.9998,
  "severity": "CRITICAL",
  "threat_class": "exfil_burst",
  "flow_ids": [19823, 4421, 1029],
  "attribution": {
    "top_channel": "bytes",
    "threat_type": "exfil_burst",
    "channel_errors": {
      "iat": 4.12,
      "bytes": 894.21,
      "entropy": 3.44,
      "burst": 42.10,
      "direction": 0.15
    }
  },
  "evidence": {
    "distinct_flows": 1,
    "flow_entropy": 0.0,
    "outbound_inbound_byte_ratio": 98.45,
    "outbound_bytes": 142000,
    "inbound_bytes": 1440,
    "packet_count": 102
  }
}
```

---

## 📚 8. References & Scientific Citations

1. **Neural Jump Ordinary Differential Equations (NJ-ODE):**  
   Herrera, C., Krach, F., & Teichmann, J. (2021). *Neural Jump Ordinary Differential Equations: Consistent Continuous-Time Prediction and Filtering*. International Conference on Learning Representations (ICLR 2021). [arXiv:2006.04727](https://arxiv.org/abs/2006.04727).
2. **CIC-IDS2017 Benchmark Dataset:**  
   Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). *Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization*. ICISSP 2018. Canadian Institute for Cybersecurity.
3. **Tranco Scientific Top-1M Ranking:**  
   Le Pochat, V., Van Goethem, T., Tajalizadekamin, S., & Joosen, W. (2019). *Tranco: A Research-Oriented Top Sites Ranking Hardened Against Manipulation*. In Proceedings of the 26th Annual Network and Distributed System Security Symposium (NDSS 2019). [tranco-list.eu](https://tranco-list.eu/).
4. **JA4+ Network Fingerprinting:**  
   Althouse, J. (2023). *JA4+ Network Fingerprinting Open Security Standard*. FoxIO Open Standard. [github.com/FoxIO-LLC/ja4](https://github.com/FoxIO-LLC/ja4).
5. **Nuclear Power Plant Accident Dataset (NPPAD):**  
   Qi, B., Xiao, X., Liang, J. et al. (2022). *An open time-series simulated dataset covering various accidents for nuclear power plants*. Nature Scientific Data 9, 766. [doi:10.1038/s41597-022-01878-3](https://doi.org/10.1038/s41597-022-01878-3).
6. **Lomb-Scargle Periodograms for Irregular Jitter:**  
   VanderPlas, J. T. (2018). *Understanding the Lomb-Scargle Periodogram*. The Astrophysical Journal Supplement Series, 236(1), 16. [doi:10.3847/1538-4365/aab766](https://doi.org/10.3847/1538-4365/aab766).
7. **Wavelet Scattering Transforms for Burst Dynamics:**  
   Bruna, J., & Mallat, S. (2013). *Invariant Scattering Convolution Networks*. IEEE Transactions on Pattern Analysis and Machine Intelligence, 35(8), 1872-1886. [doi:10.1109/TPAMI.2012.230](https://doi.org/10.1109/TPAMI.2012.230).
8. **Directed Transfer Entropy for Covert Exfiltration:**  
   Schreiber, T. (2000). *Measuring Information Transfer*. Physical Review Letters, 85(2), 461. [doi:10.1103/PhysRevLett.85.461](https://doi.org/10.1103/PhysRevLett.85.461).
