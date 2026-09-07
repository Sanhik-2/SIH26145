import React, { useState } from 'react';
import { Play, Pause, RotateCcw, Zap, Radio, Database, Server, ShieldCheck, Gauge } from 'lucide-react';

export default function ScenarioControls({ 
  onTriggerAttack, 
  currentScenario = 'calm',
  isStreaming = true,
  onToggleStreaming,
  onResetStream,
  speed = 1.0,
  onChangeSpeed,
  variant = 'full'
}) {
  const [loading, setLoading] = useState(false);

  const handleScenarioClick = async (scenarioKey) => {
    setLoading(true);
    try {
      await onTriggerAttack(scenarioKey);
    } finally {
      setLoading(false);
    }
  };

  if (variant === 'compact') {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-950/90 px-3.5 py-2 flex flex-wrap items-center justify-between gap-2.5 text-xs font-mono flex-shrink-0">
        <div className="flex items-center gap-1.5 overflow-x-auto py-0.5 max-w-full">
          <span className="text-[10px] text-zinc-400 font-semibold uppercase tracking-wider flex items-center gap-1 flex-shrink-0 pr-1">
            <Zap className="w-3.5 h-3.5 text-zinc-400" />
            Inject:
          </span>
          {[
            { key: 'calm', label: 'Calm Baseline', icon: ShieldCheck, color: 'text-emerald-400' },
            { key: 'ddos_flood', label: 'Volumetric DDoS', icon: Zap, color: 'text-rose-400' },
            { key: 'c2_beacon', label: 'C2 Beacon', icon: Radio, color: 'text-zinc-300' },
            { key: 'dga_tunnel', label: 'DGA Tunnel', icon: Server, color: 'text-amber-400' },
            { key: 'tls_c2', label: 'TLS C2', icon: Radio, color: 'text-zinc-300' },
            { key: 'portscan', label: 'Port Scan', icon: Gauge, color: 'text-zinc-300' },
            { key: 'exfil_burst', label: 'Exfil Burst', icon: Database, color: 'text-rose-400' },
          ].map(({ key, label, icon: Icon, color }) => (
            <button
              key={key}
              onClick={() => handleScenarioClick(key)}
              disabled={loading}
              className={`px-2 py-0.5 rounded-md border text-xs transition-colors flex items-center gap-1.5 flex-shrink-0 ${
                currentScenario === key
                  ? 'bg-zinc-800 border-zinc-600 text-zinc-100 font-medium ring-1 ring-zinc-600'
                  : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850'
              }`}
            >
              <Icon className={`w-3 h-3 ${color}`} />
              <span>{label}</span>
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2.5 flex-shrink-0">
          <div className="flex items-center gap-1">
            <span className="text-[10px] text-zinc-400">Speed:</span>
            {[1.0, 2.0, 5.0].map((s) => (
              <button
                key={s}
                onClick={() => onChangeSpeed(s)}
                className={`px-1.5 py-0.5 rounded border text-[11px] transition-colors ${
                  speed === s
                    ? 'bg-zinc-800 border-zinc-700 text-zinc-100 font-medium'
                    : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:text-zinc-200'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={onToggleStreaming}
              className={`px-2 py-0.5 rounded-md border text-xs flex items-center gap-1 transition-colors ${
                isStreaming
                  ? 'bg-zinc-900 border-zinc-800 text-amber-400 hover:bg-zinc-800'
                  : 'bg-zinc-900 border-zinc-800 text-emerald-400 hover:bg-zinc-800'
              }`}
            >
              {isStreaming ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
              <span>{isStreaming ? 'Pause' : 'Resume'}</span>
            </button>

            <button
              onClick={onResetStream}
              className="p-1 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              title="Reset Stream Buffer"
            >
              <RotateCcw className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-4">
      {/* Title & Controls */}
      <div className="flex items-center justify-between gap-3 mb-3.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Threat Scenario Injection
            </h3>
            <p className="text-[11px] text-zinc-400">
              One-click in-zone air-gap traffic injection · Real-time pipeline testing
            </p>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={onToggleStreaming}
            className={`px-2.5 py-1 rounded-md border font-mono text-xs flex items-center gap-1.5 transition-colors ${
              isStreaming
                ? 'bg-zinc-900 border-zinc-800 text-amber-400 hover:bg-zinc-800'
                : 'bg-zinc-900 border-zinc-800 text-emerald-400 hover:bg-zinc-800'
            }`}
          >
            {isStreaming ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isStreaming ? 'PAUSE' : 'RESUME'}</span>
          </button>

          <button
            onClick={onResetStream}
            className="px-2.5 py-1 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors text-xs font-mono flex items-center gap-1"
            title="Reset telemetry & alert buffer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESET</span>
          </button>
        </div>
      </div>

      {/* 7 Attack & Benign Scenario Injection Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2.5">
        {/* 1. Calm Baseline */}
        <button
          onClick={() => handleScenarioClick('calm')}
          disabled={loading}
          className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
            currentScenario === 'calm'
              ? 'bg-zinc-900 border-zinc-600 text-zinc-100 ring-1 ring-zinc-600'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-emerald-400">
              <ShieldCheck className="w-3.5 h-3.5" />
              Calm Baseline
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
              BENIGN
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Periodic SCADA telemetry + subtle web sync. Reconstruction error &lt; τ.
          </p>
        </button>

        {/* 2. Volumetric / Protocol DDoS */}
        <button
          onClick={() => handleScenarioClick('ddos_flood')}
          disabled={loading}
          className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
            currentScenario === 'ddos_flood'
              ? 'bg-zinc-900 border-rose-800/80 text-zinc-100 ring-1 ring-rose-800/80'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-rose-400">
              <Zap className="w-3.5 h-3.5" />
              Volumetric DDoS
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-rose-400 border border-zinc-800">
              DIRECTION
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Inbound flood (200 pkts/s tiny frames). Spoofed source IP entropy surge.
          </p>
        </button>

        {/* 3. Botnet C2 Beacon */}
        <button
          onClick={() => handleScenarioClick('c2_beacon')}
          disabled={loading}
          className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
            currentScenario === 'c2_beacon'
              ? 'bg-zinc-900 border-zinc-600 text-zinc-100 ring-1 ring-zinc-600'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-zinc-200">
              <Radio className="w-3.5 h-3.5 text-zinc-400" />
              C2 Beacon
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
              IAT / TIMING
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Periodic check-ins at T₀ ± δ intervals. Rigid timing signature attributed to IAT.
          </p>
        </button>

        {/* 4. DGA Domains & DNS Tunnel */}
        <button
          onClick={() => handleScenarioClick('dga_tunnel')}
          disabled={loading}
          className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
            currentScenario === 'dga_tunnel'
              ? 'bg-zinc-900 border-amber-800/80 text-zinc-100 ring-1 ring-amber-800/80'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-amber-400">
              <Server className="w-3.5 h-3.5" />
              DGA Tunnel
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-amber-400 border border-zinc-800">
              ENTROPY
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Algorithmic DNS exfil with 150-char labels. High Shannon entropy surge.
          </p>
        </button>

        {/* 5. Encrypted TLS C2 Sessions */}
        <button
          onClick={() => handleScenarioClick('tls_c2')}
          disabled={loading}
          className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
            currentScenario === 'tls_c2'
              ? 'bg-zinc-900 border-zinc-600 text-zinc-100 ring-1 ring-zinc-600'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-zinc-200">
              <Radio className="w-3.5 h-3.5 text-zinc-400" />
              Encrypted TLS C2
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
              METADATA
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Payload entropy ≈ 7.9. Detected strictly via timing &amp; packet size variance.
          </p>
        </button>

        {/* 6. Reconnaissance Port Scan */}
        <button
          onClick={() => handleScenarioClick('portscan')}
          disabled={loading}
          className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
            currentScenario === 'portscan'
              ? 'bg-zinc-900 border-zinc-600 text-zinc-100 ring-1 ring-zinc-600'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-zinc-200">
              <Gauge className="w-3.5 h-3.5 text-zinc-400" />
              Recon Port Scan
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-zinc-400 border border-zinc-800">
              FAN-OUT
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Single origin sweeping 128+ destination ports. High flow fan-out pattern.
          </p>
        </button>

        {/* 7. Data Exfiltration Flood */}
        <button
          onClick={() => handleScenarioClick('exfil_burst')}
          disabled={loading}
          className={`p-3 rounded-lg border text-left transition-colors flex flex-col justify-between ${
            currentScenario === 'exfil_burst'
              ? 'bg-zinc-900 border-rose-800/80 text-zinc-100 ring-1 ring-rose-800/80'
              : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:border-zinc-700 hover:bg-zinc-900/50'
          }`}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="font-mono text-xs font-semibold uppercase tracking-wider flex items-center gap-1.5 text-rose-400">
              <Database className="w-3.5 h-3.5" />
              Exfil Burst
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-zinc-900 text-rose-400 border border-zinc-800">
              BYTES
            </span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Bulk exfil (1400 B frames at 12ms). Skews byte volume manifold significantly.
          </p>
        </button>
      </div>

      {/* Speed Multiplier Strip */}
      <div className="mt-3.5 pt-3 border-t border-zinc-800/80 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-zinc-400">
          <Gauge className="w-4 h-4 text-zinc-400" />
          <span>SIMULATION SPEED:</span>
        </div>
        <div className="flex items-center gap-1">
          {[1.0, 2.0, 5.0, 10.0].map((s) => (
            <button
              key={s}
              onClick={() => onChangeSpeed(s)}
              className={`px-2.5 py-1 rounded-md border text-xs transition-colors ${
                speed === s
                  ? 'bg-zinc-800 border-zinc-700 text-zinc-100 font-medium'
                  : 'bg-zinc-950 border-zinc-800 text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
