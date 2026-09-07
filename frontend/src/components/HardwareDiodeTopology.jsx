import React, { useState, useEffect, useRef } from 'react';
import { ShieldCheck, Lock, Radio, Cpu, Zap, Camera, Activity, AlertTriangle, RotateCcw, Flame, Gauge, Server } from 'lucide-react';
import PhoneCameraScanner from './PhoneCameraScanner';

export default function HardwareDiodeTopology({ isStreaming, isAttacking, packetRate = 12 }) {
  const [showPhoneScanner, setShowPhoneScanner] = useState(false);
  const canvasRef = useRef(null);

  const [nuclearData, setNuclearData] = useState({
    facility: "BARC / NPCIL Kudankulam Unit 1 (PWR)",
    dataset: "Nature Scientific Data (NPPAD 96-Sensor Benchmark)",
    reactor_state: "NOMINAL_FULL_POWER",
    pressure_bar: 155.5,
    core_temp_c: 310.0,
    coolant_flow_kgs: 16515.8,
    output_mwe: 955.3,
    container_cpu_pct: 1.2,
    container_mem_mb: 22.0,
    container_mem_pct: 2.1,
    last_attack: "None",
  });
  const [actionLoading, setActionLoading] = useState(false);

  // Poll nuclear SCADA telemetry from backend
  useEffect(() => {
    const fetchNuclear = async () => {
      try {
        const res = await fetch('/api/nuclear/status');
        if (res.ok) {
          const json = await res.json();
          if (json.telemetry) {
            setNuclearData(json.telemetry);
          }
        }
      } catch (e) {}
    };

    fetchNuclear();
    const interval = setInterval(fetchNuclear, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleTripPump = async () => {
    setActionLoading(true);
    try {
      const res = await fetch('/api/scada/trip', { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        if (json.telemetry) setNuclearData(json.telemetry);
      }
    } catch (e) {}
    setActionLoading(false);
  };

  const handleResetReactor = async () => {
    setActionLoading(true);
    try {
      const res = await fetch('/api/scada/reset', { method: 'POST' });
      if (res.ok) {
        const json = await res.json();
        if (json.telemetry) setNuclearData(json.telemetry);
      }
    } catch (e) {}
    setActionLoading(false);
  };

  // Animated optical photon flow simulation on canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationId;
    let particles = [];

    let resizeObserver;
    const resize = () => {
      if (canvas.parentElement) {
        canvas.width = canvas.parentElement.clientWidth;
        canvas.height = canvas.parentElement.clientHeight;
      }
    };
    resize();
    window.addEventListener('resize', resize);
    if (canvas.parentElement && typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(canvas.parentElement);
    }

    // Constant-velocity particle generator
    const spawnRate = isAttacking ? 4 : (isStreaming ? 1.5 : 0.4);
    const particleSpeed = 2.5; // Steady, non-racing speed

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      if (Math.random() < spawnRate * 0.12) {
        particles.push({
          x: canvas.width * 0.20,
          y: canvas.height * 0.50 + (Math.random() - 0.5) * 12,
          vx: particleSpeed,
          vy: 0,
          size: 2.0,
          color: isAttacking ? '#f43f5e' : '#38bdf8',
          trail: []
        });
      }

      // Update and draw particles
      particles.forEach((p, idx) => {
        p.trail.push({ x: p.x, y: p.y });
        if (p.trail.length > 6) p.trail.shift();

        p.x += p.vx;

        // Draw crisp laser trail (no heavy blur)
        for (let i = 0; i < p.trail.length - 1; i++) {
          ctx.beginPath();
          ctx.strokeStyle = p.color;
          ctx.globalAlpha = (i / p.trail.length) * 0.45;
          ctx.lineWidth = 1.2;
          ctx.moveTo(p.trail[i].x, p.trail[i].y);
          ctx.lineTo(p.trail[i + 1].x, p.trail[i + 1].y);
          ctx.stroke();
        }

        // Draw photon head
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
        ctx.fillStyle = p.color;
        ctx.globalAlpha = 0.9;
        ctx.fill();

        // Destination reached
        if (p.x > canvas.width * 0.82) {
          particles.splice(idx, 1);
        }
      });

      ctx.globalAlpha = 1.0;
      animationId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resize);
      if (resizeObserver) resizeObserver.disconnect();
      cancelAnimationFrame(animationId);
    };
  }, [isStreaming, isAttacking]);

  const isTrip = nuclearData.reactor_state === 'LOSS_OF_FLOW';

  return (
    <div className="relative rounded-xl border border-zinc-800 bg-[#090a0f] overflow-y-auto h-full flex flex-col min-h-0 space-y-3 p-3">
      {/* Top Banner Ribbon */}
      <div className="flex items-center justify-between px-4 py-2.5 rounded-lg border border-zinc-800 bg-zinc-950/80 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Radio className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Hardware Simplex Data Diode Architecture
            </h3>
            <p className="text-[11px] text-zinc-400">
              Galvanic air-gap isolation · Unidirectional laser transmitter to photodiode detector
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowPhoneScanner(true)}
            className="flex items-center gap-1.5 px-3 py-1 rounded-md bg-emerald-950/80 border border-emerald-600/70 text-emerald-400 hover:bg-emerald-900 text-xs font-mono transition-colors shadow-sm cursor-pointer"
          >
            <Camera className="w-3.5 h-3.5 animate-pulse" />
            <span>📱 LIVE PHONE CAM SCANNER</span>
          </button>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-emerald-400 text-xs font-mono">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>0.00% REVERSE FLOW</span>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 text-xs font-mono">
            <Zap className="w-3.5 h-3.5 text-sky-400" />
            <span>INFERENCE: 1.1ms</span>
          </div>
        </div>
      </div>

      {/* Main Visual Frame with Embedded Image and Canvas Overlay */}
      <div className="relative h-56 sm:h-64 w-full rounded-xl bg-[#07090e] border border-zinc-800 overflow-hidden flex items-center justify-center flex-shrink-0">
        {/* Hardware Schematic Image */}
        <img
          src="/assets/hardware_data_diode.jpg"
          alt="Hardware Optical Data Diode Schematic"
          className="w-full h-full object-cover object-center opacity-75 filter brightness-90 contrast-110"
        />

        {/* Dynamic Canvas for Real-time Optical Photons */}
        <canvas
          ref={canvasRef}
          className="absolute inset-0 pointer-events-none z-10 w-full h-full"
        />

        {/* Subtle vignette */}
        <div className="absolute inset-0 bg-gradient-to-t from-[#090a0f] via-transparent to-[#090a0f]/40 pointer-events-none" />
        <div className="absolute inset-0 bg-gradient-to-r from-[#090a0f]/80 via-transparent to-[#090a0f]/80 pointer-events-none" />

        {/* Node Labels Overlaid */}
        <div className="absolute left-4 top-4 z-20 flex flex-col gap-1 p-2.5 rounded-lg bg-zinc-950/90 border border-zinc-800 font-mono text-xs max-w-xs shadow-md">
          <div className="flex items-center gap-1.5 text-zinc-200 font-semibold text-[11px]">
            <Lock className="w-3.5 h-3.5 text-emerald-400" />
            <span>ZONE A · IN-ZONE HIGH SECURITY</span>
          </div>
          <p className="text-[10px] text-zinc-400">
            Protected air-gapped industrial SCADA network. Generates telemetry &amp; unacknowledged UDP datagrams.
          </p>
        </div>

        <div className="absolute right-4 bottom-4 z-20 flex flex-col gap-1 p-2.5 rounded-lg bg-zinc-950/90 border border-zinc-800 font-mono text-xs max-w-xs shadow-md">
          <div className="flex items-center gap-1.5 text-zinc-200 font-semibold text-[11px]">
            <Cpu className="w-3.5 h-3.5 text-sky-400" />
            <span>ZONE B · CHRONOS SCANNER SIDE</span>
          </div>
          <p className="text-[10px] text-zinc-400">
            Photodiode receiver captures packet timing &amp; features into continuous Neural Jump-ODE core.
          </p>
        </div>

        {/* Center Transmission Pulse */}
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-3 py-1 rounded-md bg-zinc-950/90 border border-zinc-800 text-zinc-300 font-mono text-xs flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${isTrip || isAttacking ? 'bg-rose-500 animate-ping' : 'bg-emerald-400'}`}></span>
          <span>OPTICAL SIMPLEX: {isTrip || isAttacking ? 'ANOMALOUS BURST' : 'PASSIVE MONITORING'}</span>
        </div>
      </div>

      {/* Interactive Bottom Stat Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-zinc-800/80 rounded-lg border border-zinc-800 bg-zinc-950 text-xs font-mono flex-shrink-0">
        <div className="p-2.5 flex items-center justify-between">
          <span className="text-zinc-400">Medium:</span>
          <span className="text-zinc-200 font-medium">Single-Mode Fiber</span>
        </div>
        <div className="p-2.5 flex items-center justify-between">
          <span className="text-zinc-400">Isolation:</span>
          <span className="text-zinc-200 font-medium">Class-1 Simplex Laser</span>
        </div>
        <div className="p-2.5 flex items-center justify-between">
          <span className="text-zinc-400">Transport:</span>
          <span className="text-zinc-200 font-medium">Simplex UDP / QR Diode</span>
        </div>
        <div className="p-2.5 flex items-center justify-between">
          <span className="text-zinc-400">Reverse Path:</span>
          <span className="text-emerald-400 font-medium">Physically None (0 dB)</span>
        </div>
      </div>

      {/* Kudankulam Unit 1 NPPAD Nuclear SCADA Digital Twin & Resource HUD */}
      <div className="rounded-xl border border-zinc-800 bg-[#06080e] p-4 font-mono text-xs space-y-3 flex-shrink-0 shadow-lg">
        {/* Header & Status Indicator */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800/80 pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-sky-950/70 border border-sky-600/50 text-sky-400">
              <Activity className="w-4 h-4 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-xs font-bold text-zinc-100 uppercase tracking-wider">
                  Kudankulam Unit 1 (PWR) · Nuclear SCADA Digital Twin
                </h4>
                <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-900 border border-zinc-800 text-zinc-400">
                  NPPAD Benchmark (Nature 2022)
                </span>
              </div>
              <p className="text-[11px] text-zinc-400">
                Live primary coolant loop physics &amp; container resource tracking across optical air gap
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider border ${
              isTrip
                ? 'bg-rose-950/80 border-rose-600 text-rose-300 animate-pulse'
                : 'bg-emerald-950/80 border-emerald-600 text-emerald-300'
            }`}>
              {isTrip ? '🚨 LOSS OF FLOW (PUMP TRIP)' : '✅ NOMINAL FULL POWER'}
            </span>

            {/* Attack Injection Controls */}
            <button
              onClick={handleTripPump}
              disabled={actionLoading || isTrip}
              className={`px-3 py-1 rounded border text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer ${
                isTrip
                  ? 'bg-zinc-900 border-zinc-800 text-zinc-600 cursor-not-allowed'
                  : 'bg-rose-950/80 border-rose-600 text-rose-300 hover:bg-rose-900'
              }`}
              title="Inject unauthorized Modbus FC05 coil write to trip reactor coolant pump"
            >
              <Flame className="w-3.5 h-3.5" />
              <span>TRIP PUMP (MODBUS FC05)</span>
            </button>

            <button
              onClick={handleResetReactor}
              disabled={actionLoading || !isTrip}
              className={`px-3 py-1 rounded border text-xs font-bold flex items-center gap-1.5 transition-colors cursor-pointer ${
                !isTrip
                  ? 'bg-zinc-900 border-zinc-800 text-zinc-600 cursor-not-allowed'
                  : 'bg-emerald-950/80 border-emerald-600 text-emerald-300 hover:bg-emerald-900'
              }`}
              title="Reset Kudankulam reactor physics to 100% nominal baseline"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>RESTORE BASELINE</span>
            </button>
          </div>
        </div>

        {/* 4 Primary Reactor Physics Gauges */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
          {/* Gauge 1: Primary Coolant Pressure */}
          <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
            <div className="flex items-center justify-between text-[11px] text-zinc-400">
              <span className="flex items-center gap-1"><Gauge className="w-3.5 h-3.5 text-sky-400" /> Pressure (P)</span>
              <span className="text-[10px] text-zinc-500">Nominal 155.5 bar</span>
            </div>
            <div className="text-lg font-bold text-zinc-100 flex items-baseline gap-1">
              <span>{nuclearData.pressure_bar.toFixed(1)}</span>
              <span className="text-xs text-zinc-400 font-normal">bar</span>
            </div>
            <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-sky-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min((nuclearData.pressure_bar / 180) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Gauge 2: Core Average Temp */}
          <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
            <div className="flex items-center justify-between text-[11px] text-zinc-400">
              <span className="flex items-center gap-1"><Activity className="w-3.5 h-3.5 text-amber-400" /> Core Temp (Tavg)</span>
              <span className="text-[10px] text-zinc-500">Nominal 310.0 °C</span>
            </div>
            <div className="text-lg font-bold text-amber-300 flex items-baseline gap-1">
              <span>{nuclearData.core_temp_c.toFixed(1)}</span>
              <span className="text-xs text-zinc-400 font-normal">°C</span>
            </div>
            <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-amber-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min((nuclearData.core_temp_c / 350) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Gauge 3: Coolant Flow Rate WRCA */}
          <div className={`p-3 rounded-lg bg-zinc-950 border space-y-1 transition-colors ${
            isTrip ? 'border-rose-600/80 bg-rose-950/20' : 'border-zinc-800/80'
          }`}>
            <div className="flex items-center justify-between text-[11px] text-zinc-400">
              <span className="flex items-center gap-1"><Radio className="w-3.5 h-3.5 text-emerald-400" /> Coolant Flow (WRCA)</span>
              <span className="text-[10px] text-zinc-500">Nominal 16,516 kg/s</span>
            </div>
            <div className={`text-lg font-bold flex items-baseline gap-1 ${
              isTrip ? 'text-rose-400 animate-pulse' : 'text-emerald-400'
            }`}>
              <span>{nuclearData.coolant_flow_kgs.toLocaleString()}</span>
              <span className="text-xs text-zinc-400 font-normal">kg/s</span>
            </div>
            <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${isTrip ? 'bg-rose-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min((nuclearData.coolant_flow_kgs / 18000) * 100, 100)}%` }}
              />
            </div>
          </div>

          {/* Gauge 4: Electric Grid Power */}
          <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
            <div className="flex items-center justify-between text-[11px] text-zinc-400">
              <span className="flex items-center gap-1"><Zap className="w-3.5 h-3.5 text-purple-400" /> Grid Output</span>
              <span className="text-[10px] text-zinc-500">Rated 1000 MWe</span>
            </div>
            <div className="text-lg font-bold text-purple-300 flex items-baseline gap-1">
              <span>{nuclearData.output_mwe.toFixed(1)}</span>
              <span className="text-xs text-zinc-400 font-normal">MWe</span>
            </div>
            <div className="w-full bg-zinc-900 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-purple-500 h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min((nuclearData.output_mwe / 1000) * 100, 100)}%` }}
              />
            </div>
          </div>
        </div>

        {/* Cgroups v2 Container Hardware Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5 pt-1 text-[11px]">
          <div className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 flex items-center justify-between">
            <span className="text-zinc-400 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-sky-400" /> SCADA CPU Core Load:
            </span>
            <span className="font-bold text-zinc-200">
              {nuclearData.container_cpu_pct.toFixed(1)}% <span className="text-zinc-500 font-normal">(1.0 core limit)</span>
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 flex items-center justify-between">
            <span className="text-zinc-400 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-emerald-400" /> SCADA RAM Allocated:
            </span>
            <span className="font-bold text-zinc-200">
              {nuclearData.container_mem_mb.toFixed(1)} MB <span className="text-zinc-500 font-normal">(1024 MB limit)</span>
            </span>
          </div>

          <div className="p-2.5 rounded-lg bg-zinc-950/80 border border-zinc-800/80 flex items-center justify-between">
            <span className="text-zinc-400 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Active Threat State:
            </span>
            <span className={`font-bold ${nuclearData.last_attack !== 'None' ? 'text-amber-300' : 'text-zinc-400'}`}>
              {nuclearData.last_attack}
            </span>
          </div>
        </div>
      </div>

      {showPhoneScanner && (
        <PhoneCameraScanner onClose={() => setShowPhoneScanner(false)} />
      )}
    </div>
  );
}
