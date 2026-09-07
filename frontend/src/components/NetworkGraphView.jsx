import React, { useEffect, useRef, useState, useMemo } from 'react';
import { 
  ShieldAlert, 
  ShieldCheck, 
  AlertTriangle, 
  Radio, 
  Database, 
  Cpu, 
  Server, 
  Lock, 
  Zap, 
  FileText, 
  X, 
  ZoomIn, 
  ZoomOut, 
  RotateCcw, 
  Info,
  Activity,
  Layers
} from 'lucide-react';

// Node definitions reflecting the actual physical air-gap network
const INITIAL_NODES = [
  // Zone A: Air-Gapped High Security In-Zone (Left)
  {
    id: 'plc-01',
    label: 'SCADA PLC-01',
    sublabel: 'Turbine Governor',
    ip: '10.0.1.10',
    zone: 'in-zone',
    x: 140,
    y: 140,
    vx: 0,
    vy: 0,
    radius: 18,
    type: 'controller',
    normalRate: '4 pkts/s',
  },
  {
    id: 'plc-02',
    label: 'SCADA PLC-02',
    sublabel: 'Cooling Loop',
    ip: '10.0.1.11',
    zone: 'in-zone',
    x: 140,
    y: 260,
    vx: 0,
    vy: 0,
    radius: 18,
    type: 'controller',
    normalRate: '3 pkts/s',
  },
  {
    id: 'ews-alpha',
    label: 'Workstation Alpha',
    sublabel: 'Engineering Terminal',
    ip: '10.0.1.25',
    zone: 'in-zone',
    x: 270,
    y: 140,
    vx: 0,
    vy: 0,
    radius: 20,
    type: 'workstation',
    normalRate: '12 pkts/s',
  },
  {
    id: 'db-historian',
    label: 'Process Historian',
    sublabel: 'SCADA Telemetry DB',
    ip: '10.0.1.50',
    zone: 'in-zone',
    x: 270,
    y: 260,
    vx: 0,
    vy: 0,
    radius: 19,
    type: 'database',
    normalRate: '8 pkts/s',
  },
  {
    id: 'tx-diode',
    label: 'In-Zone TX Diode',
    sublabel: 'Simplex Laser Emitter',
    ip: '10.0.1.1',
    zone: 'diode-tx',
    x: 410,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 22,
    type: 'transmitter',
    normalRate: '18 pkts/s',
  },

  // Optical Air-Gap Barrier (Center)
  {
    id: 'optical-gap',
    label: 'Optical Air-Gap Isolator',
    sublabel: '100% Galvanic Simplex',
    ip: 'PHYSICAL GAP',
    zone: 'barrier',
    x: 540,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 15,
    type: 'barrier',
    normalRate: 'Simplex Fiber',
  },

  // Zone B: Monitored Scanner Side / SOC Subnet (Right)
  {
    id: 'rx-diode',
    label: 'Scanner RX Diode',
    sublabel: 'Photodiode Detector',
    ip: '192.168.10.1',
    zone: 'diode-rx',
    x: 670,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 22,
    type: 'receiver',
    normalRate: '18 pkts/s',
  },
  {
    id: 'njode-core',
    label: 'CHRONOS NJ-ODE',
    sublabel: 'Continuous Latent Engine',
    ip: '192.168.10.5',
    zone: 'scanner',
    x: 810,
    y: 140,
    vx: 0,
    vy: 0,
    radius: 24,
    type: 'ai-core',
    normalRate: 'Inference 1.1ms',
  },
  {
    id: 'sync-srv',
    label: 'Web Sync Gateway',
    sublabel: 'NTP & Benign Sync',
    ip: '192.168.10.15',
    zone: 'scanner',
    x: 810,
    y: 260,
    vx: 0,
    vy: 0,
    radius: 18,
    type: 'server',
    normalRate: '0.15 pkts/s',
  },
  {
    id: 'soc-siem',
    label: 'SOC Alert Sink',
    sublabel: 'Incident Dispatcher',
    ip: '192.168.10.100',
    zone: 'scanner',
    x: 940,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 20,
    type: 'siem',
    normalRate: 'Active Polling',
  },
];

const INITIAL_EDGES = [
  { from: 'plc-01', to: 'tx-diode' },
  { from: 'plc-02', to: 'tx-diode' },
  { from: 'ews-alpha', to: 'tx-diode' },
  { from: 'db-historian', to: 'tx-diode' },
  { from: 'ews-alpha', to: 'db-historian' },
  { from: 'plc-01', to: 'plc-02' },
  // Simplex optical bridge
  { from: 'tx-diode', to: 'optical-gap', isDiodeBridge: true },
  { from: 'optical-gap', to: 'rx-diode', isDiodeBridge: true },
  // Scanner side
  { from: 'rx-diode', to: 'njode-core' },
  { from: 'rx-diode', to: 'sync-srv' },
  { from: 'njode-core', to: 'soc-siem' },
  { from: 'sync-srv', to: 'soc-siem' },
];

