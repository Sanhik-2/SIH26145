import React, { useState, useEffect, useRef } from 'react';
import {
  ShieldAlert,
  ShieldCheck,
  Zap,
  Lock,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  X,
  Layers,
  Flame,
  Radio,
  Activity,
  Cpu
} from 'lucide-react';

// Baseline Architectural Backbone: Real Hardware Diode Bridge
const BASE_NODES = [
  // Zone A: Active In-Zone Nuclear SCADA Node (BARC Kudankulam Unit 1 PWR)
  {
    id: 'nuclear-scada',
    label: 'Kudankulam Unit 1 PWR',
    sublabel: 'Primary Reactor SCADA',
    ip: '192.168.1.10:502',
    zone: 'in-zone',
    x: 180,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 22,
    type: 'scada',
    normalRate: '1 packet/s',
    p_bar: 155.5,
    tavg_c: 310.0,
    flow_kgs: 16515.8,
    mw: 955.3,
    state: 'NOMINAL_FULL_POWER',
  },

  // Optical Egress Diode Transmitter
  {
    id: 'tx-diode',
    label: 'Optical TX Diode',
    sublabel: 'Simplex QR / Photon Emitter',
    ip: '10.0.1.1',
    zone: 'diode-tx',
    x: 410,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 22,
    type: 'transmitter',
    normalRate: 'Continuous Simplex',
  },

  // Optical Air-Gap Barrier (Center - Strict Galvanic Gap)
  {
    id: 'optical-gap',
    label: 'Physical Optical Air-Gap',
    sublabel: '100% Galvanic Isolation',
    ip: 'ZERO COPPER / RF RETURN',
    zone: 'barrier',
    x: 540,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 16,
    type: 'barrier',
    normalRate: 'Photons Only',
  },

  // Zone B: Monitored Air-Gapped Scanner Enclave (Right)
  {
    id: 'rx-diode',
    label: 'Optical RX Diode',
    sublabel: 'Iriun / Photodiode Scanner',
    ip: '192.168.10.1',
    zone: 'diode-rx',
    x: 670,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 22,
    type: 'receiver',
    normalRate: 'Continuous Ingest',
  },
  {
    id: 'njode-core',
    label: 'CHRONOS NJ-ODE Core',
    sublabel: 'Continuous Latent AI Engine',
    ip: '192.168.10.5',
    zone: 'scanner',
    x: 810,
    y: 160,
    vx: 0,
    vy: 0,
    radius: 24,
    type: 'ai-core',
    normalRate: 'Inference 1.1ms',
  },
  {
    id: 'soc-siem',
    label: 'Air-Gapped SOC SIEM',
    sublabel: 'Defense Terminal HUD',
    ip: '192.168.10.100',
    zone: 'scanner',
    x: 940,
    y: 200,
    vx: 0,
    vy: 0,
    radius: 20,
    type: 'siem',
    normalRate: 'Real-Time Telemetry',
  },
];

const BASE_EDGES = [
  // In-Zone SCADA to Diode Transmitter
  { from: 'nuclear-scada', to: 'tx-diode' },
  // Unidirectional Simplex Optical Diode Bridge
  { from: 'tx-diode', to: 'optical-gap', isDiodeBridge: true },
  { from: 'optical-gap', to: 'rx-diode', isDiodeBridge: true },
  // Scanner Enclave Internal Links
  { from: 'rx-diode', to: 'njode-core' },
  { from: 'njode-core', to: 'soc-siem' },
];

