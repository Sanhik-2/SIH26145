import React from 'react';
import { Target, Server, Database, Radio, Flame, ShieldAlert } from 'lucide-react';

export default function AttributionMatrix({ attribution = {} }) {
  const topChannel = attribution.top_channel || '—';
  const threatType = attribution.threat_type || 'calm-baseline';
  const errors = attribution.channel_errors || { iat: 0.1, bytes: 0.1, entropy: 0.1, burst: 0.1 };

  // Calculate sum and relative percentages
  const sumErrors = Object.values(errors).reduce((a, b) => a + b, 0) || 1.0;
  const pct = {
    bytes: Math.min(Math.round(((errors.bytes || 0) / sumErrors) * 100), 100),
    entropy: Math.min(Math.round(((errors.entropy || 0) / sumErrors) * 100), 100),
    iat: Math.min(Math.round(((errors.iat || 0) / sumErrors) * 100), 100),
    burst: Math.min(Math.round(((errors.burst || 0) / sumErrors) * 100), 100),
  };

  const getThreatBadge = (threat) => {
    switch (threat) {
      case 'exfil-flood':
        return { label: 'EXFILTRATION FLOOD', color: 'bg-red-500/20 text-red-300 border-red-500/50', icon: Database };
      case 'c2-beacon':
        return { label: 'C2 PERIODIC BEACON', color: 'bg-purple-500/20 text-purple-300 border-purple-500/50', icon: Radio };
      case 'dga-tunnel':
        return { label: 'DGA DNS TUNNEL', color: 'bg-amber-500/20 text-amber-300 border-amber-500/50', icon: Server };
      default:
        return { label: 'CALM TELEMETRY', color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50', icon: Target };
    }
  };

  const badge = getThreatBadge(threatType);
  const IconComponent = badge.icon;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-5 shadow-2xl flex flex-col justify-between">
      {/* Title & Identified Threat Category */}
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-purple-500/10 border border-purple-500/30 text-purple-400">
            <Target className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">
              Bayesian Channel Attribution
            </h3>
            <p className="text-xs text-slate-400">
              Unsupervised error decomposition · Threat taxonomy classification
            </p>
          </div>
        </div>

        <div className={`px-3 py-1 rounded-full border text-xs font-mono font-bold flex items-center gap-1.5 ${badge.color}`}>
          <IconComponent className="w-3.5 h-3.5" />
          <span>{badge.label}</span>
        </div>
      </div>

      {/* 4-Channel Distribution Bars */}
      <div className="space-y-3 font-mono">
        {/* Bytes Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-amber-300 flex items-center gap-1.5 font-semibold">
              <Database className="w-3.5 h-3.5" />
              bytes (Volume)
              {topChannel === 'bytes' && <span className="text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.2 rounded border border-amber-500/40">DOMINANT</span>}
            </span>
            <span className="text-slate-300">{pct.bytes}%</span>
          </div>
          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-amber-300 transition-all duration-300"
              style={{ width: `${pct.bytes}%` }}
            />
          </div>
        </div>

        {/* Entropy Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-cyan-300 flex items-center gap-1.5 font-semibold">
              <Radio className="w-3.5 h-3.5" />
              entropy (Shannon H)
              {topChannel === 'entropy' && <span className="text-[10px] bg-cyan-500/20 text-cyan-300 px-1.5 py-0.2 rounded border border-cyan-500/40">DOMINANT</span>}
            </span>
            <span className="text-slate-300">{pct.entropy}%</span>
          </div>
          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-cyan-500 to-cyan-300 transition-all duration-300"
              style={{ width: `${pct.entropy}%` }}
            />
          </div>
        </div>

        {/* IAT Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-emerald-300 flex items-center gap-1.5 font-semibold">
              <Target className="w-3.5 h-3.5" />
              iat (Timing Jitter)
              {topChannel === 'iat' && <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.2 rounded border border-emerald-500/40">DOMINANT</span>}
            </span>
            <span className="text-slate-300">{pct.iat}%</span>
          </div>
          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-emerald-300 transition-all duration-300"
              style={{ width: `${pct.iat}%` }}
            />
          </div>
        </div>

        {/* Burst Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-pink-300 flex items-center gap-1.5 font-semibold">
              <Flame className="w-3.5 h-3.5" />
              burst (Clump Density)
              {topChannel === 'burst' && <span className="text-[10px] bg-pink-500/20 text-pink-300 px-1.5 py-0.2 rounded border border-pink-500/40">DOMINANT</span>}
            </span>
            <span className="text-slate-300">{pct.burst}%</span>
          </div>
          <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-pink-500 to-pink-300 transition-all duration-300"
              style={{ width: `${pct.burst}%` }}
            />
          </div>
        </div>
      </div>

      {/* Explanation Footer */}
      <div className="mt-4 p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px] text-slate-400 font-mono flex items-center justify-between">
        <span>Decision Rule:</span>
        <span className="text-slate-200">{"arg max_c ||x_c - x̂_c||₂ (Unsupervised)"}</span>
      </div>
    </div>
  );
}