export default function NetworkGraphView({ 
  currentScenario = 'calm', 
  score = 0.48, 
  tau = 2.81,
  packetEvent = null,
  isStreaming = true,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Nodes state with physics coordinates
  const [nodes, setNodes] = useState(INITIAL_NODES);
  const [edges] = useState(INITIAL_EDGES);

  // Active flying real packets (ONLY populated when real packets flow between systems)
  const activeParticlesRef = useRef([]);
  const lastPacketRef = useRef(null);
  const [inFlightCount, setInFlightCount] = useState(0);

  // Mouse interaction state
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [draggedNode, setDraggedNode] = useState(null);

  // Transform: pan & zoom
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const isPanningRef = useRef(false);
  const panStartRef = useRef({ x: 0, y: 0 });

  // Map malware info dynamically based on current scenario
  const getMalwareStatus = (nodeId) => {
    if (currentScenario === 'ddos_flood') {
      if (nodeId === 'plc-02') {
        return {
          isInfected: true,
          severity: 'CRITICAL',
          color: '#f43f5e',
          name: 'Target.CoolingLoop.DDoSInundation',
          description: 'Cooling loop controller under high-rate reflection SYN/UDP volumetric flood (200 pkts/s, tiny 64B frames).',
          rate: '200.0 pkts/s (INBOUND)',
          dominantChannel: 'direction (inbound) / burst',
          peakScore: score.toFixed(1),
          cve: 'CWE-400 / SYN-UDP-Flood',
          traces: [
            'T-0.3s | 198.51.100.42:53211 → 10.0.1.11:80 | TCP SYN | 64 B | H=2.10 bits | 🚨 INBOUND FLOOD (flow 0xA11F)',
            'T-0.2s | 203.0.113.88:41904 → 10.0.1.11:80  | TCP SYN | 64 B | H=2.08 bits | 🚨 SPOOFED SOURCE (flow 0xB472)',
            'T-0.1s | 192.0.2.14:62890 → 10.0.1.11:80    | TCP SYN | 64 B | H=2.12 bits | 🚨 VOLUMETRIC SURGE (flow 0xC931)',
          ]
        };
      }
      if (nodeId === 'rx-diode' || nodeId === 'tx-diode') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'CRITICAL',
          color: '#f43f5e',
          name: 'Optical Receiver Saturated',
          description: 'Simplex channel inundated with inbound traffic (direction=1, 200 pkts/s). Multiple spoofed flow hashes detected.',
          rate: '200.0 pkts/s',
          dominantChannel: 'direction (inbound)',
          peakScore: score.toFixed(1),
        };
      }
      if (nodeId === 'njode-core') {
        return {
          isInfected: false,
          isTriggered: true,
          severity: 'ALERT',
          color: '#f43f5e',
          name: 'Volumetric DDoS Anomaly Confirmed',
          description: 'Continuous latent space breach: S = ' + score.toFixed(1) + ' > τ = 2.81. Attributed to direction (inbound) and burst.',
        };
      }
    } else if (currentScenario === 'tls_c2') {
      if (nodeId === 'ews-alpha') {
        return {
          isInfected: true,
          severity: 'HIGH',
          color: '#8b5cf6',
          name: 'Malware.EncryptedTLS.Ghost',
          description: 'Engineering terminal running covert TLS C2 session. Ciphertext entropy ~7.9 bits is indistinguishable from benign TLS; detected passively via timing regularity (T0 ± δ) and fixed 512B frames without payload decryption.',
          rate: 'Periodic Cadence (1.8s)',
          dominantChannel: 'iat (metadata-only)',
          peakScore: score.toFixed(1),
          cve: 'CVE-2026-9211',
          traces: [
            'T-0.4s | 10.0.1.25:49812 → 192.168.10.1:443 | TLSv1.3 | 512 B | H=7.91 bits | 🚨 METADATA REGULARITY (iat=1.80s)',
            'T-0.2s | 10.0.1.25:49812 → 192.168.10.1:443 | TLSv1.3 | 512 B | H=7.89 bits | 🚨 RIGID FRAME CADENCE (T0±δ)',
            'T-0.0s | 10.0.1.25:49812 → 192.168.10.1:443 | TLSv1.3 | 512 B | H=7.92 bits | 🚨 PASSIVE TIMING BREACH',
          ]
        };
      }
      if (nodeId === 'tx-diode' || nodeId === 'rx-diode' || nodeId === 'njode-core') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'ALERT',
          color: '#8b5cf6',
          name: 'Encrypted Channel Timing Anomaly',
          description: 'Non-benign inter-arrival distribution detected across TLS flows without decryption.',
          peakScore: score.toFixed(1),
        };
      }
    } else if (currentScenario === 'portscan') {
      if (nodeId === 'ews-alpha') {
        return {
          isInfected: true,
          severity: 'HIGH',
          color: '#3b82f6',
          name: 'Recon.HorizontalPortScan.FanOut',
          description: 'Compromised workstation performing horizontal port sweep across 128+ destination ports. Burst of small 44-60B probe frames, single source origin, high distinct flow entropy.',
          rate: 'Rapid Probe Burst (44B)',
          dominantChannel: 'burst / bytes',
          peakScore: score.toFixed(1),
          cve: 'CWE-200 / Network-Recon',
          traces: [
            'T-0.3s | 10.0.1.25:54321 → 10.0.1.10:445  | TCP SYN | 44 B | H=1.85 bits | 🚨 FAN-OUT PORT PROBE (flow 0x8F1A)',
            'T-0.2s | 10.0.1.25:54321 → 10.0.1.11:502  | TCP SYN | 44 B | H=1.84 bits | 🚨 FAN-OUT PORT PROBE (flow 0x8F1B)',
            'T-0.1s | 10.0.1.25:54321 → 10.0.1.50:4840 | TCP SYN | 44 B | H=1.87 bits | 🚨 RECON SWEEP SURGE (flow 0x8F1C)',
          ]
        };
      }
      if (nodeId === 'plc-01' || nodeId === 'plc-02' || nodeId === 'db-historian') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'SUSPECTED',
          color: '#60a5fa',
          name: 'Probed Controller Target',
          description: 'Targeted by horizontal reconnaissance port sweep from Workstation Alpha.',
          rate: 'Probe Target',
          dominantChannel: 'burst',
          peakScore: score.toFixed(1),
        };
      }
      if (nodeId === 'tx-diode' || nodeId === 'rx-diode' || nodeId === 'njode-core') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'ALERT',
          color: '#3b82f6',
          name: 'Multi-Flow Reconnaissance Fan-Out',
          description: 'Abnormal spike in distinct flow identifiers and tiny probe datagrams traversing the diode.',
          peakScore: score.toFixed(1),
        };
      }
    } else if (currentScenario === 'exfil_burst') {
      if (nodeId === 'ews-alpha') {
        return {
          isInfected: true,
          severity: 'CRITICAL',
          color: '#ef4444',
          name: 'Trojan.Exfil.LethalFlood',
          description: 'Compromised engineering workstation actively flooding large 1400B exfil datagrams towards the simplex diode.',
          rate: '66.7 pkts/s (BURST)',
          dominantChannel: 'bytes (100%)',
          peakScore: score.toFixed(1),
          cve: 'CVE-2026-8803',
          traces: [
            'T-0.3s | 10.0.1.25:9999 → 10.0.1.1:9999 | UDP | 1400 B | H=7.82 bits | 🚨 ASYMMETRIC OUTBOUND BURST (flow 0xEE41)',
            'T-0.2s | 10.0.1.25:9999 → 10.0.1.1:9999 | UDP | 1400 B | H=7.85 bits | 🚨 BULK EXFIL DETECTED (flow 0xEE41)',
            'T-0.1s | 10.0.1.25:9999 → 10.0.1.1:9999 | UDP | 1400 B | H=7.84 bits | 🚨 SKEWED BYTE RATIO (flow 0xEE41)',
          ]
        };
      }
      if (nodeId === 'tx-diode' || nodeId === 'rx-diode') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'ALERT',
          color: '#f97316',
          name: 'Diode Ingestion Anomaly Detected',
          description: 'High byte volume burst traversing simplex link. Photodiode detector forwarding to NJ-ODE core.',
          rate: '66.7 pkts/s',
          dominantChannel: 'bytes',
          peakScore: score.toFixed(1),
        };
      }
      if (nodeId === 'njode-core') {
        return {
          isInfected: false,
          isTriggered: true,
          severity: 'ALERT',
          color: '#ef4444',
          name: 'Hysteresis Confirmed Alert (2/2)',
          description: 'Continuous latent space breach: S = ' + score.toFixed(1) + ' > τ = 2.81. Attributed to bytes.',
        };
      }
    } else if (currentScenario === 'c2_beacon') {
      if (nodeId === 'plc-01') {
        return {
          isInfected: true,
          severity: 'HIGH',
          color: '#a855f7',
          name: 'Backdoor.CobaltC2.Jitter',
          description: 'Compromised PLC governor sending periodic high-entropy command-and-control heartbeats at 2.5s intervals.',
          rate: 'Periodic (2.5s jittered)',
          dominantChannel: 'entropy / iat',
          peakScore: score.toFixed(1),
          cve: 'CVE-2026-1640',
          traces: [
            'T-0.3s | 10.0.1.10:4840 → 198.51.100.99:8443 | TCP | 256 B | H=6.85 bits | 🚨 CADENCE BEACON (T0=2.5s, flow 0x7C11)',
            'T-0.2s | 10.0.1.10:4840 → 198.51.100.99:8443 | TCP | 256 B | H=6.88 bits | 🚨 PERIODIC C2 HEARTBEAT (flow 0x7C11)',
            'T-0.1s | 10.0.1.10:4840 → 198.51.100.99:8443 | TCP | 256 B | H=6.82 bits | 🚨 NON-BENIGN IAT PEAK',
          ]
        };
      }
      if (nodeId === 'tx-diode' || nodeId === 'rx-diode' || nodeId === 'njode-core') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'SUSPECTED',
          color: '#c084fc',
          name: 'Periodic Entropy Breach',
          description: 'Strict periodicity detected in irregular packet gaps. Attributed to timing/entropy.',
          peakScore: score.toFixed(1),
        };
      }
    } else if (currentScenario === 'dga_tunnel') {
      if (nodeId === 'db-historian') {
        return {
          isInfected: true,
          severity: 'HIGH',
          color: '#f59e0b',
          name: 'Tunnel.DNS.DGAv2',
          description: 'Process historian hijacked by algorithmic domain generation exfiltration tunnel with 150-char high-entropy labels.',
          rate: '2.5 pkts/s (DGA queries)',
          dominantChannel: 'entropy (86.7%)',
          peakScore: score.toFixed(1),
          cve: 'CVE-2026-7508',
          traces: [
            'T-0.3s | 10.0.1.50:53 → 10.0.1.1:53 | DNS Query | 150 B | H=5.12 bits | 🚨 HIGH-ENTROPY DGA LABEL (flow 0x3D88)',
            'T-0.2s | 10.0.1.50:53 → 10.0.1.1:53 | DNS Query | 150 B | H=5.08 bits | 🚨 ALGORITHMIC DOMAIN EXFIL (flow 0x3D88)',
            'T-0.1s | 10.0.1.50:53 → 10.0.1.1:53 | DNS Query | 150 B | H=5.15 bits | 🚨 TUNNEL SURGE DETECTED',
          ]
        };
      }
      if (nodeId === 'tx-diode' || nodeId === 'rx-diode' || nodeId === 'njode-core') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'ALERT',
          color: '#fbbf24',
          name: 'DGA Domain Anomaly Flagged',
          description: 'Shannon entropy surge in packet headers exceeding normal manifold.',
          peakScore: score.toFixed(1),
        };
      }
    }

    return {
      isInfected: false,
      severity: 'CLEAN',
      color: '#10b981',
      name: 'Clean Benign Operation',
      description: 'Device operating strictly within baseline parameters. Latent reconstruction error < τ.',
      rate: 'Normal SCADA baseline',
    };
  };

  // Main Canvas Render Loop (Physics & Animation)
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let resizeObserver;
    const resize = () => {
      const parent = canvas.parentElement;
      canvas.width = (parent && parent.clientWidth > 0) ? parent.clientWidth : 960;
      canvas.height = (parent && parent.clientHeight > 0) ? parent.clientHeight : 480;
    };
    resize();
    window.addEventListener('resize', resize);
    if (canvas.parentElement && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(canvas.parentElement);
    }

    // Handle real packet events from backend or prop
    const spawnEdgePacket = (from, to, threat = false, isDiode = false, isAlert = false, size = 64) => {
      const edgeIdx = edges.findIndex(e => e.from === from && e.to === to);
      if (edgeIdx !== -1) {
        activeParticlesRef.current.push({
          edgeIndex: edgeIdx,
          progress: 0.0,
          speedMultiplier: threat ? 1.6 : (isDiode ? 1.35 : 1.1),
          isThreat: threat,
          isDiodeBridge: isDiode || edges[edgeIdx].isDiodeBridge,
          isAlert: isAlert,
          size: Math.max(1.8, Math.min(3.2, Math.log2(size || 64) * 0.35)),
        });
      }
    };

    // Autonomous discrete packet trigger when in standalone simulation mode
    let simTimer;
    let simStep = 0;
    if (isStreaming) {
      simTimer = setInterval(() => {
        simStep++;
        const lastTs = lastPacketRef.current?.timestamp;
        const timeSinceReal = lastTs ? (Date.now() - lastTs * 1000) : 999999;
        
        // If real backend packets are actively flowing, let them drive the animation
        if (timeSinceReal < 2200) {
          return;
        }

        // Discrete pulse schedule (packets only flow when actual event occurs)
        if (simStep % 3 === 0) {
          spawnEdgePacket('plc-01', 'tx-diode', false, false, false, 128);
          setTimeout(() => spawnEdgePacket('tx-diode', 'optical-gap', false, true, false, 128), 180);
          setTimeout(() => spawnEdgePacket('optical-gap', 'rx-diode', false, true, false, 128), 340);
          setTimeout(() => spawnEdgePacket('rx-diode', 'njode-core', false, false, false, 128), 500);
        }

        if (simStep % 4 === 0) {
          const isDDoS = currentScenario === 'ddos_flood';
          spawnEdgePacket('plc-02', 'tx-diode', isDDoS, false, false, isDDoS ? 64 : 96);
          setTimeout(() => spawnEdgePacket('tx-diode', 'optical-gap', isDDoS, true, false, 64), 180);
          setTimeout(() => spawnEdgePacket('optical-gap', 'rx-diode', isDDoS, true, false, 64), 340);
          setTimeout(() => spawnEdgePacket('rx-diode', 'njode-core', isDDoS, false, false, 64), 500);
          if (isDDoS) {
            setTimeout(() => spawnEdgePacket('njode-core', 'soc-siem', true, false, true, 64), 680);
          }
        }

        if (simStep % 6 === 0) {
          const isDGA = currentScenario === 'dga_tunnel';
          spawnEdgePacket('db-historian', 'tx-diode', isDGA, false, false, isDGA ? 150 : 180);
          setTimeout(() => spawnEdgePacket('tx-diode', 'optical-gap', isDGA, true, false, 150), 180);
          setTimeout(() => spawnEdgePacket('optical-gap', 'rx-diode', isDGA, true, false, 150), 340);
          setTimeout(() => spawnEdgePacket('rx-diode', 'njode-core', isDGA, false, false, 150), 500);
          if (isDGA) {
            setTimeout(() => spawnEdgePacket('njode-core', 'soc-siem', true, false, true, 150), 680);
          }
        }

        if (currentScenario === 'exfil_burst') {
          spawnEdgePacket('ews-alpha', 'tx-diode', true, false, false, 1400);
          setTimeout(() => spawnEdgePacket('tx-diode', 'optical-gap', true, true, false, 1400), 120);
          setTimeout(() => spawnEdgePacket('optical-gap', 'rx-diode', true, true, false, 1400), 240);
          setTimeout(() => spawnEdgePacket('rx-diode', 'njode-core', true, false, false, 1400), 360);
          setTimeout(() => spawnEdgePacket('njode-core', 'soc-siem', true, false, true, 1400), 480);
        } else if (currentScenario === 'c2_beacon' && simStep % 8 === 0) {
          spawnEdgePacket('ews-alpha', 'tx-diode', true, false, false, 256);
          setTimeout(() => spawnEdgePacket('tx-diode', 'optical-gap', true, true, false, 256), 180);
          setTimeout(() => spawnEdgePacket('optical-gap', 'rx-diode', true, true, false, 256), 340);
          setTimeout(() => spawnEdgePacket('rx-diode', 'njode-core', true, false, false, 256), 500);
          setTimeout(() => spawnEdgePacket('njode-core', 'soc-siem', true, false, true, 256), 680);
        } else if (currentScenario === 'portscan' && simStep % 2 === 0) {
          spawnEdgePacket('ews-alpha', 'tx-diode', true, false, false, 54);
          setTimeout(() => spawnEdgePacket('tx-diode', 'optical-gap', true, true, false, 54), 140);
          setTimeout(() => spawnEdgePacket('optical-gap', 'rx-diode', true, true, false, 54), 280);
          setTimeout(() => spawnEdgePacket('rx-diode', 'njode-core', true, false, false, 54), 420);
          setTimeout(() => spawnEdgePacket('njode-core', 'soc-siem', true, false, true, 54), 560);
        } else if (currentScenario === 'tls_c2' && simStep % 6 === 0) {
          spawnEdgePacket('ews-alpha', 'tx-diode', true, false, false, 512);
          setTimeout(() => spawnEdgePacket('tx-diode', 'optical-gap', true, true, false, 512), 180);
          setTimeout(() => spawnEdgePacket('optical-gap', 'rx-diode', true, true, false, 512), 340);
          setTimeout(() => spawnEdgePacket('rx-diode', 'njode-core', true, false, false, 512), 500);
        }
      }, 120);
    }

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.save();
      // Apply pan & zoom
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);

      // 1. Subtle, clean structural grid (Dieter Rams / Swiss ratio)
      ctx.strokeStyle = 'rgba(39, 39, 42, 0.35)'; // zinc-800
      ctx.lineWidth = 1;
      const gridSize = 48;
      for (let x = -200; x < canvas.width * 1.6; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, -200);
        ctx.lineTo(x, canvas.height * 1.6);
        ctx.stroke();
      }
      for (let y = -200; y < canvas.height * 1.6; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(-200, y);
        ctx.lineTo(canvas.width * 1.6, y);
        ctx.stroke();
      }

      // 2. Optical Air-Gap Demarcation Zone (Center: x = 480 to 600)
      ctx.fillStyle = 'rgba(24, 24, 27, 0.45)';
      ctx.fillRect(480, 20, 120, canvas.height - 40);

      ctx.strokeStyle = 'rgba(63, 63, 70, 0.5)';
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(480, 20);
      ctx.lineTo(480, canvas.height - 20);
      ctx.moveTo(600, 20);
      ctx.lineTo(600, canvas.height - 20);
      ctx.stroke();
      ctx.setLineDash([]);

      // Section Boundary Headers
      ctx.font = '600 10px "JetBrains Mono", monospace';
      ctx.fillStyle = '#71717a';
      ctx.textAlign = 'left';
      ctx.fillText('ZONE A  ·  AIR-GAPPED IN-ZONE', 140, 42);

      ctx.textAlign = 'right';
      ctx.fillText('ZONE B  ·  PASSIVE MONITOR ENCLAVE', 940, 42);

      ctx.textAlign = 'center';
      ctx.fillStyle = '#a1a1aa';
      ctx.fillText('OPTICAL AIR GAP', 540, 42);
      ctx.font = '9px "JetBrains Mono", monospace';
      ctx.fillStyle = '#52525b';
      ctx.fillText('HARDWARE SIMPLEX DIODE', 540, 56);

      // 3. Draw Edges (Physical fiber/copper links)
      edges.forEach((edge) => {
        const source = nodes.find(n => n.id === edge.from);
        const target = nodes.find(n => n.id === edge.to);
        if (!source || !target) return;

        const sourceStatus = getMalwareStatus(source.id);
        const targetStatus = getMalwareStatus(target.id);
        const isThreatLine = sourceStatus.isInfected || targetStatus.isInfected;

        ctx.beginPath();
        ctx.moveTo(source.x, source.y);
        ctx.lineTo(target.x, target.y);

        if (edge.isDiodeBridge) {
          // Hardware Diode Simplex Link: distinct dashed path indicating galvanic gap
          ctx.setLineDash([5, 3]);
          ctx.strokeStyle = isThreatLine ? '#f43f5e' : '#38bdf8';
          ctx.lineWidth = 1.5;
        } else if (isThreatLine) {
          ctx.setLineDash([]);
          ctx.strokeStyle = 'rgba(244, 63, 94, 0.4)';
          ctx.lineWidth = 1.2;
        } else {
          ctx.setLineDash([]);
          ctx.strokeStyle = 'rgba(39, 39, 42, 0.7)';
          ctx.lineWidth = 1.0;
        }
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // 4. Real Packet Flows: Rendered ONLY when actual packets are actively traversing links
      const particles = activeParticlesRef.current;
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        const edge = edges[p.edgeIndex];
        if (!edge) {
          particles.splice(i, 1);
          continue;
        }
        const source = nodes.find(n => n.id === edge.from);
        const target = nodes.find(n => n.id === edge.to);
        if (!source || !target) {
          particles.splice(i, 1);
          continue;
        }

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const edgeDist = Math.hypot(dx, dy) || 1;

        // Physical velocity: advances toward target and vanishes upon arrival
        const pxPerFrame = 1.35 * (p.speedMultiplier || 1.0);
        p.progress += pxPerFrame / edgeDist;

        if (p.progress >= 1.0) {
          // Packet reached destination system! Removed from transit.
          particles.splice(i, 1);
          continue;
        }

        const rgb = p.isThreat 
          ? '244, 63, 94' 
          : p.isDiodeBridge 
          ? '56, 189, 248' 
          : '148, 163, 184';

        // Packet Head (crisp, zero blur)
        const px0 = source.x + dx * p.progress;
        const py0 = source.y + dy * p.progress;
        ctx.beginPath();
        ctx.arc(px0, py0, p.isThreat ? p.size + 0.8 : p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, 0.95)`;
        ctx.fill();

        // Trail Step 1 (5px behind)
        const p1 = p.progress - (5 / edgeDist);
        if (p1 >= 0) {
          const px1 = source.x + dx * p1;
          const py1 = source.y + dy * p1;
          ctx.beginPath();
          ctx.arc(px1, py1, p.size * 0.75, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb}, 0.40)`;
          ctx.fill();
        }

        // Trail Step 2 (10px behind)
        const p2 = p.progress - (10 / edgeDist);
        if (p2 >= 0) {
          const px2 = source.x + dx * p2;
          const py2 = source.y + dy * p2;
          ctx.beginPath();
          ctx.arc(px2, py2, p.size * 0.45, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb}, 0.15)`;
          ctx.fill();
        }
      }

      // 5. Draw Nodes (Minimalist Matte Surface with Status Pip)
      nodes.forEach((node) => {
        const status = getMalwareStatus(node.id);
        const isHovered = hoveredNode?.id === node.id;
        const isSelected = selectedNode?.id === node.id;

        // Subtle hover / selected ring (1px hairline)
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 4, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(212, 212, 216, 0.25)';
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        // Main Node Body (Matte Dark Zinc)
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.zone === 'barrier' ? '#18181b' : '#111318';
        ctx.fill();

        // 1px Border Ring
        ctx.strokeStyle = (status.isInfected || status.isTriggered)
          ? '#f43f5e'
          : status.isTransitThreat
          ? '#f59e0b'
          : isHovered
          ? '#52525b'
          : '#27272a';
        ctx.lineWidth = 1.0;
        ctx.stroke();

        // Minimalist Status Pip (Dieter Rams discrete indicator)
        const pipColor = (status.isInfected || status.isTriggered)
          ? '#f43f5e'
          : status.isTransitThreat
          ? '#f59e0b'
          : node.zone === 'barrier'
          ? '#38bdf8'
          : '#10b981';

        ctx.beginPath();
        ctx.arc(node.x, node.y, 3.5, 0, Math.PI * 2);
        ctx.fillStyle = pipColor;
        ctx.fill();

        // Primary Label Typography
        ctx.font = isHovered
          ? '600 11px Inter, system-ui, sans-serif'
          : '500 11px Inter, system-ui, sans-serif';
        ctx.fillStyle = (status.isInfected || status.isTriggered)
          ? '#f43f5e'
          : isHovered
          ? '#ffffff'
          : '#e4e4e7';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + node.radius + 14);

        // Secondary Monospace IP / Role
        ctx.font = '10px "JetBrains Mono", monospace';
        ctx.fillStyle = '#71717a';
        ctx.fillText(node.ip, node.x, node.y + node.radius + 26);
      });

      ctx.restore();

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      if (resizeObserver) resizeObserver.disconnect();
      if (simTimer) clearInterval(simTimer);
      cancelAnimationFrame(animationId);
    };
  }, [nodes, edges, currentScenario, hoveredNode, selectedNode, transform, isStreaming]);

  // Trigger particle animation when a live real packet event is received
  useEffect(() => {
    if (!packetEvent) return;
    lastPacketRef.current = packetEvent;
    const fromId = packetEvent.from;
    const toId = packetEvent.to;
    const isThreat = !!packetEvent.threat;
    const isDiodeBridge = !!packetEvent.is_diode_bridge;
    const isAlert = !!packetEvent.is_alert;
    const size = packetEvent.size || 64;

    const edgeIdx = edges.findIndex(e => e.from === fromId && e.to === toId);
    if (edgeIdx !== -1) {
      activeParticlesRef.current.push({
        edgeIndex: edgeIdx,
        progress: 0.0,
        speedMultiplier: isThreat ? 1.6 : (isDiodeBridge ? 1.35 : 1.1),
        isThreat: isThreat,
        isDiodeBridge: isDiodeBridge || edges[edgeIdx].isDiodeBridge,
        isAlert: isAlert,
        size: Math.max(1.8, Math.min(3.2, Math.log2(size) * 0.35)),
      });
      setInFlightCount(activeParticlesRef.current.length);
    }
  }, [packetEvent, edges]);

  // Convert mouse event coordinates to graph world space
  const getWorldCoord = (e) => {
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;
    return {
      x: (mouseX - transform.x) / transform.k,
      y: (mouseY - transform.y) / transform.k,
      screenX: e.clientX,
      screenY: e.clientY,
    };
  };

  const handleMouseDown = (e) => {
    const { x, y } = getWorldCoord(e);
    // Check if clicking a node to drag
    const clicked = nodes.find(n => {
      const dx = n.x - x;
      const dy = n.y - y;
      return Math.sqrt(dx * dx + dy * dy) <= n.radius + 4;
    });

    if (clicked) {
      setDraggedNode(clicked);
      setSelectedNode(clicked);
    } else {
      // Pan canvas
      isPanningRef.current = true;
      panStartRef.current = { x: e.clientX - transform.x, y: e.clientY - transform.y };
    }
  };

  const handleMouseMove = (e) => {
    const { x, y } = getWorldCoord(e);

    if (draggedNode) {
      setNodes(prev => prev.map(n => n.id === draggedNode.id ? { ...n, x, y } : n));
      return;
    }

    if (isPanningRef.current) {
      setTransform(prev => ({
        ...prev,
        x: e.clientX - panStartRef.current.x,
        y: e.clientY - panStartRef.current.y,
      }));
      return;
    }

    // Check hover
    const hit = nodes.find(n => {
      const dx = n.x - x;
      const dy = n.y - y;
      return Math.sqrt(dx * dx + dy * dy) <= n.radius + 6;
    });
    setHoveredNode(hit || null);
  };

  const handleMouseUp = () => {
    setDraggedNode(null);
    isPanningRef.current = false;
  };

  // Zoom with scroll wheel
  const handleWheel = (e) => {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
    setTransform(prev => ({
      ...prev,
      k: Math.max(0.5, Math.min(prev.k * zoomFactor, 2.5)),
    }));
  };

  const activeNodeStatus = selectedNode ? getMalwareStatus(selectedNode.id) : null;
  const hoveredNodeStatus = hoveredNode ? getMalwareStatus(hoveredNode.id) : null;

  return (
    <div className="rounded-xl border border-zinc-800 bg-[#090a0f] overflow-hidden flex flex-col relative h-full" ref={containerRef}>
      {/* Top Controls Header */}
      <div className="flex flex-wrap items-center justify-between px-5 py-2.5 border-b border-zinc-800/80 bg-zinc-950/60 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Hardware Diode Topology // Passive Tap Architecture
            </h3>
            <p className="text-[11px] text-zinc-400">
              Unidirectional physical barrier · Simplex laser tap · Continuous latent observation
            </p>
          </div>
        </div>

        {/* Action buttons & Zoom controls */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <div className="flex items-center gap-1 bg-zinc-900 px-1.5 py-1 rounded-md border border-zinc-800">
            <button
              onClick={() => setTransform(t => ({ ...t, k: Math.min(t.k * 1.15, 2.5) }))}
              className="p-1 text-zinc-400 hover:text-zinc-100 rounded transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTransform(t => ({ ...t, k: Math.max(t.k * 0.85, 0.5) }))}
              className="p-1 text-zinc-400 hover:text-zinc-100 rounded transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTransform({ x: 0, y: 0, k: 1 })}
              className="p-1 text-zinc-400 hover:text-zinc-100 rounded transition-colors"
              title="Reset View"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs ${
            currentScenario !== 'calm'
              ? 'border-rose-900/60 bg-rose-950/30 text-rose-300'
              : 'border-zinc-800 bg-zinc-900 text-zinc-400'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              currentScenario !== 'calm' ? 'bg-rose-500' : 'bg-emerald-500'
            }`} />
            <span>{currentScenario !== 'calm' ? 'ANOMALY DETECTED' : 'NORMAL ENCLAVE OPERATION'}</span>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div 
        className="relative flex-1 min-h-0 w-full bg-[#07090e] cursor-grab active:cursor-grabbing overflow-hidden"
        onWheel={handleWheel}
      >
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="w-full h-full block"
        />

        {/* Hover Tooltip HUD */}
        {hoveredNode && !selectedNode && (
          <div
            className="absolute z-30 pointer-events-none p-3 rounded-lg bg-zinc-900/95 border border-zinc-800 backdrop-blur-md shadow-xl font-mono text-xs max-w-xs transition-opacity duration-150"
            style={{
              left: `${Math.max(20, Math.min(hoveredNode.x * transform.k + transform.x + 20, 680))}px`,
              top: `${Math.max(hoveredNode.y * transform.k + transform.y - 40, 20)}px`,
            }}
          >
            <div className="flex items-center justify-between gap-2 pb-1.5 mb-1.5 border-b border-zinc-800">
              <span className="font-semibold text-zinc-100 flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: hoveredNodeStatus?.color || '#10b981' }}
                />
                {hoveredNode.label}
              </span>
              <span className="text-[10px] text-zinc-400">{hoveredNode.ip}</span>
            </div>
            <div className="text-[11px] text-zinc-300 mb-1">
              Role: <span className="text-zinc-200">{hoveredNode.sublabel}</span>
            </div>
            <div className="text-[11px] text-zinc-400 mb-1">
              Status: <span style={{ color: hoveredNodeStatus?.color || '#10b981' }}>{hoveredNodeStatus?.name}</span>
            </div>
            {hoveredNodeStatus?.isInfected && (
              <div className="p-1.5 bg-rose-950/40 border border-rose-800/40 rounded text-rose-300 text-[10px] mt-1.5">
                {hoveredNodeStatus.description}
              </div>
            )}
            <div className="text-[10px] text-zinc-400 mt-2 text-right">
              Click node for forensic trace
            </div>
          </div>
        )}

        {/* Legend Overlay at Bottom-Left */}
        <div className="absolute bottom-4 left-4 z-20 p-2.5 rounded-lg bg-zinc-950/90 border border-zinc-800 font-mono text-[11px] space-y-1.5 shadow-md">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span className="text-zinc-400">Normal Monitored Node</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-500"></span>
            <span className="text-rose-400">Compromised Node</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-500"></span>
            <span className="text-amber-400">Anomalous Transit / Gateway</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-sky-400"></span>
            <span className="text-zinc-400">Simplex Diode Bridge Flow</span>
          </div>
        </div>
      </div>

      {/* Detailed Node Inspection Drawer (On Node Click) */}
      {selectedNode && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl max-w-2xl w-full p-5 shadow-2xl relative font-mono text-xs">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-zinc-800">
              <div className="flex items-center gap-3">
                <div
                  className="p-2 rounded-lg border"
                  style={{
                    backgroundColor: `${activeNodeStatus?.color}15`,
                    borderColor: `${activeNodeStatus?.color}30`,
                    color: activeNodeStatus?.color,
                  }}
                >
                  {activeNodeStatus?.isInfected ? <ShieldAlert className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-zinc-100 flex items-center gap-2">
                    {selectedNode.label}
                    <span className="text-xs text-zinc-400 font-normal">[{selectedNode.ip}]</span>
                  </h4>
                  <p className="text-xs text-zinc-400">{selectedNode.sublabel} · Zone: {selectedNode.zone.toUpperCase()}</p>
                </div>
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-100 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Status Alert Banner */}
            <div
              className="p-3 rounded-lg border mb-3"
              style={{
                backgroundColor: `${activeNodeStatus?.color}10`,
                borderColor: `${activeNodeStatus?.color}30`,
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-semibold uppercase tracking-wider text-xs" style={{ color: activeNodeStatus?.color }}>
                  {activeNodeStatus?.name}
                </span>
                {activeNodeStatus?.cve && (
                  <span className="px-1.5 py-0.5 rounded bg-black/40 text-rose-300 text-[10px] border border-rose-800/40">
                    {activeNodeStatus.cve}
                  </span>
                )}
              </div>
              <p className="text-zinc-300 text-[11px] leading-relaxed">
                {activeNodeStatus?.description}
              </p>
            </div>

            {/* Diagnostic Metrics Grid */}
            <div className="grid grid-cols-3 gap-2.5 mb-3">
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">TRAFFIC RATE</span>
                <div className="text-xs font-semibold text-zinc-200 mt-1">
                  {activeNodeStatus?.rate || selectedNode.normalRate}
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">ATTRIBUTION CHANNEL</span>
                <div className="text-xs font-semibold text-amber-400 mt-1">
                  {activeNodeStatus?.dominantChannel || 'None (Benign)'}
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">ANOMALY SCORE (PEAK)</span>
                <div className="text-xs font-semibold text-sky-400 mt-1">
                  {activeNodeStatus?.peakScore || score.toFixed(2)} / τ = {tau.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Live Packet Tail for this Node */}
            <div>
              <span className="text-zinc-400 text-[11px] font-medium mb-1.5 block">
                RECENT OBSERVED TELEMETRY FRAMES
              </span>
              <div className="p-2.5 bg-zinc-950 rounded-lg border border-zinc-800 text-[11px] text-zinc-300 space-y-1 max-h-36 overflow-y-auto">
                <div className="text-zinc-400 text-[10px] border-b border-zinc-850 pb-1">
                  TIMESTAMP | SRC → DST | PROTOCOL | PAYLOAD | ENTROPY | STATUS
                </div>
                {activeNodeStatus?.traces && activeNodeStatus.traces.length > 0 ? (
                  activeNodeStatus.traces.map((traceLine, tIdx) => (
                    <div 
                      key={tIdx} 
                      className="px-1 py-0.5 rounded text-rose-300 bg-rose-950/20 font-mono"
                    >
                      {traceLine}
                    </div>
                  ))
                ) : (
                  <>
                    <div className="text-zinc-400">
                      T-0.4s &nbsp;| {selectedNode.ip}:4840 → 10.0.1.1:9999 | UDP | 120 B | H=3.42 bits | BENIGN_MANIFOLD
                    </div>
                    <div className="text-zinc-400">
                      T-0.1s &nbsp;| {selectedNode.ip}:4840 → 10.0.1.1:9999 | UDP | 96 B  | H=3.38 bits | BENIGN_MANIFOLD
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Air-Gap Guarantee Note */}
            <div className="mt-3 pt-2.5 border-t border-zinc-800 flex items-center justify-between text-[11px] text-zinc-400">
              <span className="flex items-center gap-1.5 text-zinc-400">
                <Lock className="w-3.5 h-3.5 text-emerald-400" />
                Physical diode guarantees zero inbound payload reflection into Zone A.
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                className="px-3 py-1 bg-zinc-800 hover:bg-zinc-700 text-zinc-200 rounded-md transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
