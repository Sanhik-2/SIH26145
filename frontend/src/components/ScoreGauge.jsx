import React from 'react';
import { AlertTriangle, CheckCircle2, ShieldAlert, Zap, TrendingUp } from 'lucide-react';

export default function ScoreGauge({ score = 0, tau = 2.810, isAnomaly = false, confirmed = false, history = [] }) {
  // Compute percentage towards threshold and beyond
  const maxScoreScale = Math.max(tau * 3.5, score * 1.15, 10.0);
  const percentOfScale = Math.min((score / maxScoreScale) * 100, 100);
  const tauPercent = (tau / maxScoreScale) * 100;

  const isConfirmedAlert = confirmed && isAnomaly;
  const isSuspected = isAnomaly && !confirmed;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-5 shadow-2xl flex flex-col justify-between">
      {/* Top Title & Hysteresis State Machine Badge */}
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg border ${
            isConfirmedAlert ? 'bg-red-500/20 border-red-500 text-red-400 animate-pulse' :
            isSuspected ? 'bg-amber-500/20 border-amber-500 text-amber-400' :
            'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}>
            {isConfirmedAlert ? <ShieldAlert className="w-4 h-4" /> :
             isSuspected ? <AlertTriangle className="w-4 h-4" /> :
             <CheckCircle2 className="w-4 h-4" />}
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white tracking-wide uppercase font-mono">
              Anomaly Score vs τ Threshold
            </h3>
            <p className="text-xs text-slate-400">
              {"Window Peak S = max_t ||x_i - x̂_i||₂ · Operational Threshold τ = " + tau.toFixed(2)}
            </p>
          </div>
        </div>

        {/* 2-of-3 Hysteresis State Badge */}
        <div className={`px-3 py-1 rounded-full text-xs font-mono font-bold tracking-wider uppercase border flex items-center gap-1.5 ${
          isConfirmedAlert ? 'bg-red-500/20 border-red-500/60 text-red-300 animate-pulse shadow-lg shadow-red-500/30' :
          isSuspected ? 'bg-amber-500/20 border-amber-500/60 text-amber-300' :
          'bg-emerald-500/15 border-emerald-500/40 text-emerald-300'
        }`}>
          <span className={`w-2 h-2 rounded-full ${
            isConfirmedAlert ? 'bg-red-400 animate-ping' :
            isSuspected ? 'bg-amber-400' :
            'bg-emerald-400'
          }`} />
          <span>
            {isConfirmedAlert ? '🚨 CONFIRMED ATTACK (2/2)' :
             isSuspected ? '⚠️ SUSPECTED (1/2 STRIDE)' :
             '✅ PASSIVE CALM'}
          </span>
        </div>
      </div>

      {/* Center Big Metric & Gauge Bar */}
      <div className="my-3 p-4 rounded-xl bg-slate-950/70 border border-slate-800/80 flex flex-col items-center justify-center relative overflow-hidden">
        {/* Glow backdrop on alert */}
        {isConfirmedAlert && (
          <div className="absolute inset-0 bg-red-600/10 pointer-events-none animate-pulse" />
        )}

        <div className="flex items-baseline gap-3 z-10 font-mono">
          <span className={`text-5xl font-extrabold tracking-tight ${
            isConfirmedAlert ? 'text-red-400 drop-shadow-[0_0_15px_rgba(239,68,68,0.7)]' :
            isSuspected ? 'text-amber-400 drop-shadow-[0_0_12px_rgba(245,158,11,0.5)]' :
            'text-cyan-400 drop-shadow-[0_0_10px_rgba(6,182,212,0.4)]'
          }`}>
            {score.toFixed(2)}
          </span>
          <span className="text-slate-400 text-sm font-semibold">
            / τ = {tau.toFixed(2)}
          </span>
        </div>

        {/* Progress Bar with Marker for Tau */}
        <div className="w-full mt-4 z-10">
          <div className="relative h-3 w-full bg-slate-800 rounded-full overflow-visible">
            {/* Dynamic Score Fill */}
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                score > tau ? 'bg-gradient-to-r from-amber-500 to-red-500' : 'bg-gradient-to-r from-cyan-500 to-emerald-400'
              }`}
              style={{ width: `${percentOfScale}%` }}
            />

            {/* Threshold Pin */}
            <div
              className="absolute -top-1 bottom-0 w-1 bg-white shadow-[0_0_8px_#ffffff] z-20"
              style={{ left: `${tauPercent}%` }}
            />
            <div
              className="absolute -bottom-5 text-[10px] font-mono text-white font-bold -translate-x-1/2"
              style={{ left: `${tauPercent}%` }}
            >
              τ = {tau.toFixed(2)}
            </div>
          </div>
        </div>

        <div className="w-full flex justify-between text-[10px] font-mono text-slate-500 mt-6">
          <span>0.0 (Null drift)</span>
          <span>Calibrated Horizon Baseline</span>
          <span>{maxScoreScale.toFixed(1)} (Peak)</span>
        </div>
      </div>

      {/* Trailing Score Sparkline Mini-Chart */}
      <div className="mt-2">
        <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1.5">
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3.5 h-3.5 text-cyan-400" />
            Window Peak Trail (Last 30 Windows)
          </span>
          <span>Hysteresis Gate: 2-of-3</span>
        </div>

        <div className="h-16 w-full flex items-end gap-1 px-2 py-1 bg-slate-950/60 rounded-xl border border-slate-800">
          {history.slice(-30).map((h, i) => {
            const barH = Math.min((h.score / maxScoreScale) * 100, 100);
            const exceedsTau = h.score > tau;
            return (
              <div key={i} className="flex-1 flex flex-col items-center justify-end h-full group relative">
                <div
                  className={`w-full rounded-t-sm transition-all ${
                    exceedsTau ? 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.7)]' : 'bg-cyan-600/70 hover:bg-cyan-400'
                  }`}
                  style={{ height: `${Math.max(barH, 6)}%` }}
                />
                {/* Tooltip on hover */}
                <div className="opacity-0 group-hover:opacity-100 absolute bottom-full mb-1 z-30 pointer-events-none text-[10px] font-mono bg-black/90 border border-slate-700 px-1.5 py-0.5 rounded text-white whitespace-nowrap">
                  S = {h.score.toFixed(2)}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
