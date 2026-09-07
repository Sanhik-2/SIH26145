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
  // Zone A: Air-Gapped High Security In-Zone
  {
    id: 'plc-01',
    label: 'SCADA PLC-01',
    sublabel: 'Turbine Governor',
    ip: '10.0.1.10',
    zone: 'in-zone',
    x: 180,
    y: 160,
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
    y: 280,
    vx: 0,
    vy: 0,
    radius: 17,
    type: 'controller',
    normalRate: '3 pkts/s',
  },
  {
    id: 'ews-alpha',
    label: 'Workstation Alpha',
    sublabel: 'Engineering Terminal',
    ip: '10.0.1.25',
    zone: 'in-zone',
    x: 290,
    y: 110,
    vx: 0,
    vy: 0,
    radius: 22,
    type: 'workstation',
    normalRate: '12 pkts/s',
  },
  {
    id: 'db-historian',
    label: 'Process Historian',
    sublabel: 'SCADA Telemetry DB',
    ip: '10.0.1.50',
    zone: 'in-zone',
    x: 260,
    y: 330,
    vx: 0,
    vy: 0,
    radius: 20,
    type: 'database',
    normalRate: '8 pkts/s',
  },
  {
    id: 'tx-diode',
    label: 'In-Zone TX Diode',
    sublabel: 'Simplex UDP Laser Emitter',
    ip: '10.0.1.1',
    zone: 'diode-tx',
    x: 420,
    y: 220,
    vx: 0,
    vy: 0,
    radius: 24,
    type: 'transmitter',
    normalRate: '18 pkts/s',
  },

  // The Diode Optical Barrier Node
  {
    id: 'optical-gap',
    label: 'Optical Air-Gap Isolator',
    sublabel: '100% Galvanic Simplex',
    ip: '0.0.0.0 [PHYSICAL]',
    zone: 'barrier',
    x: 560,
    y: 220,
    vx: 0,
    vy: 0,
    radius: 16,
    type: 'barrier',
    normalRate: 'Simplex Laser',
  },

  // Zone B: Monitored Scanner Side / SOC Subnet
  {
    id: 'rx-diode',
    label: 'Scanner RX Diode',
    sublabel: 'Photodiode Detector',
    ip: '192.168.10.1',
    zone: 'diode-rx',
    x: 700,
    y: 220,
    vx: 0,
    vy: 0,
    radius: 24,
    type: 'receiver',
    normalRate: '18 pkts/s',
  },
  {
    id: 'njode-core',
    label: 'CHRONOS NJ-ODE',
    sublabel: 'Continuous Latent Engine',
    ip: '192.168.10.5',
    zone: 'scanner',
    x: 840,
    y: 150,
    vx: 0,
    vy: 0,
    radius: 26,
    type: 'ai-core',
    normalRate: 'Inference 1.1ms',
  },
  {
    id: 'soc-siem',
    label: 'SOC Alert Sink',
    sublabel: 'Incident Dispatcher',
    ip: '192.168.10.100',
    zone: 'scanner',
    x: 960,
    y: 260,
    vx: 0,
    vy: 0,
    radius: 20,
    type: 'siem',
    normalRate: 'Active Polling',
  },
  {
    id: 'sync-srv',
    label: 'Web Sync Gateway',
    sublabel: 'NTP & Benign Sync',
    ip: '192.168.10.15',
    zone: 'scanner',
    x: 790,
    y: 340,
    vx: 0,
    vy: 0,
    radius: 19,
    type: 'server',
    normalRate: '0.15 pkts/s',
  },
];

const INITIAL_EDGES = [
  { from: 'plc-01', to: 'tx-diode', speed: 1.0 },
  { from: 'plc-02', to: 'tx-diode', speed: 1.0 },
  { from: 'ews-alpha', to: 'tx-diode', speed: 1.4 },
  { from: 'db-historian', to: 'tx-diode', speed: 1.1 },
  { from: 'ews-alpha', to: 'db-historian', speed: 0.8 },
  { from: 'plc-01', to: 'plc-02', speed: 0.6 },
  // Simplex optical bridge
  { from: 'tx-diode', to: 'optical-gap', speed: 2.2, isDiodeBridge: true },
  { from: 'optical-gap', to: 'rx-diode', speed: 2.2, isDiodeBridge: true },
  // Scanner side
  { from: 'rx-diode', to: 'njode-core', speed: 1.8 },
  { from: 'njode-core', to: 'soc-siem', speed: 1.2 },
  { from: 'rx-diode', to: 'sync-srv', speed: 0.7 },
];

