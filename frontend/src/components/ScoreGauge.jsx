import React from 'react';
import { AlertTriangle, CheckCircle2, ShieldAlert, TrendingUp } from 'lucide-react';

export default function ScoreGauge({ score = 0, tau = 2.810, isAnomaly = false, confirmed = false, history = [] }) {
  // Compute percentage towards threshold and beyond
  const maxScoreScale = Math.max(tau * 3.5, score * 1.15, 10.0);
  const percentOfScale = Math.min((score / maxScoreScale) * 100, 100);
  const tauPercent = (tau / maxScoreScale) * 100;

  const isConfirmedAlert = confirmed && isAnomaly;
  const isSuspected = isAnomaly && !confirmed;

  return (
    <div className="rounded-xl border border-zinc-800 bg-[#090a0f] p-4 flex flex-col justify-between">
      {/* Top Title & Hysteresis State Machine Badge */}
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-md border text-xs ${
            isConfirmedAlert ? 'bg-rose-950/40 border-rose-800/40 text-rose-400' :
            isSuspected ? 'bg-amber-950/40 border-amber-800/40 text-amber-400' :
            'bg-zinc-900 border-zinc-800 text-emerald-400'
          }`}>
            {isConfirmedAlert ? <ShieldAlert className="w-4 h-4" /> :
             isSuspected ? <AlertTriangle className="w-4 h-4" /> :
             <CheckCircle2 className="w-4 h-4" />}
          </div>
          <div>
            <h3 className="text-xs font-semibold text-zinc-200 tracking-wider uppercase font-mono">
              Anomaly Score vs τ Threshold
            </h3>
            <p className="text-[11px] text-zinc-400">
              {"Peak error S = max ||x - x̂||₂ · Calibrated threshold τ = " + tau.toFixed(2)}
            </p>
          </div>
        </div>

        {/* 2-of-3 Hysteresis State Badge */}
        <div className={`px-2.5 py-1 rounded-md text-xs font-mono font-medium tracking-wider uppercase border flex items-center gap-1.5 ${
          isConfirmedAlert ? 'bg-rose-950/30 border-rose-900/60 text-rose-300' :
          isSuspected ? 'bg-amber-950/30 border-amber-900/60 text-amber-300' :
          'bg-zinc-900 border-zinc-800 text-zinc-400'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${
            isConfirmedAlert ? 'bg-rose-500' :
            isSuspected ? 'bg-amber-400' :
            'bg-emerald-500'
          }`} />
          <span>
            {isConfirmedAlert ? 'CONFIRMED ANOMALY (2/2)' :
             isSuspected ? 'SUSPECTED (1/2 STRIDE)' :
             'PASSIVE CALM'}
          </span>
        </div>
      </div>

      {/* Center Numeric Metric & Gauge Bar */}
      <div className="my-2.5 p-4 rounded-lg bg-zinc-950 border border-zinc-800 flex flex-col items-center justify-center relative">
        <div className="flex items-baseline gap-2.5 z-10 font-mono">
          <span className={`text-4xl font-bold tracking-tight ${
            isConfirmedAlert ? 'text-rose-400' :
            isSuspected ? 'text-amber-400' :
            'text-zinc-100'
          }`}>
            {score.toFixed(2)}
          </span>
          <span className="text-zinc-400 text-xs font-medium">
            / τ = {tau.toFixed(2)}
          </span>
        </div>

        {/* Linear Progress Bar with Marker for Tau */}
        <div className="w-full mt-3 z-10">
          <div className="relative h-2 w-full bg-zinc-850 rounded-full overflow-visible">
            {/* Dynamic Score Fill */}
            <div
              className={`h-full rounded-full transition-all duration-300 ${
                score > tau ? 'bg-rose-500' : 'bg-sky-500'
              }`}
              style={{ width: `${percentOfScale}%` }}
            />

            {/* Threshold Pin */}
            <div
              className="absolute -top-1 bottom-0 w-0.5 bg-zinc-300 z-20"
              style={{ left: `${tauPercent}%` }}
            />
            <div
              className="absolute -bottom-5 text-[10px] font-mono text-zinc-400 -translate-x-1/2 whitespace-nowrap"
              style={{ left: `${tauPercent}%` }}
            >
              τ = {tau.toFixed(2)}
            </div>
          </div>
        </div>

        <div className="w-full flex justify-between text-[10px] font-mono text-zinc-400 mt-5">
          <span>0.0</span>
          <span>Calibrated Horizon Baseline</span>
          <span>{maxScoreScale.toFixed(1)} max</span>
        </div>
      </div>

      {/* Trailing Score Sparkline Mini-Chart */}
      <div className="mt-2">
        <div className="flex items-center justify-between text-xs font-mono text-zinc-400 mb-1.5">
          <span className="flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-zinc-400" />
            Window Peak History (Last 30 Windows)
          </span>
          <span className="text-[10px] text-zinc-400">Gate: 2-of-3</span>
        </div>

        <div className="h-14 w-full flex items-end gap-1 px-2 py-1 bg-zinc-950 rounded-lg border border-zinc-800">
          {history.slice(-30).map((h, i) => {
            const barH = Math.min((h.score / maxScoreScale) * 100, 100);
            const exceedsTau = h.score > tau;
            return (
              <div key={i} className="flex-1 flex flex-col items-center justify-end h-full group relative">
                <div
                  className={`w-full rounded-xs transition-colors ${
                    exceedsTau ? 'bg-rose-500' : 'bg-zinc-700 hover:bg-zinc-500'
                  }`}
                  style={{ height: `${Math.max(barH, 6)}%` }}
                />
                {/* Tooltip on hover */}
                <div className="opacity-0 group-hover:opacity-100 absolute bottom-full mb-1 z-30 pointer-events-none text-[10px] font-mono bg-zinc-900 border border-zinc-700 px-1.5 py-0.5 rounded text-zinc-200 whitespace-nowrap shadow-lg">
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
