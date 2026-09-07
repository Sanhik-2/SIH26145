import React from 'react';
import { Target, Server, Database, Radio, Flame, Zap, ShieldAlert, ArrowDownLeft } from 'lucide-react';

export default function AttributionMatrix({ attribution = {} }) {
  const topChannel = attribution.top_channel || '—';
  const threatType = attribution.threat_type || 'calm-baseline';
  const errors = attribution.channel_errors || { iat: 0.1, bytes: 0.1, entropy: 0.1, burst: 0.1, direction: 0.1 };

  // Calculate sum and relative percentages across 5 channels
  const sumErrors = Object.values(errors).reduce((a, b) => a + b, 0) || 1.0;
  const pct = {
    bytes: Math.min(Math.round(((errors.bytes || 0) / sumErrors) * 100), 100),
    entropy: Math.min(Math.round(((errors.entropy || 0) / sumErrors) * 100), 100),
    iat: Math.min(Math.round(((errors.iat || 0) / sumErrors) * 100), 100),
    burst: Math.min(Math.round(((errors.burst || 0) / sumErrors) * 100), 100),
    direction: Math.min(Math.round(((errors.direction || 0) / sumErrors) * 100), 100),
  };

  const getThreatBadge = (threat) => {
    switch (threat) {
      case 'ddos_flood':
      case 'volumetric-ddos':
        return { label: 'VOLUMETRIC / PROTOCOL DDOS', color: 'bg-rose-950/40 text-rose-300 border-rose-800/40', icon: Zap };
      case 'c2_beacon':
      case 'c2-beacon':
      case 'beacon/recon':
        return { label: 'BOTNET C2 BEACON', color: 'bg-zinc-900 text-zinc-200 border-zinc-700', icon: Radio };
      case 'dga_tunnel':
      case 'dga-tunnel':
      case 'tunnel/encrypted-c2':
        return { label: 'DGA DNS TUNNEL', color: 'bg-amber-950/40 text-amber-300 border-amber-800/40', icon: Server };
      case 'tls_c2':
        return { label: 'ENCRYPTED TLS C2', color: 'bg-zinc-900 text-zinc-200 border-zinc-700', icon: ShieldAlert };
      case 'portscan':
        return { label: 'RECON PORT SCAN', color: 'bg-zinc-900 text-zinc-200 border-zinc-700', icon: Target };
      case 'exfil_burst':
      case 'exfil-flood':
        return { label: 'EXFILTRATION FLOOD', color: 'bg-rose-950/40 text-rose-300 border-rose-800/40', icon: Database };
      default:
        return { label: 'CALM BENIGN BASELINE', color: 'bg-zinc-900 text-emerald-400 border-zinc-800', icon: Target };
    }
  };

  const badge = getThreatBadge(threatType);
  const IconComponent = badge.icon;

  return (
    <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-4 flex flex-col justify-between">
      {/* Title & Identified Threat Category */}
      <div className="flex items-center justify-between gap-2 mb-3.5">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-md bg-zinc-900 border border-zinc-800 text-zinc-400">
            <Target className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Channel Attribution Matrix
            </h3>
            <p className="text-[11px] text-zinc-400">
              5-Channel reconstruction error decomposition
            </p>
          </div>
        </div>

        <div className={`px-2.5 py-1 rounded-md border text-xs font-mono font-medium flex items-center gap-1.5 ${badge.color}`}>
          <IconComponent className="w-3.5 h-3.5" />
          <span>{badge.label}</span>
        </div>
      </div>

      {/* 5-Channel Distribution Bars */}
      <div className="space-y-2.5 font-mono text-xs">
        {/* Direction Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-zinc-300 flex items-center gap-1.5">
              <ArrowDownLeft className="w-3 h-3 text-rose-400" />
              <span>direction (Flow asymmetry)</span>
              {topChannel === 'direction' && (
                <span className="text-[9px] bg-zinc-800 text-rose-400 px-1.5 py-0.5 rounded border border-zinc-700 font-medium">
                  DOMINANT
                </span>
              )}
            </span>
            <span className="text-zinc-400 font-medium">{pct.direction}%</span>
          </div>
          <div className="h-1.5 w-full bg-zinc-850 rounded-full overflow-hidden">
            <div
              className="h-full bg-rose-500 transition-all duration-300"
              style={{ width: `${pct.direction}%` }}
            />
          </div>
        </div>

        {/* Bytes Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-zinc-300 flex items-center gap-1.5">
              <Database className="w-3 h-3 text-sky-400" />
              <span>bytes (Payload volume)</span>
              {topChannel === 'bytes' && (
                <span className="text-[9px] bg-zinc-800 text-sky-400 px-1.5 py-0.5 rounded border border-zinc-700 font-medium">
                  DOMINANT
                </span>
              )}
            </span>
            <span className="text-zinc-400 font-medium">{pct.bytes}%</span>
          </div>
          <div className="h-1.5 w-full bg-zinc-850 rounded-full overflow-hidden">
            <div
              className="h-full bg-sky-500 transition-all duration-300"
              style={{ width: `${pct.bytes}%` }}
            />
          </div>
        </div>

        {/* Entropy Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-zinc-300 flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-amber-400" />
              <span>entropy (Shannon bits)</span>
              {topChannel === 'entropy' && (
                <span className="text-[9px] bg-zinc-800 text-amber-400 px-1.5 py-0.5 rounded border border-zinc-700 font-medium">
                  DOMINANT
                </span>
              )}
            </span>
            <span className="text-zinc-400 font-medium">{pct.entropy}%</span>
          </div>
          <div className="h-1.5 w-full bg-zinc-850 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 transition-all duration-300"
              style={{ width: `${pct.entropy}%` }}
            />
          </div>
        </div>

        {/* IAT Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-zinc-300 flex items-center gap-1.5">
              <Target className="w-3 h-3 text-emerald-400" />
              <span>iat (Inter-arrival timing)</span>
              {topChannel === 'iat' && (
                <span className="text-[9px] bg-zinc-800 text-emerald-400 px-1.5 py-0.5 rounded border border-zinc-700 font-medium">
                  DOMINANT
                </span>
              )}
            </span>
            <span className="text-zinc-400 font-medium">{pct.iat}%</span>
          </div>
          <div className="h-1.5 w-full bg-zinc-850 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 transition-all duration-300"
              style={{ width: `${pct.iat}%` }}
            />
          </div>
        </div>

        {/* Burst Channel */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-zinc-300 flex items-center gap-1.5">
              <Flame className="w-3 h-3 text-rose-400" />
              <span>burst (Density clustering)</span>
              {topChannel === 'burst' && (
                <span className="text-[9px] bg-zinc-800 text-rose-400 px-1.5 py-0.5 rounded border border-zinc-700 font-medium">
                  DOMINANT
                </span>
              )}
            </span>
            <span className="text-zinc-400 font-medium">{pct.burst}%</span>
          </div>
          <div className="h-1.5 w-full bg-zinc-850 rounded-full overflow-hidden">
            <div
              className="h-full bg-rose-500 transition-all duration-300"
              style={{ width: `${pct.burst}%` }}
            />
          </div>
        </div>
      </div>

      {/* Decision Rule Footnote */}
      <div className="mt-3.5 p-2 rounded-md bg-zinc-950 border border-zinc-800 text-[11px] text-zinc-400 font-mono flex items-center justify-between">
        <span>Attribution Rule:</span>
        <span className="text-zinc-300">{"arg max_c ||x_c - x̂_c||₂ (Unsupervised)"}</span>
      </div>
    </div>
  );
}