export default function NetworkGraphView({ 
  currentScenario = 'calm', 
  score = 0.48, 
  tau = 2.464,
  packetEvent = null,
  isStreaming = true,
}) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  // Dynamic Nodes & Edges: ONLY connected nodes exist on this topology!
  const [nodes, setNodes] = useState(BASE_NODES);
  const [edges, setEdges] = useState(BASE_EDGES);

  // Real in-flight packets (ONLY populated when real packets flow)
  const activeParticlesRef = useRef([]);
  const [lastPacketTime, setLastPacketTime] = useState(null);

  // Mouse interaction state
  const [hoveredNode, setHoveredNode] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [draggedNode, setDraggedNode] = useState(null);

  // Transform: pan & zoom
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 });
  const isPanningRef = useRef(false);
  const panStartRef = useRef({ x: 0, y: 0 });

  // Live node status mapping based on REAL packet events and SCADA physics
  const getMalwareStatus = (nodeId) => {
    const node = nodes.find(n => n.id === nodeId);
    if (!node) return { isInfected: false, severity: 'CLEAN', color: '#10b981', name: 'Nominal Baseline' };

    if (node.isAttacking || node.type === 'attacker') {
      return {
        isInfected: true,
        severity: 'CRITICAL',
        color: '#f43f5e',
        name: 'Adversary Cyber Warfare Injection',
        description: 'Unauthorized host transmitting hostile payloads / port sweep against SCADA infrastructure.',
        rate: node.lastRate || 'Active Attack Vector',
        dominantChannel: 'burst / packet volume surge',
        peakScore: score.toFixed(2),
        cve: 'NTRO PS #26145 / Cyber Threat',
      };
    }

    if (nodeId === 'nuclear-scada') {
      const isTrip = node.state === 'LOSS_OF_FLOW' || (node.flow_kgs && node.flow_kgs < 10000);
      const isLoca = node.state === 'LOCA_ACCIDENT';
      if (isTrip || isLoca) {
        return {
          isInfected: true,
          severity: 'CRITICAL',
          color: '#f43f5e',
          name: isLoca ? 'CRITICAL: LOSS OF COOLANT ACCIDENT' : 'CRITICAL: COOLANT PUMP TRIPPED (LOF)',
          description: isLoca
            ? 'Severe primary circuit depressurization (LOCA transient active).'
            : 'Primary reactor coolant pump tripped via unauthorized command injection. Coolant flow collapsed.',
          rate: 'Physical SCADA Anomaly',
          dominantChannel: 'NPPAD WRCA transient',
          peakScore: Math.max(score, 2.85).toFixed(2),
        };
      }
      return {
        isInfected: false,
        severity: 'NOMINAL',
        color: '#10b981',
        name: '100% Full-Power Nominal Baseline',
        description: 'Kudankulam Unit 1 PWR operating strictly within design basis. Primary coolant flow stable at 16,515 kg/s.',
        rate: 'Routine 1.0s Telemetry',
      };
    }

    if (nodeId === 'njode-core' && score > tau) {
      return {
        isInfected: false,
        isTransitThreat: true,
        severity: 'EVALUATING',
        color: '#f59e0b',
        name: 'Continuous Anomaly Confirmed',
        description: `Latent neural jump-ODE reconstruction error exceeded calibrated threshold τ (${score.toFixed(3)} > ${tau.toFixed(3)}).`,
        rate: 'Continuous Latent Grid',
        peakScore: score.toFixed(2),
      };
    }

    return {
      isInfected: false,
      severity: 'CLEAN',
      color: '#10b981',
      name: 'Verified Physical Simplex',
      description: 'Zero return copper/RF connection. Air-gap integrity 100% guaranteed.',
      rate: 'Passive Simplex Egress',
    };
  };

  // ----------------------------------------------------------------------
  // DYNAMIC NODE REGISTRATION: Handle real packetEvent from backend / scanner
  // ----------------------------------------------------------------------
  useEffect(() => {
    if (!packetEvent) return;
    setLastPacketTime(Date.now());

    const fromId = String(packetEvent.from || 'nuclear-scada').trim();
    const toId = String(packetEvent.to || 'tx-diode').trim();
    const isThreat = Boolean(packetEvent.threat);
    const isDiodeBridge = Boolean(packetEvent.is_diode_bridge);
    const isAlert = Boolean(packetEvent.is_alert);
    const size = packetEvent.size || 128;
    const scada = packetEvent.scada || {};

    // 1. Dynamically ensure `fromId` and `toId` exist in `nodes`
    setNodes(prevNodes => {
      let updated = [...prevNodes];
      let hasChanges = false;

      // Ensure `fromId` exists
      if (!updated.some(n => n.id === fromId)) {
        hasChanges = true;
        const inZoneCount = updated.filter(n => n.zone === 'in-zone').length;
        const isAttacker = isThreat || fromId.toLowerCase().includes('red') || fromId.toLowerCase().includes('attack');
        
        updated.push({
          id: fromId,
          label: isAttacker ? 'Red Team Adversary' : (fromId.includes('node') ? `Node ${fromId}` : fromId),
          sublabel: isAttacker ? 'Offensive Cyber Unit' : 'Connected Substation',
          ip: isAttacker ? '192.168.1.150' : `10.0.1.${20 + inZoneCount}`,
          zone: 'in-zone',
          x: 140,
          y: Math.min(420, 100 + inZoneCount * 90),
          vx: 0,
          vy: 0,
          radius: isAttacker ? 21 : 18,
          type: isAttacker ? 'attacker' : 'device',
          normalRate: 'Live Stream',
          isAttacking: isAttacker,
        });
      }

      // Update SCADA telemetry on `nuclear-scada` if present in event
      const pVal = packetEvent.p ?? packetEvent.pressure_bar ?? scada.p ?? scada.pressure_bar;
      const flowVal = packetEvent.flow ?? packetEvent.coolant_flow_kgs ?? scada.flow ?? scada.coolant_flow_kgs;
      const stateVal = packetEvent.state ?? packetEvent.reactor_state ?? scada.state ?? scada.reactor_state;
      const tempVal = packetEvent.tavg ?? packetEvent.core_temp_c ?? scada.tavg ?? scada.core_temp_c;
      const mwVal = packetEvent.mw ?? packetEvent.output_mwe ?? scada.mw ?? scada.output_mwe;

      if (pVal !== undefined || flowVal !== undefined || stateVal !== undefined) {
        updated = updated.map(n => {
          if (n.id === 'nuclear-scada') {
            return {
              ...n,
              p_bar: pVal !== undefined ? Number(pVal) : n.p_bar,
              flow_kgs: flowVal !== undefined ? Number(flowVal) : n.flow_kgs,
              state: stateVal || n.state,
              tavg_c: tempVal !== undefined ? Number(tempVal) : n.tavg_c,
              mw: mwVal !== undefined ? Number(mwVal) : n.mw,
            };
          }
          return n;
        });
        hasChanges = true;
      }

      return hasChanges ? updated : prevNodes;
    });

    // 2. Dynamically ensure edge exists between `fromId` and `toId`
    setEdges(prevEdges => {
      if (prevEdges.some(e => e.from === fromId && e.to === toId)) {
        return prevEdges;
      }
      return [...prevEdges, {
        from: fromId,
        to: toId,
        isDiodeBridge: isDiodeBridge || fromId === 'tx-diode' || toId === 'optical-gap' || fromId === 'optical-gap' || toId === 'rx-diode',
      }];
    });

    // 3. Spawn real in-flight packet animation
    activeParticlesRef.current.push({
      from: fromId,
      to: toId,
      progress: 0.0,
      speedMultiplier: isThreat ? 1.5 : (isDiodeBridge ? 1.3 : 1.05),
      isThreat: isThreat,
      isDiodeBridge: isDiodeBridge || fromId === 'tx-diode' || toId === 'optical-gap' || fromId === 'optical-gap' || toId === 'rx-diode',
      isAlert: isAlert,
      size: Math.max(2.0, Math.min(3.6, Math.log2(size || 64) * 0.38)),
    });
  }, [packetEvent]);

  // ----------------------------------------------------------------------
  // Canvas Render Loop (Dieter Rams / Minimalist Pure Real Packet Graphics)
  // ----------------------------------------------------------------------
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

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      ctx.save();
      // Apply pan & zoom
      ctx.translate(transform.x, transform.y);
      ctx.scale(transform.k, transform.k);

      // 1. Subtle, clean structural grid
      ctx.strokeStyle = 'rgba(39, 39, 42, 0.30)'; // zinc-800
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
      ctx.fillText('ZONE A  ·  AIR-GAPPED IN-ZONE (SCADA)', 140, 42);

      ctx.textAlign = 'right';
      ctx.fillText('ZONE B  ·  AIR-GAPPED SCANNER SOC', 940, 42);

      ctx.textAlign = 'center';
      ctx.fillStyle = '#a1a1aa';
      ctx.fillText('OPTICAL AIR GAP', 540, 42);
      ctx.font = '9px "JetBrains Mono", monospace';
      ctx.fillStyle = '#52525b';
      ctx.fillText('PHYSICAL SIMPLEX DIODE', 540, 56);

      // 3. Draw Edges between Active Connected Nodes
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
          ctx.setLineDash([6, 3]);
          ctx.strokeStyle = isThreatLine ? '#f43f5e' : '#38bdf8';
          ctx.lineWidth = 1.5;
        } else if (isThreatLine) {
          ctx.setLineDash([]);
          ctx.strokeStyle = 'rgba(244, 63, 94, 0.45)';
          ctx.lineWidth = 1.2;
        } else {
          ctx.setLineDash([]);
          ctx.strokeStyle = 'rgba(39, 39, 42, 0.75)';
          ctx.lineWidth = 1.0;
        }
        ctx.stroke();
        ctx.setLineDash([]);
      });

      // 4. Real Packet Flows: Rendered ONLY when actual packets are actively traversing links
      const particles = activeParticlesRef.current;
      for (let i = particles.length - 1; i >= 0; i--) {
        const p = particles[i];
        const source = nodes.find(n => n.id === p.from);
        const target = nodes.find(n => n.id === p.to);
        if (!source || !target) {
          particles.splice(i, 1);
          continue;
        }

        const dx = target.x - source.x;
        const dy = target.y - source.y;
        const edgeDist = Math.hypot(dx, dy) || 1;

        // Physical velocity
        const pxPerFrame = 1.45 * (p.speedMultiplier || 1.0);
        p.progress += pxPerFrame / edgeDist;

        if (p.progress >= 1.0) {
          particles.splice(i, 1);
          continue;
        }

        const rgb = p.isThreat 
          ? '244, 63, 94' 
          : p.isDiodeBridge 
          ? '56, 189, 248' 
          : '148, 163, 184';

        // Packet Head
        const px0 = source.x + dx * p.progress;
        const py0 = source.y + dy * p.progress;
        ctx.beginPath();
        ctx.arc(px0, py0, p.isThreat ? p.size + 0.8 : p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${rgb}, 0.95)`;
        ctx.fill();

        // Trail Step 1
        const p1 = p.progress - (6 / edgeDist);
        if (p1 >= 0) {
          const px1 = source.x + dx * p1;
          const py1 = source.y + dy * p1;
          ctx.beginPath();
          ctx.arc(px1, py1, p.size * 0.75, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb}, 0.40)`;
          ctx.fill();
        }

        // Trail Step 2
        const p2 = p.progress - (12 / edgeDist);
        if (p2 >= 0) {
          const px2 = source.x + dx * p2;
          const py2 = source.y + dy * p2;
          ctx.beginPath();
          ctx.arc(px2, py2, p.size * 0.45, 0, Math.PI * 2);
          ctx.fillStyle = `rgba(${rgb}, 0.15)`;
          ctx.fill();
        }
      }

      // 5. Draw Connected Nodes
      nodes.forEach((node) => {
        const status = getMalwareStatus(node.id);
        const isHovered = hoveredNode?.id === node.id;
        const isSelected = selectedNode?.id === node.id;

        // Subtle hover / selected ring
        if (isSelected || isHovered) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, node.radius + 4, 0, Math.PI * 2);
          ctx.strokeStyle = 'rgba(212, 212, 216, 0.25)';
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        // Main Node Body
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

        // Minimalist Status Pip
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

        // Live SCADA telemetry badge if nuclear node
        if (node.id === 'nuclear-scada') {
          ctx.font = '9px "JetBrains Mono", monospace';
          ctx.fillStyle = node.state === 'LOSS_OF_FLOW' ? '#f43f5e' : '#38bdf8';
          const p = node.p_bar ? `${node.p_bar}b` : '155.5b';
          const f = node.flow_kgs ? `${Math.round(node.flow_kgs)}kg/s` : '16516kg/s';
          ctx.fillText(`[${p} | ${f}]`, node.x, node.y + node.radius + 37);
        }
      });

      ctx.restore();

      animationId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener('resize', resize);
      if (resizeObserver) resizeObserver.disconnect();
      cancelAnimationFrame(animationId);
    };
  }, [nodes, edges, currentScenario, hoveredNode, selectedNode, transform]);

  // Convert mouse event coordinates to graph world space
  const getWorldCoord = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
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
    const clicked = nodes.find(n => {
      const dx = n.x - x;
      const dy = n.y - y;
      return Math.sqrt(dx * dx + dy * dy) <= n.radius + 6;
    });

    if (clicked) {
      setDraggedNode(clicked);
      setSelectedNode(clicked);
    } else {
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
              Live Connected Topology // Real Optical Diode Mesh
            </h3>
            <p className="text-[11px] text-zinc-400">
              Only active transmitting systems rendered · Zero simulated fake packets · Optical air-gap ingress
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
            <span>{currentScenario !== 'calm' ? 'ANOMALY DETECTED' : 'REAL NETWORK INGESTION ACTIVE'}</span>
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
            {hoveredNode.id === 'nuclear-scada' && (
              <div className="p-1.5 bg-zinc-950 border border-zinc-800 rounded text-sky-300 text-[10px] mt-1.5">
                P: {hoveredNode.p_bar || 155.5} bar · Flow: {Math.round(hoveredNode.flow_kgs || 16516)} kg/s
              </div>
            )}
            <div className="text-[10px] text-zinc-400 mt-2 text-right">
              Click node for live parameters
            </div>
          </div>
        )}

        {/* Legend Overlay at Bottom-Left */}
        <div className="absolute bottom-4 left-4 z-20 p-2.5 rounded-lg bg-zinc-950/90 border border-zinc-800 font-mono text-[11px] space-y-1.5 shadow-md">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-zinc-400">Nominal Telemetry Flow</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span className="text-zinc-400">Cyber Threat / Anomaly</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-sky-400" />
            <span className="text-zinc-400">Simplex Optical Photons</span>
          </div>
        </div>
      </div>

      {/* Forensic / Node Inspector Modal */}
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

            {/* Nuclear SCADA Physical Parameters if Nuclear Node */}
            {selectedNode.id === 'nuclear-scada' && (
              <div className="p-3 bg-zinc-950 border border-zinc-800 rounded-lg mb-3">
                <span className="text-[10px] text-zinc-400 font-medium block mb-2 uppercase tracking-wider">
                  Kudankulam Unit 1 PWR Physical Telemetry (NPPAD Benchmark)
                </span>
                <div className="grid grid-cols-4 gap-2 text-center">
                  <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                    <span className="text-[10px] text-zinc-500 block">PRESSURE</span>
                    <span className="text-xs font-bold text-sky-400">{selectedNode.p_bar || 155.5} bar</span>
                  </div>
                  <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                    <span className="text-[10px] text-zinc-500 block">CORE TEMP</span>
                    <span className="text-xs font-bold text-emerald-400">{selectedNode.tavg_c || 310.0} °C</span>
                  </div>
                  <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                    <span className="text-[10px] text-zinc-500 block">COOLANT FLOW</span>
                    <span className={`text-xs font-bold ${selectedNode.state === 'LOSS_OF_FLOW' ? 'text-rose-400' : 'text-emerald-400'}`}>
                      {Math.round(selectedNode.flow_kgs || 16516)} kg/s
                    </span>
                  </div>
                  <div className="p-2 bg-zinc-900 rounded border border-zinc-800">
                    <span className="text-[10px] text-zinc-500 block">ELECTRICAL</span>
                    <span className="text-xs font-bold text-amber-400">{selectedNode.mw || 955.3} MWe</span>
                  </div>
                </div>
              </div>
            )}

            {/* Diagnostic Metrics Grid */}
            <div className="grid grid-cols-3 gap-2.5 mb-3">
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">CONNECTION TYPE</span>
                <div className="text-xs font-semibold text-zinc-200 mt-1">
                  {selectedNode.zone === 'barrier' ? 'Optical Air-Gap' : (selectedNode.zone === 'in-zone' ? 'Protected LAN' : 'Air-Gapped SOC')}
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">EGRESS CHANNEL</span>
                <div className="text-xs font-semibold text-sky-400 mt-1">
                  {selectedNode.zone.startsWith('diode') || selectedNode.zone === 'barrier' ? 'Optical Photons' : 'Simplex UDP 9999'}
                </div>
              </div>
              <div className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800">
                <span className="text-zinc-400 text-[10px] block">AI ANOMALY SCORE</span>
                <div className="text-xs font-semibold text-emerald-400 mt-1">
                  S_peak: {score.toFixed(2)} / τ: {tau.toFixed(2)}
                </div>
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
