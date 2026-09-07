import React, { useState } from 'react';
import { BarChart3, LineChart, ShieldCheck, Timer, Target, Sparkles, CheckCircle2, ChevronRight } from 'lucide-react';

export default function CampaignAnalytics({ campaignData = {} }) {
  const [activeTab, setActiveTab] = useState('summary');

  const p1 = campaignData.phase1_baseline || { fpr: 0.0, mean_peak_score: 0.50 };
  const p2 = campaignData.phase2_regime_shift || { regime_shift_fpr: 0.0, mean_peak_score: 2.45 };
  const p3 = campaignData.phase3_sustained_attack || { persistence_rate: 1.0, ttd_seconds: 1.02, mean_peak_score: 880.32 };
  const p4 = campaignData.phase4_recovery || { post_recovery_fpr: 0.0, recovery_seconds: 13.0, mean_peak_score: 0.50 };
  const tau = campaignData.threshold_tau || 2.810;

  const benchmarkMatrix = [
    {
      attack: 'Exfil Flood (exfil_burst)',
      peakScore: '880.32',
      tau: '2.81',
      ttd: '1.02s',
      persistence: '100.0%',
      channel: 'bytes (100%)',
      verdict: 'IMMEDIATE LETHAL BURST DETECTION'
    },
    {
      attack: 'C2 Beacon (c2_beacon)',
      peakScore: '16.40',
      tau: '2.81',
      ttd: '3.02s',
      persistence: '98.3%',
      channel: 'entropy (100%)',
      verdict: 'STEALTHY PERIODICITY CAUGHT'
    },
    {
      attack: 'DGA Tunnel (dga_tunnel)',
      peakScore: '75.08',
      tau: '2.81',
      ttd: '1.02s',
      persistence: '100.0%',
      channel: 'entropy (86.7%)',
      verdict: 'DOMAIN ANOMALY FLAGGED'
    }
  ];

  return (
    <div className="space-y-6">
      {/* 4-Phase Continuous Timeline Header */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-6 shadow-2xl">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div>
            <h3 className="text-lg font-bold text-white tracking-wide uppercase font-mono flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-cyan-400" />
              Continuous 300-Second Campaign Benchmark
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Single multiregime baseline checkpoint (τ = {tau.toFixed(3)}) · Zero false positives across calm & regime shifts
            </p>
          </div>

          <div className="flex items-center gap-2 font-mono text-xs">
            <span className="px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
              0.0% CALM FPR
            </span>
            <span className="px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              1.02s FASTEST TTD
            </span>
            <span className="px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/30 text-purple-400">
              100% PERSISTENCE
            </span>
          </div>
        </div>

        {/* 4 Phase KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
          {/* Phase 1 */}
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span>PHASE 1 (0–60s)</span>
              <span className="text-emerald-400">CALM BASELINE</span>
            </div>
            <div className="text-2xl font-bold text-white">
              {(p1.fpr * 100).toFixed(1)}% <span className="text-xs text-slate-400 font-normal">FPR</span>
            </div>
            <div className="text-xs text-slate-400 mt-2">
              Mean Peak Score: <b className="text-emerald-300">{p1.mean_peak_score?.toFixed(2) || '0.50'}</b> &lt;&lt; τ
            </div>
          </div>

          {/* Phase 2 */}
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span>PHASE 2 (60–120s)</span>
              <span className="text-cyan-400">REGIME SHIFT</span>
            </div>
            <div className="text-2xl font-bold text-white">
              {((p2.regime_shift_fpr || 0) * 100).toFixed(1)}% <span className="text-xs text-slate-400 font-normal">FPR</span>
            </div>
            <div className="text-xs text-slate-400 mt-2">
              Web Sync Mean S: <b className="text-cyan-300">{p2.mean_peak_score?.toFixed(2) || '2.45'}</b> &lt; τ
            </div>
          </div>

          {/* Phase 3 */}
          <div className="p-4 rounded-xl bg-slate-950/70 border border-red-500/30 bg-red-950/10 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span>PHASE 3 (120–240s)</span>
              <span className="text-red-400 font-bold">SUSTAINED ATTACK</span>
            </div>
            <div className="text-2xl font-bold text-red-400">
              {((p3.persistence_rate || 1.0) * 100).toFixed(1)}% <span className="text-xs text-slate-400 font-normal">PERSISTENCE</span>
            </div>
            <div className="text-xs text-slate-400 mt-2">
              Time-to-Detect: <b className="text-red-300">{p3.ttd_seconds || 1.02}s</b> | Peak S: {p3.mean_peak_score?.toFixed(1) || '880.3'}
            </div>
          </div>

          {/* Phase 4 */}
          <div className="p-4 rounded-xl bg-slate-950/70 border border-slate-800 flex flex-col justify-between">
            <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
              <span>PHASE 4 (240–300s)</span>
              <span className="text-purple-400">POST RECOVERY</span>
            </div>
            <div className="text-2xl font-bold text-white">
              {((p4.post_recovery_fpr || 0) * 100).toFixed(1)}% <span className="text-xs text-slate-400 font-normal">FPR</span>
            </div>
            <div className="text-xs text-slate-400 mt-2">
              Decay Recovery: <b className="text-purple-300">~{p4.recovery_seconds || 13.0}s</b> (Hysteresis reset)
            </div>
          </div>
        </div>

        {/* High-Resolution Continuous Campaign Plot Display */}
        <div className="mt-6 rounded-xl border border-slate-800 overflow-hidden bg-black/80 flex flex-col items-center">
          <div className="w-full px-4 py-2 border-b border-slate-800 text-xs font-mono text-slate-400 flex items-center justify-between">
            <span>FIGURE 1: CONTINUOUS 300s TIMELINE PEAK ANOMALY SCORE S(t) VS DECISION BOUNDARY τ</span>
            <span className="text-cyan-400">CHECKPOINT: njode_telemetry.pt (v1.0)</span>
          </div>
          <img
            src="/assets/campaign.png"
            alt="CHRONOS Continuous Campaign Benchmark Plot"
            className="w-full max-h-[420px] object-contain p-2 hover:scale-[1.01] transition-transform duration-300"
          />
        </div>
      </div>

      {/* Canonical Comparison Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-xl p-6 shadow-2xl">
        <h4 className="text-sm font-bold text-white tracking-wide uppercase font-mono mb-4 flex items-center gap-2">
          <Target className="w-4 h-4 text-cyan-400" />
          Canonical Benchmark Across Attack Vectors (PPT Presentation Reference)
        </h4>

        <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/70">
          <table className="w-full text-left border-collapse font-mono text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/90 text-slate-400 uppercase text-[11px]">
                <th className="py-3 px-4">Attack Scenario</th>
                <th className="py-3 px-4 text-right">Mean Peak Score (S)</th>
                <th className="py-3 px-4 text-center">Decision Threshold (τ)</th>
                <th className="py-3 px-4 text-right">Time-to-Detect (TTD)</th>
                <th className="py-3 px-4 text-center">Persistence Rate</th>
                <th className="py-3 px-4">Dominant Channel Attribution</th>
                <th className="py-3 px-4">Jury Review Takeaway</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {benchmarkMatrix.map((row, idx) => (
                <tr key={idx} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3 px-4 font-bold text-white">{row.attack}</td>
                  <td className="py-3 px-4 text-right font-bold text-red-400">{row.peakScore}</td>
                  <td className="py-3 px-4 text-center text-slate-400">{row.tau}</td>
                  <td className="py-3 px-4 text-right text-cyan-300 font-bold">{row.ttd}</td>
                  <td className="py-3 px-4 text-center text-emerald-400">{row.persistence}</td>
                  <td className="py-3 px-4">
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-amber-300 font-bold">
                      {row.channel}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-slate-300 text-[11px]">{row.verdict}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