export default function NetworkGraphView({ currentScenario = 'calm', score = 0.48, tau = 2.81 }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Nodes state with physics coordinates
  const [nodes, setNodes] = useState(INITIAL_NODES);
  const [edges] = useState(INITIAL_EDGES);

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
    if (currentScenario === 'exfil_burst') {
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
          dominantChannel: 'entropy (100%)',
          peakScore: score.toFixed(1),
          cve: 'CVE-2026-1640',
        };
      }
      if (nodeId === 'tx-diode' || nodeId === 'rx-diode' || nodeId === 'njode-core') {
        return {
          isInfected: false,
          isTransitThreat: true,
          severity: 'SUSPECTED',
          color: '#c084fc',
          name: 'Periodic Entropy Breach',
          description: 'Strict periodicity detected in irregular packet gaps. Attributed to entropy.',
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

    // Packet particles traveling along edges
    const particles = [];
    const maxParticles = 40;

    const resize = () => {
      const parent = canvas.parentElement;
      canvas.width = (parent && parent.clientWidth > 0) ? parent.clientWidth : 960;
      canvas.height = (parent && parent.clientHeight > 0) ? parent.clientHeight : 480;
    };
    resize();
    window.addEventListener('resize', resize);

    // Seed initial particles
    edges.forEach((edge, eIdx) => {
      for (let i = 0; i < 3; i++) {
        particles.push({
          edgeIndex: eIdx,
          progress: Math.random(),
          speed: 0.006 * (edge.speed || 1.0) * (currentScenario !== 'calm' ? 1.6 : 1.0),
        });
      }
    });

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.save();
      // Apply pan & zoom
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);

      // Draw subtle background grid for Obsidian feel
      ctx.strokeStyle = 'rgba(30, 41, 59, 0.25)';
      ctx.lineWidth = 1;
      const gridSize = 40;
      for (let x = -200; x < canvas.width * 1.5; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, -200);
        ctx.lineTo(x, canvas.height * 1.5);
        ctx.stroke();
      }
      for (let y = -200; y < canvas.height * 1.5; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(-200, y);
        ctx.lineTo(canvas.width * 1.5, y);
        ctx.stroke();
      }

      // Draw Zone Partition Dividers (Air-Gapped In-Zone vs Monitored Scanner Side)
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.15)';
      ctx.setLineDash([6, 6]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(560, 40);
      ctx.lineTo(560, canvas.height - 40);
      ctx.stroke();
      ctx.setLineDash([]);

      ctx.fillStyle = 'rgba(6, 182, 212, 0.4)';
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.fillText('◄ AIR-GAPPED HIGH-SECURITY IN-ZONE', 280, 50);
      ctx.fillText('MONITORED SCANNER / SOC SIDE ►', 620, 50);

      // 1. Draw Edges (Connections)
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
          // Highlighted Optical Simplex Diode Link
          ctx.strokeStyle = isThreatLine ? '#ef4444' : '#00f0ff';
          ctx.lineWidth = 2.5;
          ctx.shadowColor = isThreatLine ? 'rgba(239, 68, 68, 0.8)' : 'rgba(0, 240, 255, 0.8)';
          ctx.shadowBlur = 10;
        } else if (isThreatLine) {
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.6)';
          ctx.lineWidth = 1.8;
          ctx.shadowColor = 'rgba(239, 68, 68, 0.5)';
          ctx.shadowBlur = 6;
        } else {
          ctx.strokeStyle = 'rgba(71, 85, 105, 0.45)';
          ctx.lineWidth = 1.2;
          ctx.shadowBlur = 0;
        }
        ctx.stroke();
        ctx.shadowBlur = 0;
      });

      // 2. Animate and Draw Subtle Flowing Packet Particles
      particles.forEach((p) => {
        const edge = edges[p.edgeIndex];
        if (!edge) return;
        const source = nodes.find(n => n.id === edge.from);
        const target = nodes.find(n => n.id === edge.to);
        if (!source || !target) return;

        p.progress += p.speed;
        if (p.progress > 1.0) p.progress = 0;

        const px = source.x + (target.x - source.x) * p.progress;
        const py = source.y + (target.y - source.y) * p.progress;

        const sourceStatus = getMalwareStatus(source.id);
        const isThreat = sourceStatus.isInfected || (edge.isDiodeBridge && currentScenario !== 'calm');

        ctx.beginPath();
        ctx.arc(px, py, isThreat ? 3.2 : 2.2, 0, Math.PI * 2);
        ctx.fillStyle = isThreat ? '#ef4444' : '#00f0ff';
        ctx.shadowColor = isThreat ? '#ef4444' : '#00f0ff';
        ctx.shadowBlur = 8;
        ctx.fill();
        ctx.shadowBlur = 0;
      });

      // 3. Draw Nodes (Obsidian Graph Nodes)
      nodes.forEach((node) => {
        const status = getMalwareStatus(node.id);
        const isHovered = hoveredNode?.id === node.id;
        const isSelected = selectedNode?.id === node.id;

        // Outer threat pulse ring for infected nodes
        if (status.isInfected) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 8 + Math.sin(Date.now() * 0.008) * 3, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Selected halo
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 5, 0, Math.PI * 2);
          ctx.strokeStyle = '#00f0ff';
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Main Node Body Circle
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);

        if (status.isInfected) {
          ctx.fillStyle = '#991b1b';
          ctx.shadowColor = '#ef4444';
          ctx.shadowBlur = 15;
        } else if (status.isTransitThreat) {
          ctx.fillStyle = '#c2410c';
          ctx.shadowColor = '#f97316';
          ctx.shadowBlur = 10;
        } else if (node.zone === 'barrier') {
          ctx.fillStyle = '#0f766e';
          ctx.shadowColor = '#14b8a6';
          ctx.shadowBlur = 8;
        } else {
          ctx.fillStyle = '#1e293b';
          ctx.shadowColor = '#38bdf8';
          ctx.shadowBlur = isHovered ? 12 : 4;
        }
        ctx.fill();
        ctx.shadowBlur = 0;

        // Node Border Ring
        ctx.strokeStyle = status.isInfected
          ? '#ef4444'
          : status.isTransitThreat
          ? '#fb923c'
          : isHovered
          ? '#38bdf8'
          : '#475569';
        ctx.lineWidth = isHovered ? 2.5 : 1.5;
        ctx.stroke();

        // Node Inner Core Dot
        ctx.beginPath();
        ctx.arc(node.x, node.y, node.radius * 0.35, 0, Math.PI * 2);
        ctx.fillStyle = status.isInfected ? '#fecaca' : isHovered ? '#ffffff' : '#94a3b8';
        ctx.fill();

        // Node Label Typography
        ctx.font = isHovered
          ? 'bold 11px "JetBrains Mono", monospace'
          : '10px "JetBrains Mono", monospace';
        ctx.fillStyle = status.isInfected
          ? '#f87171'
          : isHovered
          ? '#ffffff'
          : '#cbd5e1';
        ctx.textAlign = 'center';
        ctx.fillText(node.label, node.x, node.y + node.radius + 14);

        // Small IP / Role Sublabel
        ctx.font = '9px "JetBrains Mono", monospace';
        ctx.fillStyle = status.isInfected ? '#fca5a5' : '#64748b';
        ctx.fillText(node.ip, node.x, node.y + node.radius + 25);
      });

      ctx.restore();

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(animationId);
    };
  }, [nodes, edges, currentScenario, hoveredNode, selectedNode, transform]);

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
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl overflow-hidden shadow-2xl flex flex-col relative" ref={containerRef}>
      {/* Top Controls Header */}
      <div className="flex flex-wrap items-center justify-between px-6 py-3.5 border-b border-slate-800/80 bg-slate-950/80">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono flex items-center gap-2">
              Obsidian Topology Graph // Air-Gap Network Map
            </h3>
            <p className="text-xs text-slate-400">
              Interactive force-directed nodes · Real-time malware color-coding · Subtle packet streams
            </p>
          </div>
        </div>

        {/* Action buttons & Zoom controls */}
        <div className="flex items-center gap-2 font-mono text-xs">
          <div className="flex items-center gap-1 bg-slate-900 px-2 py-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setTransform(t => ({ ...t, k: Math.min(t.k * 1.15, 2.5) }))}
              className="p-1 text-slate-400 hover:text-white rounded"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTransform(t => ({ ...t, k: Math.max(t.k * 0.85, 0.5) }))}
              className="p-1 text-slate-400 hover:text-white rounded"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setTransform({ x: 0, y: 0, k: 1 })}
              className="p-1 text-slate-400 hover:text-white rounded"
              title="Reset View"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-slate-300">
            <span className={`w-2 h-2 rounded-full ${
              currentScenario !== 'calm' ? 'bg-red-500 animate-ping' : 'bg-emerald-400'
            }`} />
            <span>{currentScenario !== 'calm' ? '🚨 THREAT CORRELATION ACTIVE' : 'ALL NODES CLEAN'}</span>
          </div>
        </div>
      </div>

      {/* Main Canvas Area */}
      <div 
        className="relative h-[480px] w-full bg-[#070a10] cursor-grab active:cursor-grabbing overflow-hidden"
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
            className="absolute z-30 pointer-events-none p-3 rounded-xl bg-slate-950/90 border border-slate-700/80 backdrop-blur-md shadow-2xl font-mono text-xs max-w-xs transition-opacity duration-150"
            style={{
              left: `${Math.max(20, Math.min(hoveredNode.x * transform.k + transform.x + 20, 680))}px`,
              top: `${Math.max(hoveredNode.y * transform.k + transform.y - 40, 20)}px`,
            }}
          >
            <div className="flex items-center justify-between gap-2 pb-1.5 mb-1.5 border-b border-slate-800">
              <span className="font-bold text-white flex items-center gap-1.5">
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: hoveredNodeStatus?.color || '#10b981' }}
                />
                {hoveredNode.label}
              </span>
              <span className="text-[10px] text-slate-400">{hoveredNode.ip}</span>
            </div>
            <div className="text-[11px] text-slate-300 mb-1">
              Role: <b className="text-cyan-300">{hoveredNode.sublabel}</b>
            </div>
            <div className="text-[11px] text-slate-400 mb-1">
              Status: <b style={{ color: hoveredNodeStatus?.color || '#10b981' }}>{hoveredNodeStatus?.name}</b>
            </div>
            {hoveredNodeStatus?.isInfected && (
              <div className="p-1.5 bg-red-950/40 border border-red-500/30 rounded text-red-300 text-[10px] mt-1.5">
                ⚠️ {hoveredNodeStatus.description}
              </div>
            )}
            <div className="text-[10px] text-slate-500 mt-2 text-right">
              👉 Click node for detailed logs
            </div>
          </div>
        )}

        {/* Legend Overlay at Bottom-Left */}
        <div className="absolute bottom-4 left-4 z-20 p-2.5 rounded-xl bg-slate-950/85 border border-slate-800/80 backdrop-blur-md font-mono text-[11px] space-y-1.5 shadow-lg">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            <span className="text-slate-300">Clean / Benign Node</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
            <span className="text-red-300">Compromised / Malware Active</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-amber-400"></span>
            <span className="text-amber-300">Anomalous Transit / Gateway</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
            <span className="text-cyan-300">Flowing Packet Telemetry</span>
          </div>
        </div>
      </div>

      {/* Detailed Node Inspection Drawer (On Node Click) */}
      {selectedNode && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-2xl w-full p-6 shadow-2xl relative font-mono text-xs">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 mb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div
                  className="p-2 rounded-xl border"
                  style={{
                    backgroundColor: `${activeNodeStatus?.color}20`,
                    borderColor: `${activeNodeStatus?.color}60`,
                    color: activeNodeStatus?.color,
                  }}
                >
                  {activeNodeStatus?.isInfected ? <ShieldAlert className="w-5 h-5" /> : <ShieldCheck className="w-5 h-5" />}
                </div>
                <div>
                  <h4 className="text-base font-bold text-white flex items-center gap-2">
                    {selectedNode.label}
                    <span className="text-xs text-slate-400 font-normal">[{selectedNode.ip}]</span>
                  </h4>
                  <p className="text-xs text-slate-400">{selectedNode.sublabel} · Zone: {selectedNode.zone.toUpperCase()}</p>
                </div>
              </div>

              <button
                onClick={() => setSelectedNode(null)}
                className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-all"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Status Alert Banner */}
            <div
              className="p-3.5 rounded-xl border mb-4"
              style={{
                backgroundColor: `${activeNodeStatus?.color}15`,
                borderColor: `${activeNodeStatus?.color}40`,
              }}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold uppercase tracking-wider" style={{ color: activeNodeStatus?.color }}>
                  {activeNodeStatus?.name}
                </span>
                {activeNodeStatus?.cve && (
                  <span className="px-2 py-0.5 rounded bg-black/40 text-red-300 text-[10px] border border-red-500/30">
                    {activeNodeStatus.cve}
                  </span>
                )}
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                {activeNodeStatus?.description}
              </p>
            </div>

            {/* Diagnostic Metrics Grid */}
            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                <span className="text-slate-400 text-[10px]">CURRENT TRAFFIC RATE</span>
                <div className="text-sm font-bold text-white mt-1">
                  {activeNodeStatus?.rate || selectedNode.normalRate}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                <span className="text-slate-400 text-[10px]">DOMINANT ATTRIBUTION</span>
                <div className="text-sm font-bold text-amber-400 mt-1">
                  {activeNodeStatus?.dominantChannel || 'None (Calm)'}
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800">
                <span className="text-slate-400 text-[10px]">ANOMALY SCORE (PEAK)</span>
                <div className="text-sm font-bold text-cyan-400 mt-1">
                  {activeNodeStatus?.peakScore || score.toFixed(2)} / τ = {tau.toFixed(2)}
                </div>
              </div>
            </div>

            {/* Live Packet Tail for this Node */}
            <div>
              <span className="text-slate-400 text-xs font-semibold mb-2 block">
                RECENT PACKET TRACE &amp; TELEMETRY FRAMES
              </span>
              <div className="p-3 bg-slate-950 rounded-xl border border-slate-800 text-[11px] text-slate-300 space-y-1 max-h-40 overflow-y-auto">
                <div className="text-slate-500 text-[10px] border-b border-slate-900 pb-1">
                  TIMESTAMP | SRC → DST | PROTOCOL | PAYLOAD SIZE | ENTROPY | STATUS
                </div>
                <div className="text-emerald-400">
                  T-0.4s &nbsp;| {selectedNode.ip}:4840 → 10.0.1.1:9999 | UDP | 120 B | H=3.42 bits | VERIFIED BENIGN
                </div>
                {activeNodeStatus?.isInfected ? (
                  <>
                    <div className="text-red-400 font-bold bg-red-950/20 px-1 py-0.5 rounded">
                      T-0.2s &nbsp;| {selectedNode.ip}:9999 → 10.0.1.1:9999 | UDP | 1400 B | H=7.82 bits | 🚨 ANOMALY BREACH
                    </div>
                    <div className="text-red-400 font-bold bg-red-950/20 px-1 py-0.5 rounded">
                      T-0.1s &nbsp;| {selectedNode.ip}:9999 → 10.0.1.1:9999 | UDP | 1400 B | H=7.85 bits | 🚨 PERSISTENT ATTACK
                    </div>
                  </>
                ) : (
                  <div className="text-slate-400">
                    T-0.1s &nbsp;| {selectedNode.ip}:4840 → 10.0.1.1:9999 | UDP | 96 B  | H=3.38 bits | VERIFIED BENIGN
                  </div>
                )}
              </div>
            </div>

            {/* Air-Gap Guarantee Note */}
            <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <Lock className="w-3.5 h-3.5" />
                Hardware Air-Gap: Simplex laser guarantees zero inbound payload reflection.
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-white rounded-lg transition-colors"
              >
                Close Logs
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
