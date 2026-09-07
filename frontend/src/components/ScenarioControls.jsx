import React, { useState } from 'react';
import { Play, Pause, RotateCcw, Zap, Radio, Database, Server, ShieldCheck, Gauge } from 'lucide-react';

export default function ScenarioControls({ 
  onTriggerAttack, 
  currentScenario = 'calm',
  isStreaming = true,
  onToggleStreaming,
  onResetStream,
  speed = 1.0,
  onChangeSpeed
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

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-5 shadow-2xl">
      {/* Title */}
      <div className="flex items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400">
            <Zap className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">
              Live Threat Scenario Controller
            </h3>
            <p className="text-xs text-slate-400">
              One-click in-zone air-gap traffic injection · Real-time pipeline testing
            </p>
          </div>
        </div>

        {/* Playback Controls */}
        <div className="flex items-center gap-2">
          <button
            onClick={onToggleStreaming}
            className={`p-2 rounded-xl border font-mono text-xs flex items-center gap-1.5 transition-all ${
              isStreaming
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-300 hover:bg-amber-500/30'
                : 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300 hover:bg-emerald-500/30'
            }`}
          >
            {isStreaming ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
            <span>{isStreaming ? 'PAUSE' : 'RESUME'}</span>
          </button>

          <button
            onClick={onResetStream}
            className="p-2 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 hover:text-white hover:border-slate-600 transition-all text-xs font-mono flex items-center gap-1"
            title="Reset telemetry & alert buffer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESET</span>
          </button>
        </div>
      </div>

      {/* 4 Attack Injection Buttons */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {/* 1. Calm Baseline */}
        <button
          onClick={() => handleScenarioClick('calm')}
          disabled={loading}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between ${
            currentScenario === 'calm'
              ? 'bg-emerald-500/20 border-emerald-500 text-emerald-300 shadow-lg shadow-emerald-500/20 scale-[1.02]'
              : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:border-emerald-500/50 hover:bg-emerald-500/5'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Calm Baseline
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              BENIGN
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Periodic SCADA telemetry + subtle web sync. Anomaly score remains &lt; τ = 2.810 (0.0% FPR).
          </p>
        </button>

        {/* 2. Exfiltration Flood */}
        <button
          onClick={() => handleScenarioClick('exfil_burst')}
          disabled={loading}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between ${
            currentScenario === 'exfil_burst'
              ? 'bg-red-500/20 border-red-500 text-red-300 shadow-lg shadow-red-500/20 scale-[1.02]'
              : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:border-red-500/50 hover:bg-red-500/5'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-red-400">
              <Database className="w-4 h-4 text-red-400" />
              Exfil Flood
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/30">
              BYTES
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            High-volume data leak (1400 B packets at 15ms). Drives score to ~880. Attributed to <b className="text-red-300">bytes</b>.
          </p>
        </button>

        {/* 3. C2 Beacon */}
        <button
          onClick={() => handleScenarioClick('c2_beacon')}
          disabled={loading}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between ${
            currentScenario === 'c2_beacon'
              ? 'bg-purple-500/20 border-purple-500 text-purple-300 shadow-lg shadow-purple-500/20 scale-[1.02]'
              : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:border-purple-500/50 hover:bg-purple-500/5'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-purple-400">
              <Radio className="w-4 h-4 text-purple-400" />
              C2 Beacon
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
              ENTROPY
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Covert heartbeats (2.5s period, high entropy). Drives score to ~16.4. Attributed to <b className="text-purple-300">entropy</b>.
          </p>
        </button>

        {/* 4. DGA Tunnel */}
        <button
          onClick={() => handleScenarioClick('dga_tunnel')}
          disabled={loading}
          className={`p-3.5 rounded-xl border text-left transition-all duration-200 flex flex-col justify-between ${
            currentScenario === 'dga_tunnel'
              ? 'bg-amber-500/20 border-amber-500 text-amber-300 shadow-lg shadow-amber-500/20 scale-[1.02]'
              : 'bg-slate-950/60 border-slate-800/80 text-slate-300 hover:border-amber-500/50 hover:bg-amber-500/5'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="font-mono text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 text-amber-400">
              <Server className="w-4 h-4 text-amber-400" />
              DGA Tunnel
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
              ENTROPY
            </span>
          </div>
          <p className="text-[11px] text-slate-400">
            Algorithmic domain queries. Drives score to ~75.0. Attributed to <b className="text-amber-300">entropy</b> (86.7%+).
          </p>
        </button>
      </div>

      {/* Speed Slider Strip */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2 text-slate-400">
          <Gauge className="w-4 h-4 text-cyan-400" />
          <span>SIMULATION SPEED MULTIPLIER:</span>
        </div>
        <div className="flex items-center gap-1.5">
          {[1.0, 2.0, 5.0, 10.0].map((s) => (
            <button
              key={s}
              onClick={() => onChangeSpeed(s)}
              className={`px-3 py-1 rounded-lg border transition-all ${
                speed === s
                  ? 'bg-cyan-500/20 border-cyan-500 text-cyan-300 font-bold shadow-md shadow-cyan-500/20'
                  : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-white'
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
