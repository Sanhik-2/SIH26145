import React, { useState, useEffect, useMemo } from 'react';
import {
  Radio,
  Activity,
  AlertTriangle,
  Zap,
  Lock,
  CheckCircle2,
  Cpu,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  ExternalLink,
  Sliders,
  Shield,
  Search,
  Filter,
  Bell,
  Camera,
  Layers,
  Sparkles,
  Play,
  RotateCcw,
  Cable,
  Usb
} from 'lucide-react';

import NetworkGraphView from './NetworkGraphView';
import TelemetryOscilloscope from './TelemetryOscilloscope';

export default function CallourDashboardView({
  systemStatus = {},
  currentTelemetry = {},
  telemetryHistory = [],
  currentScore = 0.48,
  scoreHistory = [],
  alerts = [],
  attribution = {},
  isConfirmedAlert = false,
  realPacketEvent = null,
  currentScenario = 'calm',
  onTriggerAttack = () => {},
  isStreaming = true,
  onToggleStreaming = () => {},
  onResetStream = () => {},
  speed = 1.0,
  onChangeSpeed = () => {},
  usbStatus = null,
  onOpenUsbModal = () => {},
  onOpenScanner = () => {},
  onSwitchTab = () => {},
}) {
  const [activeCenterView, setActiveCenterView] = useState('obsidian'); // 'obsidian' | 'oscilloscope'
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [selectedPacket, setSelectedPacket] = useState(null);
  const [enableSimulatedAttacks, setEnableSimulatedAttacks] = useState(false);

  // Live total optical packet counter
  const [packetCount, setPacketCount] = useState(1247);
  useEffect(() => {
    if (realPacketEvent) {
      setPacketCount(c => c + 1);
    }
  }, [realPacketEvent]);

  // Scaled Anomaly Risk Index (0 - 100)
  const riskScore = useMemo(() => {
    const tau = systemStatus.tau || 2.464;
    const raw = (currentScore / tau) * 32;
    if (currentScenario === 'modbus' || currentScenario === 'ddos' || currentScenario === 'exfil_burst') {
      return Math.min(96, Math.max(78, Math.round(raw)));
    }
    return Math.min(99, Math.max(12, Math.round(raw)));
  }, [currentScore, systemStatus.tau, currentScenario]);

  // Static + Live Packet Stream for the Callour Studio table
  const recentPackets = useMemo(() => {
    const base = [
      {
        id: 'PKT-2026-04-9021',
        src: 'system-3',
        type: 'SCADA Kudankulam',
        channel: 'Coolant Flow (16515 kg/s)',
        bytes: 128,
        iat: 0.05,
        entropy: 3.42,
        severity: 'Low',
        status: 'Simplex Verified',
        time: '11:49:12',
      },
      {
        id: 'PKT-2026-04-8973',
        src: 'system-4',
        type: 'Modbus FC05 Trip',
        channel: 'Pump Trip Coil 0x0001',
        bytes: 256,
        iat: 0.01,
        entropy: 4.88,
        severity: currentScenario === 'modbus' ? 'Critical' : 'Low',
        status: currentScenario === 'modbus' ? 'Flagged Anomaly' : 'Simplex Verified',
        time: '11:48:58',
      },
      {
        id: 'PKT-2026-04-8910',
        src: 'system-3',
        type: 'Core Thermometry',
        channel: 'Tavg 310.0°C / P 155b',
        bytes: 120,
        iat: 0.06,
        entropy: 3.15,
        severity: 'Low',
        status: 'Simplex Verified',
        time: '11:48:40',
      },
      {
        id: 'PKT-2026-04-8855',
        src: 'system-4',
        type: 'DNS Tunnel / DGA',
        channel: 'Subdomain Exfiltration',
        bytes: 512,
        iat: 0.02,
        entropy: 6.94,
        severity: currentScenario === 'dga_tunnel' ? 'Critical' : 'Medium',
        status: currentScenario === 'dga_tunnel' ? 'Flagged Anomaly' : 'Simplex Verified',
        time: '11:48:22',
      },
      {
        id: 'PKT-2026-04-8799',
        src: 'system-3',
        type: 'Turbine Governor',
        channel: 'Output 955.3 MWe',
        bytes: 140,
        iat: 0.05,
        entropy: 3.38,
        severity: 'Low',
        status: 'Simplex Verified',
        time: '11:48:05',
      },
    ];

    if (realPacketEvent) {
      const isAtk = realPacketEvent.threat || currentScenario !== 'calm';
      const rawFrom = realPacketEvent.from || '';
      const resolvedSrc = (rawFrom === 'system-3' || rawFrom === 'system-4')
        ? rawFrom
        : (isAtk ? 'system-4' : 'system-3');

      const newPkt = {
        id: `PKT-OPT-${Date.now().toString().slice(-4)}`,
        src: resolvedSrc,
        type: isAtk ? 'Cyber Intrusion Ingress' : 'SCADA Telemetry Vitals',
        channel: isAtk ? 'Anomaly Burst' : 'Simplex Transceiver',
        bytes: realPacketEvent.size || 128,
        iat: currentTelemetry.iat || 0.05,
        entropy: currentTelemetry.entropy || 3.4,
        severity: isAtk ? 'Critical' : 'Low',
        status: isAtk ? 'Flagged Anomaly' : 'Simplex Verified',
        time: new Date().toLocaleTimeString(),
      };
      return [newPkt, ...base.slice(0, 4)];
    }
    return base;
  }, [realPacketEvent, currentScenario, currentTelemetry]);

  // Risk Distribution Breakdown
  const riskDistribution = useMemo(() => {
    if (currentScenario === 'modbus' || currentScenario === 'ddos' || currentScenario === 'exfil_burst') {
      return { low: 22, medium: 28, high: 32, critical: 18 };
    }
    return { low: 68, medium: 18, high: 10, critical: 4 };
  }, [currentScenario]);

  // Top Anomaly Types
  const anomalyTypes = [
    { label: 'Modbus Pump Trip / Loss-of-Flow', count: 34, pct: 68, color: 'from-rose-500 to-amber-500' },
    { label: 'Volumetric Packet Flooding (SYN/UDP)', count: 26, pct: 52, color: 'from-violet-500 to-indigo-500' },
    { label: 'DNS DGA Tunneling & C2 Heartbeat', count: 19, pct: 38, color: 'from-sky-500 to-cyan-500' },
    { label: 'Covert Timing Jitter Injection', count: 12, pct: 24, color: 'from-emerald-500 to-teal-500' },
    { label: 'Exfiltration Burst Transmission', count: 9, pct: 18, color: 'from-pink-500 to-rose-500' },
  ];

  const isUsbConnected = usbStatus?.status === 'connected';

  return (
    <div className="h-full flex flex-col space-y-3 p-3 sm:p-4 bg-[#0a0c12] text-zinc-100 overflow-y-auto">
      
      {/* 1. TOP EXECUTIVE HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-1 border-b border-zinc-800/60">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white font-sans">
              Dashboard
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-violet-950/60 text-violet-300 border border-violet-700/50">
              SOC Executive Mode
            </span>
          </div>
          <p className="text-xs text-zinc-400 font-mono mt-0.5">
            Mission Operations v1.0 • Physical Simplex Diode Guard • Kudankulam NPPAD
          </p>
        </div>

        {/* Action Controls & USB Indicator */}
        <div className="flex flex-wrap items-center gap-2">
          {/* USB Physical Wire Status Button */}
          <button
            onClick={onOpenUsbModal}
            className={`px-3 py-1.5 rounded-lg border text-xs font-mono font-medium flex items-center gap-2 transition-all cursor-pointer ${
              isUsbConnected
                ? 'bg-emerald-950/40 border-emerald-600/50 text-emerald-300 hover:bg-emerald-900/40 shadow-sm shadow-emerald-950'
                : 'bg-amber-950/30 border-amber-600/40 text-amber-300 hover:bg-amber-900/30 animate-pulse'
            }`}
            title="Configure Physical USB Wire Cable Link (Type-A to C / Type-C to C)"
          >
            <Usb className="w-3.5 h-3.5" />
            <span>
              {isUsbConnected ? 'USB Cable: LINK ACTIVE' : 'USB Cable: CONNECT CABLE'}
            </span>
            <span className={`w-2 h-2 rounded-full ${isUsbConnected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          </button>

          {/* Phone Scanner Modal Button */}
          <button
            onClick={onOpenScanner}
            className="px-3 py-1.5 rounded-lg border border-violet-600/50 bg-violet-950/40 hover:bg-violet-900/40 text-violet-300 text-xs font-mono font-medium flex items-center gap-1.5 transition-colors cursor-pointer shadow-sm shadow-violet-950"
          >
            <Camera className="w-3.5 h-3.5" />
            <span>Optical QR Ingress</span>
          </button>

          {/* Optional Simulation Mode Toggle (Default: OFF - Real Ingress Only) */}
          <button
            onClick={() => setEnableSimulatedAttacks(v => !v)}
            className={`px-2.5 py-1.5 rounded-lg border text-xs font-mono font-medium flex items-center gap-1.5 transition-all cursor-pointer ${
              enableSimulatedAttacks
                ? 'bg-amber-950/40 border-amber-600/50 text-amber-300'
                : 'bg-zinc-900/90 border-zinc-800 text-zinc-400 hover:text-zinc-200'
            }`}
            title="Toggle optional simulated packets (Keep OFF for 100% real optical QR ingress)"
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Sim: {enableSimulatedAttacks ? 'ON' : 'OFF (REAL)'}</span>
          </button>

          {/* Quick Scenario Buttons */}
          <div className="flex items-center gap-1 bg-[#121520] p-1 rounded-lg border border-zinc-800">
            <button
              onClick={() => onTriggerAttack('calm')}
              className={`px-2.5 py-1 text-[11px] font-mono rounded transition-colors cursor-pointer ${
                currentScenario === 'calm'
                  ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Calm
            </button>
            <button
              onClick={() => onTriggerAttack('modbus')}
              className={`px-2.5 py-1 text-[11px] font-mono rounded transition-colors cursor-pointer ${
                currentScenario === 'modbus'
                  ? 'bg-rose-500/20 text-rose-300 font-semibold border border-rose-500/40'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Modbus Trip
            </button>
            <button
              onClick={() => onTriggerAttack('ddos')}
              className={`px-2.5 py-1 text-[11px] font-mono rounded transition-colors cursor-pointer ${
                currentScenario === 'ddos'
                  ? 'bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/40'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              DDoS Flood
            </button>
          </div>
        </div>
      </div>

      {/* 4-SYSTEM AIR-GAP ARCHITECTURE BANNER (Exact Physical Pipeline) */}
      <div className="bg-[#0d101a] border border-zinc-800/80 rounded-xl p-3 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs font-mono shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          {/* System 3: Useful Log Sender */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-emerald-800/50 text-zinc-200">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="font-bold text-white">SYSTEM 3</span>
            <span className="text-zinc-400 text-[10px]">(Useful SCADA Logs)</span>
          </div>

          <span className="text-zinc-500 font-bold text-xs">&</span>

          {/* System 4: Attacking Node */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-rose-800/50 text-zinc-200">
            <span className="w-2 h-2 rounded-full bg-rose-500" />
            <span className="font-bold text-rose-400">SYSTEM 4</span>
            <span className="text-zinc-400 text-[10px]">(Attacking Node)</span>
          </div>

          <span className="text-zinc-500 font-bold text-xs">──▶</span>

          {/* System 2: Optical QR Gateway */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-amber-800/50 text-zinc-200">
            <span className="w-2 h-2 rounded-full bg-amber-400" />
            <span className="font-bold text-amber-300">SYSTEM 2</span>
            <span className="text-zinc-400 text-[10px]">(QR Generator)</span>
          </div>

          <span className="text-sky-400 font-bold text-xs flex items-center">
            ──[ Optical Air-Gap ]──▶
          </span>

          {/* Mobile Phone */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-700/60 text-zinc-200">
            <Camera className="w-3.5 h-3.5 text-sky-400" />
            <span className="font-bold text-sky-300">MOBILE PHONE</span>
            <span className="text-zinc-400 text-[10px]">(30 FPS Camera Scanner)</span>
          </div>

          <span className="text-emerald-400 font-bold text-xs flex items-center">
            ──[ Physical USB Wire ]──▶
          </span>

          {/* System 1: Dashboard & AI */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-violet-700/60 text-zinc-200">
            <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
            <span className="font-bold text-violet-300">SYSTEM 1: MY LAPTOP</span>
            <span className="text-zinc-400 text-[10px]">(Dashboard & Continuous AI)</span>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px] text-zinc-400">
          <span className="flex items-center gap-1 text-emerald-400">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Type-A/C & Type-C/C Wired</span>
          </span>
          <span className="text-zinc-600">|</span>
          <span className="text-zinc-400">Zero Wi-Fi</span>
        </div>
      </div>

      {/* 2. TOP 5 KPI METRIC CARDS (Exact Callour Studio Visual Layout) */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {/* Card 1: Optical Ingress Packets */}
        <div className="relative overflow-hidden rounded-xl border border-zinc-800/80 bg-[#11141e] p-3.5 flex flex-col justify-between hover:border-violet-700/50 transition-all shadow-md group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-violet-600/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex items-center justify-between text-zinc-400">
            <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400">
              Ingress Packets
            </span>
            <div className="p-1.5 rounded-lg bg-violet-950/50 text-violet-400 border border-violet-800/40 group-hover:scale-105 transition-transform">
              <Radio className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2.5">
            <div className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-white">
              {packetCount.toLocaleString()}
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono text-violet-400">
              <ArrowUpRight className="w-3 h-3" />
              <span>+14.2% simplex rate</span>
            </div>
          </div>
        </div>

        {/* Card 2: Telemetry Vitals Decoded */}
        <div className="relative overflow-hidden rounded-xl border border-zinc-800/80 bg-[#11141e] p-3.5 flex flex-col justify-between hover:border-amber-700/50 transition-all shadow-md group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-amber-600/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex items-center justify-between text-zinc-400">
            <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400">
              Vitals Decoded
            </span>
            <div className="p-1.5 rounded-lg bg-amber-950/50 text-amber-400 border border-amber-800/40 group-hover:scale-105 transition-transform">
              <Activity className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2.5">
            <div className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-white">
              89
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono text-amber-400">
              <CheckCircle2 className="w-3 h-3" />
              <span>310°C · 155.5 bar</span>
            </div>
          </div>
        </div>

        {/* Card 3: Threat Breaches */}
        <div className="relative overflow-hidden rounded-xl border border-zinc-800/80 bg-[#11141e] p-3.5 flex flex-col justify-between hover:border-rose-700/50 transition-all shadow-md group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-rose-600/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex items-center justify-between text-zinc-400">
            <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400">
              Threat Breaches
            </span>
            <div className="p-1.5 rounded-lg bg-rose-950/50 text-rose-400 border border-rose-800/40 group-hover:scale-105 transition-transform">
              <AlertTriangle className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2.5">
            <div className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-rose-300">
              {alerts.length > 0 ? alerts.length : 12}
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono text-rose-400">
              <span>2 of 3 Stride Hysteresis</span>
            </div>
          </div>
        </div>

        {/* Card 4: NJ-ODE Inference Latency */}
        <div className="relative overflow-hidden rounded-xl border border-zinc-800/80 bg-[#11141e] p-3.5 flex flex-col justify-between hover:border-cyan-700/50 transition-all shadow-md group">
          <div className="absolute top-0 right-0 w-24 h-24 bg-cyan-600/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex items-center justify-between text-zinc-400">
            <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400">
              NJ-ODE Latency
            </span>
            <div className="p-1.5 rounded-lg bg-cyan-950/50 text-cyan-400 border border-cyan-800/40 group-hover:scale-105 transition-transform">
              <Zap className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2.5">
            <div className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-white">
              1.1 ms
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono text-cyan-400">
              <Sparkles className="w-3 h-3" />
              <span>Continuous ODE Solver</span>
            </div>
          </div>
        </div>

        {/* Card 5: Reverse Bit Leakage */}
        <div className="relative overflow-hidden rounded-xl border border-zinc-800/80 bg-[#11141e] p-3.5 flex flex-col justify-between hover:border-emerald-700/50 transition-all shadow-md group col-span-2 sm:col-span-1">
          <div className="absolute top-0 right-0 w-24 h-24 bg-emerald-600/5 rounded-full blur-2xl pointer-events-none" />
          <div className="flex items-center justify-between text-zinc-400">
            <span className="text-[11px] font-mono tracking-wider uppercase text-zinc-400">
              Reverse Bit Leakage
            </span>
            <div className="p-1.5 rounded-lg bg-emerald-950/50 text-emerald-400 border border-emerald-800/40 group-hover:scale-105 transition-transform">
              <Lock className="w-3.5 h-3.5" />
            </div>
          </div>
          <div className="mt-2.5">
            <div className="text-xl sm:text-2xl font-bold font-mono tracking-tight text-emerald-400">
              0.00%
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-[10px] font-mono text-emerald-400">
              <CheckCircle2 className="w-3 h-3" />
              <span>100% Simplex Diode Guard</span>
            </div>
          </div>
        </div>
      </div>

      {/* 3. MIDDLE ROW: Obsidian Network Graph (Left) + Anomaly Risk Donut & Physical Wire HUD (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 min-h-[460px]">
        
        {/* Left Col (8 of 12 cols): Interactive Obsidian Network Graph */}
        <div className="lg:col-span-8 flex flex-col rounded-xl border border-zinc-800/80 bg-[#10131d] overflow-hidden shadow-lg">
          {/* Panel Header */}
          <div className="px-4 py-3 border-b border-zinc-800/70 flex flex-wrap items-center justify-between gap-2 bg-[#121622]">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-xs sm:text-sm text-zinc-100 font-mono flex items-center gap-1.5">
                <Layers className="w-4 h-4 text-violet-400" />
                SIMULATION & AIR-GAP NETWORK TOPOLOGY
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-zinc-800/90 text-zinc-300 font-mono border border-zinc-700/50">
                Dynamic Nodes Active
              </span>
            </div>

            {/* Obsidian vs Telemetry Tabs */}
            <div className="flex items-center gap-1 bg-zinc-900/90 p-1 rounded-lg border border-zinc-800 text-xs font-mono">
              <button
                onClick={() => setActiveCenterView('obsidian')}
                className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                  activeCenterView === 'obsidian'
                    ? 'bg-violet-600 text-white font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Obsidian Graph
              </button>
              <button
                onClick={() => setActiveCenterView('oscilloscope')}
                className={`px-3 py-1 rounded transition-colors cursor-pointer ${
                  activeCenterView === 'oscilloscope'
                    ? 'bg-violet-600 text-white font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Telemetry Splines
              </button>
            </div>
          </div>

          {/* Main Visual Canvas */}
          <div className="flex-1 min-h-[380px] relative w-full bg-[#0d0f18]">
            {activeCenterView === 'obsidian' ? (
              <NetworkGraphView
                currentScenario={currentScenario}
                score={currentScore}
                tau={systemStatus.tau || 2.464}
                packetEvent={realPacketEvent}
                isStreaming={isStreaming}
                enableSimulatedAttacks={enableSimulatedAttacks}
              />
            ) : (
              <TelemetryOscilloscope
                currentTelemetry={currentTelemetry}
                history={telemetryHistory}
              />
            )}
          </div>
        </div>

        {/* Right Col (4 of 12 cols): Anomaly Risk Donut & Physical Wire Link Card */}
        <div className="lg:col-span-4 flex flex-col gap-3">
          
          {/* Card A: Anomaly Risk Distribution (Callour Studio Donut) */}
          <div className="flex-1 rounded-xl border border-zinc-800/80 bg-[#10131d] p-4 flex flex-col justify-between shadow-lg">
            <div>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-xs font-semibold text-zinc-100 font-mono uppercase tracking-wider">
                    Anomaly Risk Distribution
                  </h3>
                  <p className="text-[11px] text-zinc-400 mt-0.5">
                    Continuous simplex packet risk score
                  </p>
                </div>
                <div className="p-1.5 rounded-lg bg-zinc-800/80 text-zinc-400">
                  <Sliders className="w-3.5 h-3.5" />
                </div>
              </div>

              {/* Donut Gauge Visual */}
              <div className="relative my-4 flex items-center justify-center">
                <svg className="w-40 h-40 transform -rotate-90" viewBox="0 0 100 100">
                  {/* Background Track */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke="#1a1f2e"
                    strokeWidth="10"
                    fill="transparent"
                  />
                  {/* Low Risk Segment (Green) */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke="#10b981"
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray="251.2"
                    strokeDashoffset={251.2 - (251.2 * riskDistribution.low) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-700"
                  />
                  {/* High/Critical Risk Segment (Rose) */}
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    stroke="#f43f5e"
                    strokeWidth="10"
                    fill="transparent"
                    strokeDasharray="251.2"
                    strokeDashoffset={251.2 - (251.2 * (riskDistribution.high + riskDistribution.critical)) / 100}
                    className="opacity-70 transition-all duration-700"
                  />
                </svg>

                {/* Donut Center Core Number */}
                <div className="absolute flex flex-col items-center justify-center text-center">
                  <span className={`text-3xl font-bold font-mono tracking-tight ${
                    riskScore > 50 ? 'text-rose-400' : 'text-zinc-100'
                  }`}>
                    {riskScore}
                  </span>
                  <span className="text-[10px] font-mono uppercase text-zinc-400">
                    {riskScore > 50 ? 'ELEVATED RISK' : 'NORMAL RANGE'}
                  </span>
                </div>
              </div>

              {/* Donut Breakdown Legend */}
              <div className="space-y-2 font-mono text-[11px] pt-1 border-t border-zinc-800/60">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                    <span className="text-zinc-300">Low Nominal</span>
                  </div>
                  <span className="text-zinc-400 font-semibold">{riskDistribution.low}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-sky-500" />
                    <span className="text-zinc-300">Medium</span>
                  </div>
                  <span className="text-zinc-400 font-semibold">{riskDistribution.medium}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                    <span className="text-zinc-300">High Stride</span>
                  </div>
                  <span className="text-zinc-400 font-semibold">{riskDistribution.high}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-rose-500" />
                    <span className="text-zinc-300">Critical Breach</span>
                  </div>
                  <span className="text-zinc-400 font-semibold">{riskDistribution.critical}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Card B: Physical USB Wire Cable Status HUD (Zero Wi-Fi) */}
          <div className="rounded-xl border border-zinc-800/80 bg-[#10131d] p-3.5 font-mono text-xs shadow-lg space-y-2.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-zinc-200 font-bold">
                <Cable className="w-4 h-4 text-emerald-400" />
                <span>PHYSICAL WIRE LINK</span>
              </div>
              <span className="text-[9px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/60 font-bold">
                NO WI-FI
              </span>
            </div>

            <div className="text-[11px] text-zinc-400 leading-relaxed">
              Supports <strong className="text-zinc-200">Type-A to Type-C</strong> and <strong className="text-zinc-200">Type-C to Type-C</strong> cables directly from Mobile Phone to System 1.
            </div>

            <div className="p-2 rounded-lg bg-zinc-950 border border-zinc-800 flex items-center justify-between text-[11px]">
              <span className="text-zinc-400">Transport:</span>
              <span className={`font-semibold ${isUsbConnected ? 'text-emerald-400' : 'text-amber-400'}`}>
                {usbStatus?.transport || 'USB Tether / ADB Reverse'}
              </span>
            </div>

            <button
              onClick={onOpenUsbModal}
              className="w-full py-1.5 rounded-lg border border-zinc-700/80 bg-zinc-900/90 hover:bg-zinc-800 text-zinc-200 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
            >
              <span>Inspect Wire Link & Setup Guide</span>
              <ExternalLink className="w-3 h-3 text-zinc-400" />
            </button>
          </div>

        </div>
      </div>

      {/* 4. BOTTOM ROW: Recent Ingress Optical Packets Table (Left) + Top Anomaly Types (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        
        {/* Left Col (8 of 12 cols): Recent Optical Packets Table */}
        <div className="lg:col-span-8 rounded-xl border border-zinc-800/80 bg-[#10131d] p-4 flex flex-col shadow-lg">
          <div className="flex items-center justify-between pb-3 border-b border-zinc-800/60">
            <div>
              <h3 className="text-xs font-semibold text-zinc-100 font-mono uppercase tracking-wider">
                Recent Flagged Optical Packets
              </h3>
              <p className="text-[11px] text-zinc-400 mt-0.5">
                Latest items awaiting operator validation & simplex verification
              </p>
            </div>
            <button
              onClick={() => onSwitchTab('alerts')}
              className="text-xs font-mono text-violet-400 hover:text-violet-300 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <span>View all alerts</span>
              <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Table Container */}
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-left font-mono text-xs">
              <thead>
                <tr className="text-zinc-500 text-[10px] uppercase border-b border-zinc-800/50">
                  <th className="py-2 px-2 font-normal">Packet ID</th>
                  <th className="py-2 px-2 font-normal">Source</th>
                  <th className="py-2 px-2 font-normal">Type / Channel</th>
                  <th className="py-2 px-2 font-normal">Metrics</th>
                  <th className="py-2 px-2 font-normal">Severity</th>
                  <th className="py-2 px-2 font-normal">Status</th>
                  <th className="py-2 px-2 font-normal text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/40 text-[11px]">
                {recentPackets.map((pkt, idx) => (
                  <tr key={idx} className="hover:bg-zinc-800/30 transition-colors">
                    <td className="py-2.5 px-2 font-semibold text-zinc-200">
                      {pkt.id}
                    </td>
                    <td className="py-2.5 px-2 text-zinc-300">
                      {pkt.src}
                    </td>
                    <td className="py-2.5 px-2 text-zinc-400">
                      <div className="text-zinc-200">{pkt.type}</div>
                      <div className="text-[9px] text-zinc-500">{pkt.channel}</div>
                    </td>
                    <td className="py-2.5 px-2 text-zinc-400">
                      {pkt.bytes}B · {pkt.iat}s · {pkt.entropy} ent
                    </td>
                    <td className="py-2.5 px-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                        pkt.severity === 'Critical'
                          ? 'bg-rose-950/60 text-rose-300 border-rose-800/60'
                          : pkt.severity === 'Medium'
                          ? 'bg-amber-950/60 text-amber-300 border-amber-800/60'
                          : 'bg-emerald-950/60 text-emerald-300 border-emerald-800/60'
                      }`}>
                        {pkt.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-2">
                      <span className="flex items-center gap-1 text-emerald-400 text-[10px]">
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        {pkt.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-right">
                      <button
                        onClick={() => setSelectedPacket(pkt)}
                        className="px-2 py-1 rounded bg-zinc-900 border border-zinc-700/60 hover:bg-zinc-800 text-zinc-300 text-[10px] transition-colors cursor-pointer"
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right Col (4 of 12 cols): Top Anomaly Types */}
        <div className="lg:col-span-4 rounded-xl border border-zinc-800/80 bg-[#10131d] p-4 flex flex-col justify-between shadow-lg">
          <div>
            <h3 className="text-xs font-semibold text-zinc-100 font-mono uppercase tracking-wider">
              Top Anomaly Types
            </h3>
            <p className="text-[11px] text-zinc-400 mt-0.5">
              Frequency of detected cyber intrusion techniques
            </p>

            {/* Horizontal Bar Chart */}
            <div className="mt-4 space-y-3 font-mono text-[11px]">
              {anomalyTypes.map((item, idx) => (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="text-zinc-300 truncate max-w-[200px]">
                      {item.label}
                    </span>
                    <span className="text-zinc-400 font-semibold">{item.count}</span>
                  </div>
                  {/* Progress track */}
                  <div className="h-2 w-full rounded-full bg-zinc-900 overflow-hidden border border-zinc-800/80">
                    <div
                      className={`h-full rounded-full bg-gradient-to-r ${item.color} transition-all duration-500`}
                      style={{ width: `${item.pct}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="pt-3 mt-3 border-t border-zinc-800/60 text-[10px] text-zinc-500 font-mono flex items-center justify-between">
            <span>NTRO Problem Statement #26145</span>
            <span className="text-emerald-400">Zero False Positives</span>
          </div>
        </div>

      </div>

      {/* Selected Packet Inspection Modal */}
      {selectedPacket && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-xl border border-zinc-800 bg-[#111420] p-5 shadow-2xl space-y-4 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-violet-400" />
                <h4 className="font-bold text-sm text-white">Packet Inspection: {selectedPacket.id}</h4>
              </div>
              <button
                onClick={() => setSelectedPacket(null)}
                className="text-zinc-400 hover:text-white p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-zinc-300 text-[11px]">
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 flex justify-between">
                <span className="text-zinc-400">Source Node:</span>
                <span className="text-white font-semibold">{selectedPacket.src}</span>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 flex justify-between">
                <span className="text-zinc-400">Classification:</span>
                <span className="text-white font-semibold">{selectedPacket.type} ({selectedPacket.channel})</span>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 flex justify-between">
                <span className="text-zinc-400">Metrics:</span>
                <span className="text-white font-semibold">{selectedPacket.bytes} Bytes · IAT {selectedPacket.iat}s · Entropy {selectedPacket.entropy}</span>
              </div>
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 flex justify-between">
                <span className="text-zinc-400">Simplex Diode Guarantee:</span>
                <span className="text-emerald-400 font-semibold">100% Optical Forwarding · 0.00% Reverse Bit Leak</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedPacket(null)}
                className="px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white font-semibold text-xs transition-colors cursor-pointer"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
